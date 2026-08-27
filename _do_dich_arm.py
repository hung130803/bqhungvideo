# -*- coding: utf-8 -*-
"""CÁC ARM SỬA — mọi arm chạy CÙNG BỘ CÂU, ghi ra file NGAY SAU MỖI LƯỢT.

| arm    | khác MỐC ở ĐÚNG một thứ                                          |
|--------|------------------------------------------------------------------|
| moc    | `thay_giong._dich_loat` nguyên xi (đường app đang đi)            |
| app    | `thay_giong.dich_hau_kiem` — ĐƯỜNG THẬT, có hậu kiểm dịch ngược  |
| me     | chia MẺ theo ngân sách token, prompt Y HỆT MỐC                   |
| ngucanh| MẺ + bối cảnh cả bài + 3 câu TRƯỚC / 3 câu SAU (không dịch)      |
| van    | NGỮ CẢNH + ĐỐI SOÁT DẤU VÂN câu gốc, lệch thì ĐÒI LẠI            |
| model  | MỐC nhưng đổi model (đo cột MODEL)                               |
| gio    | `dich.dich_theo_gio` (mở lại hướng đã bác)                       |
| soat   | `dich.dich_va_soat` (mở lại hướng đã bác)                        |

BẤT BIẾN: arm `me`/`ngucanh`/`van` dùng LẠI `_theo_nhan` + `_LUAT_KHONG_SOT`
của `thay_giong` — không viết bản prompt thứ hai cho cùng một việc.
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
import _dich_do_chung as C                                    # noqa: E402

# --------------------------------------------------------------- NGÂN SÁCH MẺ
#: Ước token ĐẦU RA cho MỘT câu (đo thật: 167 câu -> 3.312 token = 19,8/câu).
TOKEN_RA_MOI_CAU = 20
#: Chỗ trả lời phải rộng gấp ngần này lần mức CẦN. Model suy luận ăn CHUNG
#: ngân sách `max_tokens`, và khi chỗ hẹp nó "gói lại sớm" -> ĐÁNH RƠI/GỘP câu
#: rồi ĐÁNH SỐ TIẾP -> LỆCH BẬC. Đây là hằng số chống đúng chuyện đó.
HE_SO_ROI = 4.0
#: Trần cứng số câu mỗi mẻ (đừng để một mẻ to tới mức model lạc số).
ME_TOI_DA = 30
ME_TOI_THIEU = 8
#: Số câu NGỮ CẢNH mỗi bên (không dịch, chỉ để hiểu).
NGU_CANH_BEN = 3
#: Bối cảnh cả bài — bao nhiêu ký tự đầu.
BOI_CANH_KY_TU = 700
#: Dấu vân: bao nhiêu ký tự ĐẦU câu gốc bắt model chép lại để đối soát.
VAN_KY_TU = 4


def _uoc_prompt_token(cau, chi_so, them: int = 0) -> int:
    from app.ai import llm
    s = "".join('#%d [9.9 giay]: "%s"\n' % (i, cau[i]["text"]) for i in chi_so)
    return llm._uoc_token(s) + 420 + them


def chia_me(cau, chi_so):
    """Chia `chi_so` thành mẻ sao cho CHỖ TRẢ LỜI luôn rộng gấp `HE_SO_ROI`
    lần mức cần. Đây là phép chia THEO SỐ, không phải con số đặt mò."""
    from app.ai import llm
    ra, cur = [], []
    for i in chi_so:
        thu = cur + [i]
        pt = _uoc_prompt_token(cau, thu)
        mt = max(llm.GROQ_OUT_TOI_THIEU,
                 min(llm.GROQ_OUT_TOI_DA,
                     llm.GROQ_TPM_TRAN - pt - llm.GROQ_BIEN_AN_TOAN))
        can = TOKEN_RA_MOI_CAU * len(thu) * HE_SO_ROI
        if cur and (can > mt or len(thu) > ME_TOI_DA):
            ra.append(cur)
            cur = [i]
        else:
            cur = thu
    if cur:
        ra.append(cur)
    return ra


# ------------------------------------------------------------------- PROMPT
def _prompt_me(cau, phan, dich_sang, goc_ma, boi_canh="", ngu_canh=False,
               van=False):
    from app.core.thay_giong import _ten_nn, _LUAT_KHONG_SOT
    ten_dich = _ten_nn(dich_sang)
    n = len(cau)
    items = []
    for i in phan:
        c = cau[i]
        dur = max(0.1, float(c["end"]) - float(c["start"]))
        items.append('#%d [%.1f giây]: "%s"' % (i, dur, c["text"][:400]))
    dau = "Dịch các câu thoại sau từ %s sang %s.\n" % (_ten_nn(goc_ma),
                                                       ten_dich)
    if boi_canh:
        dau += ('\nBỐI CẢNH CẢ VIDEO (chỉ để hiểu đúng thuật ngữ và tên riêng, '
                'KHÔNG dịch phần này):\n"%s"\n' % boi_canh)
    if ngu_canh:
        a, b = phan[0], phan[-1]
        tr = " ".join(cau[j]["text"] for j in range(max(0, a - NGU_CANH_BEN), a))
        sa = " ".join(cau[j]["text"]
                      for j in range(b + 1, min(n, b + 1 + NGU_CANH_BEN)))
        dau += ('\nĐOẠN NGAY TRƯỚC (KHÔNG dịch, chỉ để nối mạch): "%s"\n'
                % (tr or "(đầu bài)"))
        dau += ('ĐOẠN NGAY SAU (KHÔNG dịch, chỉ để nối mạch): "%s"\n'
                % (sa or "(cuối bài)"))
        dau += ("\nCÁC CÂU CẦN DỊCH (chỉ dịch đúng những câu có dấu #):\n")
    luat = (
        "\n\nQUY TẮC:\n"
        "- Dịch sang %s, văn NÓI tự nhiên — viết như người thật đang NÓI "
        "trong video, KHÔNG dịch máy móc từng chữ.\n" % ten_dich
        + "- Giữ giọng điệu của câu gốc (kể chuyện, giới thiệu, cảm thán).\n"
          "- ĐỌC LÊN phải lọt khung [số giây] của câu đó — dài quá thì lược "
          "từ đệm, GIỮ Ý CHÍNH.\n"
          "- KHÔNG thêm chú thích, không phiên âm.\n"
        + _LUAT_KHONG_SOT + "\n")
    if ngu_canh:
        luat += ("- Câu ngắn/cụt là MỘT MẨU của câu dài đang nói dở: dịch nó "
                 "sao cho NỐI ĐƯỢC với đoạn trước và đoạn sau, đừng dịch nó "
                 "như một câu độc lập.\n")
    if van:
        luat += (
            "- Trả MẢNG JSON %d đối tượng "
            '{"i": <đúng số sau dấu #>, "g": "<%d KÝ TỰ ĐẦU của chính câu gốc '
            'số đó, chép y nguyên>", "t": "<bản dịch>"}. '
            "Trường \"g\" là để đối soát: chép SAI là bản dịch bị loại. "
            "BẮT BUỘC đủ MỌI số #, KHÔNG bỏ câu nào, KHÔNG gộp hai câu."
            % (len(phan), VAN_KY_TU))
    else:
        luat += ("- Trả MẢNG JSON %d đối tượng "
                 '{"i": <đúng số sau dấu #>, "t": "<bản dịch>"}. '
                 "BẮT BUỘC đủ MỌI số #, KHÔNG bỏ câu nào, KHÔNG gộp hai câu."
                 % len(phan))
    return dau + "\n".join(items) + luat


_SYSTEM = ("Bạn là chuyên gia dịch THAY TIẾNG cho video. Dịch tự nhiên như "
           "VĂN NÓI, đúng ý, đúng cảm xúc. CHỈ trả JSON thuần.")


def dich_me(cau, dich_sang, goc_ma, ngu_canh=False, van=False, model=None,
            vong=3):
    """Dịch theo MẺ. Trả (ban_dich, sổ)."""
    from app.ai import llm
    from app.core.thay_giong import _mang_llm
    n = len(cau)
    boi_canh = ""
    if ngu_canh:
        acc, tong = [], 0
        for c in cau:
            t = str(c.get("text") or "").strip()
            if not t or tong + len(t) > BOI_CANH_KY_TU:
                break
            acc.append(t)
            tong += len(t)
        boi_canh = " ".join(acc)
    ra: dict[int, str] = {}
    van_hong = 0
    mau_van: list = []
    con = list(range(n))
    for _v in range(vong):
        if not con:
            break
        moi: dict[int, str] = {}
        for phan in chia_me(cau, con):
            p = _prompt_me(cau, phan, dich_sang, goc_ma, boi_canh, ngu_canh,
                           van)
            try:
                d = llm.complete_json(p, system=_SYSTEM, model=model)
            except Exception:                              # noqa: BLE001
                continue
            for o in _mang_llm(d):
                if not isinstance(o, dict):
                    continue
                try:
                    i = int(o.get("i"))
                except (TypeError, ValueError):
                    continue
                t = o.get("t")
                if i not in phan or not isinstance(t, str) or not t.strip():
                    continue
                if van:
                    # ĐỐI SOÁT DẤU VÂN — chốt DUY NHẤT bắt được LỆCH BẬC.
                    # **CHỈ LOẠI KHI VÂN TRỎ SANG CÂU KHÁC**, không loại khi
                    # vân chỉ chép hơi lệch: loại bừa là đổi một câu lệch bậc
                    # lấy một câu MẤT HẲN (rồi rơi về câu gốc = mã F).
                    g = str(o.get("g") or "").strip()
                    that = str(cau[i].get("text") or "")[:VAN_KY_TU]
                    if g and g[:VAN_KY_TU] != that:
                        tro_ai = _van_tro_ai(cau, i, g)
                        mau_van.append({"i": i, "van": g[:8], "that": that,
                                        "tro": tro_ai})
                        if tro_ai is not None and tro_ai != i:
                            van_hong += 1
                            continue
                moi[i] = t.strip()
        if not moi:
            break
        ra.update(moi)
        con = [i for i in range(n) if i not in ra]
    bd = [ra.get(i) or str(cau[i].get("text") or "") for i in range(n)]
    return bd, {"thieu": len(con), "van_hong": van_hong,
                "van_lech_mat_chu": len(mau_van), "mau_van": mau_van[:60]}


def _van_tro_ai(cau, i, g):
    """Dấu vân `g` trỏ vào câu nào trong cửa sổ ±5? None = không trỏ ai cả."""
    g = str(g or "")[:VAN_KY_TU]
    if not g:
        return None
    tot, j_tot = 0, None
    for j in range(max(0, i - 5), min(len(cau), i + 6)):
        t = str(cau[j].get("text") or "")
        n = sum(1 for k in range(min(len(g), VAN_KY_TU)) if g[k] in t)
        if t[:VAN_KY_TU] == g:
            return j
        if n > tot:
            tot, j_tot = n, j
    # trỏ mờ (chỉ trùng vài ký tự) thì KHÔNG kết luận
    return j_tot if tot >= max(2, VAN_KY_TU - 1) else None


# --------------------------------------------------------------------- ARM
def chay_arm(arm: str, ma_video: str, dich_sang: str, lan: int,
             model: str = "") -> dict:
    from app.core import thay_giong as TG
    cau, meta = C.doc_cau(ma_video)
    goc_ma = (meta.get("language") or "")[:2].lower()
    goc = [c["text"] for c in cau]
    so = C.SoGoi()
    so.bat()
    t0, loi, phu = time.time(), "", {}
    try:
        if arm == "moc":
            bd = TG._dich_loat(cau, dich_sang, goc_ma)
        elif arm == "app":
            d = TG.dich_hau_kiem(cau, dich_sang, goc_ma)
            bd = list(d["ban_dich"])
            phu = {k: v for k, v in d.items() if k != "ban_dich"}
        elif arm == "me":
            bd, phu = dich_me(cau, dich_sang, goc_ma)
        elif arm == "ngucanh":
            bd, phu = dich_me(cau, dich_sang, goc_ma, ngu_canh=True)
        elif arm == "van":
            bd, phu = dich_me(cau, dich_sang, goc_ma, ngu_canh=True, van=True)
        elif arm == "model":
            bd = _dich_loat_model(cau, dich_sang, goc_ma, model)
        elif arm == "memodel":
            bd, phu = dich_me(cau, dich_sang, goc_ma, ngu_canh=True, van=True,
                              model=model)
        elif arm == "gio":
            from app.ai import dich as D
            d = D.dich_theo_gio(cau, dich_sang, goc_ma)
            bd = list(d["ban_dich"])
            phu = {k: v for k, v in d.items()
                   if k not in ("ban_dich", "ngan_sach")}
        elif arm == "soat":
            from app.ai import dich as D
            d = D.dich_va_soat(cau, dich_sang, goc_ma)
            bd = list(d["ban_dich"])
            phu = {k: v for k, v in d.items()
                   if k not in ("ban_dich", "ngan_sach", "cau_cham")}
        else:
            raise SystemExit("arm lạ: " + arm)
    except Exception as e:                                    # noqa: BLE001
        loi = "%s: %s" % (type(e).__name__, e)
        bd = list(goc)
    finally:
        so.tat()
    giay = round(time.time() - t0, 2)

    f_goc = [i for i in range(len(goc)) if bd[i].strip() == goc[i].strip()]
    f_rong = [i for i in range(len(goc)) if not bd[i].strip()]
    e_he: dict = {}
    for i, t in enumerate(bd):
        h = C.he_chu(t)
        if h:
            e_he.setdefault(h, []).append(i)
    ten = "%s_%s_%s_l%d" % (arm, ma_video, dich_sang, lan)
    if model:
        ten = "%s@%s_%s_%s_l%d" % (arm, model.split("/")[-1], ma_video,
                                   dich_sang, lan)
    kq = {"video": ma_video, "dich_sang": dich_sang, "lan": lan, "arm": arm,
          "model": model, "so_cau": len(goc), "giay": giay, "loi": loi,
          "phu": phu, "goi": so.tom_tat(), "goi_chi_tiet": so.muc,
          "F_tra_nguyen_goc": f_goc, "F_rong": f_rong,
          "E_he_chu_la": e_he, "E_khong_dau_viet": [],
          "ban_dich": bd, "goc": goc}
    C.ghi(ten + ".json", kq)
    g = so.tom_tat()
    print("[%s] %ss · %d lượt gọi (cắt %d · lỗi %d) · mẻ lớn nhất %d câu · "
          "F %d · E %s%s"
          % (ten, giay, g["so_luot"], g["so_bi_cat"], g["so_loi"],
             max([m.get("so_muc", 0) for m in so.muc] or [0]),
             len(f_goc) + len(f_rong),
             {k: len(v) for k, v in e_he.items()},
             (" · phụ %s" % phu) if phu else ""))
    if loi:
        print("   LỖI:", loi)
    return kq


def _dich_loat_model(cau, dich_sang, goc_ma, model):
    """MỐC nhưng ép model khác — bọc `complete_json` để KHÔNG đẻ bản `_dich_loat`
    thứ hai (bản thứ hai là bản sẽ lệch khi ai đó sửa một bên)."""
    from app.ai import llm
    from app.core import thay_giong as TG
    cu = llm.complete_json

    def bao(prompt, system="", provider=None, model_=None):
        return cu(prompt, system=system, provider=provider, model=model)
    llm.complete_json = bao
    try:
        return TG._dich_loat(cau, dich_sang, goc_ma)
    finally:
        llm.complete_json = cu


if __name__ == "__main__":
    for v in sys.argv[1:]:
        p = v.split(":")
        chay_arm(p[0], p[1], p[2], int(p[3]), p[4] if len(p) > 4 else "")
