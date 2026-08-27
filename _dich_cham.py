# -*- coding: utf-8 -*-
"""THƯỚC CHẤM BẢN DỊCH — 3 thước ĐỘC LẬP, đừng gộp chúng lại.

1. **chrF (thuần code, TIỀN ĐỊNH, không vướng giấy phép)** — dịch bản dịch
   NGƯỢC về tiếng GỐC bằng một lượt gọi ĐỘC LẬP rồi so n-gram KÝ TỰ với câu
   gốc. Đây là thước sát nhất với chữ "khớp 99%" mà KHÔNG phải LLM tự chấm nó.
2. **LLM chấm trung thành 1-5 + LÝ DO + MÃ LỖI** — model chấm phải KHÁC model
   dịch, nếu không nó tự chấm nó.
3. **Đếm câu vào/ra + dò hệ chữ** — bắt mã F và mã E, thuần code (ở
   `_dich_do_chung.py`).

BẤT BIẾN: model chấm KHÁC model dịch. Gọi `kiem_thuoc()` TRƯỚC khi in bảng.
"""
from __future__ import annotations
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

#: Model CHẤM — khác hẳn họ model dịch (gpt-oss). Qwen còn là model gốc Trung
#: nên đọc câu gốc tiếng Trung là việc nó mạnh nhất.
MODEL_CHAM = "qwen/qwen3.8-27b"
#: Số câu mỗi lượt chấm. Trần TPM 8.000 -> prompt + max_tokens <= 8000.
CO_LO_CHAM = 20


def kiem_thuoc() -> str:
    """Model chấm PHẢI khác model dịch. Ném nếu cùng họ — bảng số vô nghĩa."""
    from config import settings
    ho_cham = MODEL_CHAM.split("/")[0]
    ho_dich = str(settings.GROQ_LLM_MODEL).split("/")[0]
    if ho_cham == ho_dich:
        raise RuntimeError(
            f"MODEL CHẤM «{MODEL_CHAM}» CÙNG HỌ với model dịch "
            f"«{settings.GROQ_LLM_MODEL}» — nó tự chấm nó, số vô nghĩa.")
    return MODEL_CHAM


# ---------------------------------------------------------------------- chrF
def _ngram(s: str, n: int) -> Counter:
    s = re.sub(r"\s+", "", s)
    return Counter(s[i:i + n] for i in range(max(0, len(s) - n + 1)))


def chrf(goc: str, thu: str, n_max: int = 6, beta: float = 2.0) -> float:
    """chrF (F-score n-gram KÝ TỰ) — 0..100. Thuần code, TIỀN ĐỊNH.

    Dùng KÝ TỰ chứ không dùng TỪ: nguồn là tiếng Trung, không có dấu cách.
    """
    goc, thu = str(goc or ""), str(thu or "")
    if not goc or not thu:
        return 0.0
    ps, rs = [], []
    for n in range(1, n_max + 1):
        a, b = _ngram(goc, n), _ngram(thu, n)
        if not a or not b:
            continue
        chung = sum((a & b).values())
        ps.append(chung / sum(b.values()))
        rs.append(chung / sum(a.values()))
    if not ps:
        return 0.0
    p, r = sum(ps) / len(ps), sum(rs) / len(rs)
    if p + r == 0:
        return 0.0
    b2 = beta * beta
    return round(100.0 * (1 + b2) * p * r / (b2 * p + r), 2)


# -------------------------------------------------- DỊCH NGƯỢC (lượt ĐỘC LẬP)
def dich_nguoc(dich, goc_ma: str, dich_ma: str, model: str = ""):
    """Dịch bản dịch NGƯỢC về tiếng gốc.

    **KHÔNG cho model thấy câu gốc** — thấy là nó chép lại câu gốc rồi mọi
    điểm đều đẹp (đúng bẫy "tự chấm mình").
    """
    from app.ai import llm
    from app.core.thay_giong import _ten_nn, _theo_nhan
    md = model or MODEL_CHAM
    # BỘ ĐO CŨNG RỚT ĐUÔI — đã đo: qwen một mình chỉ dịch ngược được 120/167.
    # Bỏ sót của BỘ ĐO đọc ra thành "không có lệch bậc" = kết luận NGƯỢC.
    # Nên có model DỰ PHÒNG (vẫn KHÁC model dịch 120b).
    chuoi = [md, "openai/gpt-oss-20b", md]
    ra = {}
    con = list(range(len(dich)))
    for _vong in range(len(chuoi)):
        if not con:
            break
        md = chuoi[_vong]
        moi = {}
        for k in range(0, len(con), CO_LO_CHAM):
            phan = con[k:k + CO_LO_CHAM]
            items = ['#%d: "%s"' % (i, dich[i][:300]) for i in phan]
            prompt = (
                "Dich cac cau %s sau sang %s.\n" % (_ten_nn(dich_ma),
                                                    _ten_nn(goc_ma))
                + "\n".join(items)
                + "\n\nQUY TAC:\n"
                  "- Dich SAT NGHIA, giu dung moi chi tiet, KHONG them bot.\n"
                  "- Khong giai thich, khong chu thich.\n"
                  "- Tra MANG JSON %d doi tuong " % len(phan)
                + '{"i": <dung so sau dau #>, "t": "<ban dich nguoc>"}.')
            try:
                d = llm.complete_json(
                    prompt, system="Ban la bien dich. CHI tra JSON thuan.",
                    model=md)
            except Exception:                              # noqa: BLE001
                continue
            for i, t in _theo_nhan(d, phan, "t").items():
                if isinstance(t, str) and t.strip():
                    moi[i] = t.strip()
        if not moi:
            break
        ra.update(moi)
        con = [i for i in range(len(dich)) if i not in ra]
    return [ra.get(i, "") for i in range(len(dich))]


# ------------------------------------------------------ LLM CHẤM 1-5 + LÝ DO
_MA_LOI = ("matchu", "sainghia", "cut", "them", "gungong", "roirac")


def cham_trung_thanh(goc, dich, goc_ma: str, dich_ma: str, model: str = ""):
    """Chấm TRUNG THÀNH 1-5 + LÝ DO + MÃ LỖI. Model KHÁC model dịch."""
    from app.ai import llm
    from app.core.thay_giong import _ten_nn, _mang_llm
    md = model or MODEL_CHAM
    ra = {}
    con = list(range(len(goc)))
    for _vong in range(3):
        if not con:
            break
        moi = {}
        for k in range(0, len(con), CO_LO_CHAM):
            phan = con[k:k + CO_LO_CHAM]
            items = ['#%d\n  GOC: "%s"\n  DICH: "%s"'
                     % (i, goc[i][:250], dich[i][:250]) for i in phan]
            prompt = (
                "Cham DO TRUNG THANH cua ban dich %s -> %s.\n"
                % (_ten_nn(goc_ma), _ten_nn(dich_ma))
                + "\n".join(items)
                + "\n\nTHANG 1-5, CANG CAO CANG TRUNG THANH:\n"
                  "- 5 = dung tron nghia, khong sot khong them, doc tu nhien.\n"
                  "- 4 = dung nghia, chi khac cach dien dat nho.\n"
                  "- 3 = hieu duoc nhung sot/lech mot y phu, hoac dich cung.\n"
                  "- 2 = SAI mot y chinh, hoac dich mat chu lam cau toi nghia.\n"
                  "- 1 = SAI HAN nghia / vo nghia / khong lien quan cau goc.\n\n"
                  'Kem "loi" = MOT ma trong: "" (khong loi) · "matchu" (dich '
                  'mat chu, khong hieu thanh ngu) · "sainghia" (sai nghia tu '
                  'khoa) · "cut" (thieu y) · "them" (bia them y) · "gungong" '
                  '(dung nghia nhung cau guong, khong phai van noi) · '
                  '"roirac" (roi rac, khong noi duoc voi cau quanh no).\n'
                  'Kem "vs" = ly do NGAN (duoi 15 chu).\n'
                  "Tra MANG JSON %d doi tuong " % len(phan)
                + '{"i": <so sau dau #>, "d": <1-5>, "loi": "<ma>", '
                  '"vs": "<ly do>"}.')
            try:
                d = llm.complete_json(
                    prompt,
                    system="Ban la nguoi soat ban dich chuyen nghiep, nghiem "
                           "khac. CHI tra JSON thuan.",
                    model=md)
            except Exception:                              # noqa: BLE001
                continue
            for o in _mang_llm(d):
                if not isinstance(o, dict):
                    continue
                try:
                    i = int(o.get("i"))
                    diem = float(o.get("d"))
                except (TypeError, ValueError):
                    continue
                if i in phan and i not in ra:
                    ml = str(o.get("loi") or "").strip().lower()
                    moi[i] = {"diem": diem,
                              "loi": ml if ml in _MA_LOI else "",
                              "vs": str(o.get("vs") or "")[:120]}
        if not moi:
            break
        ra.update(moi)
        con = [i for i in range(len(goc)) if i not in ra]
    return [ra.get(i, {"diem": None, "loi": "", "vs": "KHONG CHAM DUOC"})
            for i in range(len(goc))]


# ------------------------------------------------- CHẤM CHÍNH CÂU GỐC (mã A/B)
def cham_nguon(cau, goc_ma: str, model: str = ""):
    """Chấm CHÍNH BẢN CHÉP LỜI, KHÔNG đụng bản dịch — tách mã A và mã B.

    · `nghe` 1-5 = câu gốc có phải tiếng %s ĐÚNG, đọc lên hiểu được không
      (thấp = ASR nghe nhầm -> mã A; nguồn sai thì dịch không cứu được).
    · `tron` 1-5 = câu có TRỌN Ý một mình không, hay là MẨU bị chặt giữa ý
      (thấp = mã B, lỗi CẮT CÂU chứ không phải lỗi dịch).
    Model chấm được xem 2 câu TRƯỚC và 2 câu SAU để biết đâu là mẩu.
    """
    from app.ai import llm
    from app.core.thay_giong import _ten_nn, _mang_llm
    md = model or MODEL_CHAM
    goc = [c["text"] for c in cau]
    ra = {}
    con = list(range(len(goc)))
    for _vong in range(3):
        if not con:
            break
        moi = {}
        for k in range(0, len(con), CO_LO_CHAM):
            phan = con[k:k + CO_LO_CHAM]
            items = []
            for i in phan:
                truoc = " ".join(goc[max(0, i - 2):i]) or "(dau bai)"
                sau = " ".join(goc[i + 1:i + 3]) or "(cuoi bai)"
                items.append('#%d\n  TRUOC: "%s"\n  CAU: "%s"\n  SAU: "%s"'
                             % (i, truoc[:120], goc[i][:250], sau[:120]))
            prompt = (
                "Duoi day la ban CHEP LOI TU DONG (may nghe) mot video %s. "
                "Cham CHINH CAU GOC, KHONG dich.\n" % _ten_nn(goc_ma)
                + "\n".join(items)
                + "\n\nHAI DIEM RIENG BIET, moi diem 1-5, cang cao cang tot:\n"
                  '"nghe" = cau nay co phai %s DUNG khong: dung chinh ta, '
                  "dung tu, doc len hieu duoc va HOP voi cau TRUOC/SAU. "
                  "May nghe NHAM (ra chu dong am vo nghia, ten rieng sai, "
                  "cau khong ai noi the) thi cham 1-2.\n" % _ten_nn(goc_ma)
                + '"tron" = cau nay co TRON Y khi dung MOT MINH khong. '
                  "5 = cau hoan chinh. 3 = thieu chu ngu nhung van doan duoc. "
                  "1-2 = MAU bi chat giua y (menh de phu, trang ngu, nua cau), "
                  "dich rieng ra thi vo nghia.\n"
                  'Kem "vs" = ly do NGAN (duoi 12 chu).\n'
                  "Tra MANG JSON %d doi tuong " % len(phan)
                + '{"i": <so sau dau #>, "nghe": <1-5>, "tron": <1-5>, '
                  '"vs": "<ly do>"}.')
            try:
                d = llm.complete_json(
                    prompt,
                    system="Ban la nguoi ban ngu %s, soat ban chep loi tu "
                           "dong. CHI tra JSON thuan." % _ten_nn(goc_ma),
                    model=md)
            except Exception:                              # noqa: BLE001
                continue
            for o in _mang_llm(d):
                if not isinstance(o, dict):
                    continue
                try:
                    i = int(o.get("i"))
                    ng = float(o.get("nghe"))
                    tr = float(o.get("tron"))
                except (TypeError, ValueError):
                    continue
                if i in phan and i not in ra:
                    moi[i] = {"nghe": ng, "tron": tr,
                              "vs": str(o.get("vs") or "")[:120]}
        if not moi:
            break
        ra.update(moi)
        con = [i for i in range(len(goc)) if i not in ra]
    return [ra.get(i, {"nghe": None, "tron": None, "vs": "KHONG CHAM DUOC"})
            for i in range(len(goc))]
