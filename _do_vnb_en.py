# -*- coding: utf-8 -*-
"""GIỌNG **NHÂN BẢN** ĐỌC TIẾNG ANH: VieNeu (`vnb:`) vs Chatterbox (`cb:`).

Anh Hùng (26/08/2026): *"âm thanh giọng nói oke mà CÁCH PHÁT ÂM BỊ LỖI rồi, khi
clone giọng tiếng Anh nó đọc như thằng mới học ấy, nói không lưu loát không
chuẩn chữ"*. Màn hình anh ấy: **Ngôn ngữ đích = Tiếng Anh**, **Giọng đọc =
`adam Clone (giọng nhân bản, VieNeu, ...)`** tức tiền tố **`vnb:`**.

═══════════════════════════════════════════════════════════════════════════
VÌ SAO PHẢI ĐO LẠI — SỐ CŨ ĐO TRÊN GIỌNG **DỰNG SẴN**
═══════════════════════════════════════════════════════════════════════════
`_kq_adam_en.txt` (19/08) đo `vn:Adam` = một trong 20 giọng DỰNG SẴN của
VieNeu (có `speaker_emb` học sẵn). Anh Hùng dùng `vnb:` = **nhân bản từ file
mẫu**, đường mã khác hẳn (`infer(ref_audio=...)` thay vì `voice="Adam"`).
Chưa ai đo đường đó trên tiếng Anh. Hai bảng KHÔNG thay nhau được.

═══════════════════════════════════════════════════════════════════════════
GHÉP CẶP: MỘT MẪU, BA MÁY — VÀ VÌ SAO ĐÓ LÀ ĐIỀU KIỆN BẮT BUỘC
═══════════════════════════════════════════════════════════════════════════
`giong_chatter` đã đo được (26/08): **MẪU kéo nhịp đọc, không riêng gì TIẾNG**
— cùng 12 câu tiếng Anh, mẫu `en-US-Andrew` ra 1,03x còn mẫu `A_nu` ra 1,32x.
Nên hai arm nhân bản ở đây dùng **CÙNG MỘT FILE mẫu, từng byte** (không sinh
lại giữa chừng: edge-tts KHÔNG trả về audio giống từng byte qua các ngày, và
lượt đo 21/08 đã kết luận nhầm "không tái hiện được" đúng vì chuyện này).

  · `VNB_en` — `vnb:<mẫu>`      × 34 câu Anh + 24 token rời  (đường ANH HÙNG)
  · `CB_en`  — `cb:en|<mẫu>`    × cùng bộ câu                (đường thay thế)
  · `edge_en`— `en-US-AriaNeural` × cùng bộ câu — **TRẦN ĐỐI CHỨNG**, lấy lại
    từ cache lượt 19/08 nên là **ĐÚNG file tiếng** đã sinh ra bảng Adam.

**KHÔNG có TRẦN thì mọi con số vô nghĩa** — 5% sai chữ là tốt hay tệ chỉ trả
lời được khi biết máy đọc bản ngữ đạt bao nhiêu trên CHÍNH bộ câu này.

═══════════════════════════════════════════════════════════════════════════
RANH GIỚI CỨNG — MẪU PHẢI LÀ GIỌNG MÁY
═══════════════════════════════════════════════════════════════════════════
Mẫu ở đây do **edge-tts** sinh ra. **KHÔNG dùng `_mau_giong/adam_clone.wav`**
(bản sao giọng Adam của ElevenLabs — một giọng thương mại đang được bán, mà
app này BÁN RA), KHÔNG nhân bản giọng người thật nào. Đây là cùng ranh giới
`_do_adam_en.py` đã đặt, không phải luật mới.

═══════════════════════════════════════════════════════════════════════════
BẪY LỚN NHẤT CỦA LƯỢT NÀY: **LÙI ÊM VỀ edge-tts**
═══════════════════════════════════════════════════════════════════════════
`dubbing._synth_all` cố tình lùi về edge-tts khi máy nhân bản hỏng CẢ LOẠT
(`_lui_chatter`) — đúng thiết kế cho người dùng, nhưng với phép ĐO thì nó là
**thảm hoạ**: bảng sẽ ghi "Chatterbox 0,0% sai chữ" trong khi thứ vừa đọc là
edge-tts. Nên mỗi arm đều bị **CANH ĐỘNG CƠ**: bọc `giong_vieneu.doc_loat` và
`giong_chatter.doc_loat`, đếm số câu THẬT SỰ do máy đó trả ra. Arm nào không
khớp -> đánh dấu **KHÔNG HỢP LỆ** và số của nó không được vào kết luận.
Không có chốt này thì phép đo tự cấp chứng nhận cho kết quả ngược hẳn.

═══════════════════════════════════════════════════════════════════════════
DÙNG LẠI BỘ CHẤM CŨ, KHÔNG VIẾT BỘ THỨ HAI
═══════════════════════════════════════════════════════════════════════════
Corpus (`_bo_cau_thu_doc`), WER, chấm token (`_do_doc_sai`), cache TTS, cột
bịa-chữ và lề-im đều lấy thẳng từ `_do_vieneu_en.py` + `_do_adam_en.py`. Viết
bộ chấm thứ hai là đẻ ra hai bảng số không so được với nhau.

VieNeu **KHÔNG tiền định** -> arm `VNB_en` chạy **2 lượt**, bảng ghi **DẢI**.
Chatterbox đo được là **tiền định theo (chữ, mẫu, tiếng, seed)** — vẫn chạy 2
lượt để **KIỂM lời đó**, chứ không tin sẵn.

Chạy:  .venv\\Scripts\\python -u _do_vnb_en.py
Env:   BQ_VNB_VONG=2 · BQ_VNB_LAI=1 (bỏ cache) · BQ_VNB_ARM=VNB_en,CB_en
"""
from __future__ import annotations

import json
import os
import statistics as st
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

import _do_adam_en as DA                                        # noqa: E402
import _do_vieneu_en as DV                                      # noqa: E402
from _do_doc_sai import tu_kiem_bo_cham                         # noqa: E402

HOP_MAU = REPO / "_do_vnb_en"
KQ_JSON = REPO / "_kq_vnb_en.json"

#: Câu đọc để LÀM MẪU. Tiếng ANH, vì mẫu của anh Hùng cũng là một đoạn ghi âm
#: tiếng Anh — mẫu tiếng Việt là đo một arm khác.
CAU_MAU = ("This is a short recording used as a voice sample. I am reading a "
           "few sentences at a normal pace so that the model has enough "
           "material to work with. The weather today is clear and cold, and "
           "the streets are unusually quiet this morning.")

#: Giọng edge-tts sinh mẫu. Nam, tiếng Anh Mỹ — vai trò gần nhất với mẫu Adam
#: của anh Hùng mà KHÔNG đụng tới file giọng thương mại.
GIONG_MAU = "en-US-AndrewMultilingualNeural"

NHAN = {
    "VNB_en": "vnb: NHÂN BẢN qua VieNeu x ANH  <= ANH HÙNG ĐANG ĐI",
    "CB_en":  "cb: NHÂN BẢN qua Chatterbox x ANH",
    "edge_en": "edge Aria x ANH (TRẦN ĐỐI CHỨNG)",
    "AD_en":  "vn:Adam DỰNG SẴN x ANH (bảng 19/08)",
}

THU_TU = ["VNB_en", "CB_en", "edge_en", "AD_en"]


# ------------------------------------------------------------------ mẫu giọng
def lam_mau() -> Path:
    """Sinh (một lần) file mẫu 24 kHz mono. **GIỮ LẠI FILE**, không sinh lại.

    Bài học `giong_chatter` 26/08: hai lượt edge-tts cùng chữ + cùng giọng cho
    ra hai file **cùng cỡ, khác MD5**, và máy nhân bản đọc theo BYTE của mẫu ->
    sinh lại mẫu là đo một arm KHÁC. Nên nếu file đã có thì dùng lại y nguyên.
    """
    HOP_MAU.mkdir(parents=True, exist_ok=True)
    ra = HOP_MAU / "mau_en_andrew.wav"
    if ra.exists() and ra.stat().st_size > 4000:
        return ra
    import asyncio

    import edge_tts
    mp3 = ra.with_suffix(".mp3")

    async def _go() -> None:
        await edge_tts.Communicate(CAU_MAU, GIONG_MAU).save(str(mp3))

    asyncio.run(_go())
    from config import settings
    ff = str(getattr(settings, "FFMPEG_PATH", "") or "ffmpeg")
    subprocess.run([ff, "-y", "-v", "error", "-i", str(mp3),
                    "-vn", "-ac", "1", "-ar", "24000", str(ra)],
                   capture_output=True, check=False)
    if not (ra.exists() and ra.stat().st_size > 4000):
        raise RuntimeError("không sinh được file mẫu")
    return ra


# ------------------------------------------------------------- canh động cơ
class CanhDongCo:
    """Đếm câu THẬT SỰ do từng máy nhân bản trả ra, trong một khối `with`.

    Đây là chốt chống **lùi êm về edge-tts** — xem khối ghi chú đầu file. Bọc
    ở tầng `giong_*.doc_loat` chứ không ở `dubbing._synth_all`: cửa chung là
    đúng thứ đang được ĐO, vá nó là đo một đường khác.
    """

    def __init__(self) -> None:
        self.dem: dict[str, int] = {"vieneu": 0, "chatter": 0}
        self._cu: dict = {}

    def __enter__(self) -> "CanhDongCo":
        from app.core import giong_chatter, giong_vieneu
        self._cu = {"vn": giong_vieneu.doc_loat, "cb": giong_chatter.doc_loat}

        def bao(ten: str, that: object):
            def _g(*a, **k):
                r = that(*a, **k)                      # type: ignore[operator]
                ok = r[0] if isinstance(r, tuple) else r
                try:
                    self.dem[ten] += sum(1 for x in ok if x)
                except Exception:                       # noqa: BLE001
                    pass
                return r
            return _g

        giong_vieneu.doc_loat = bao("vieneu", self._cu["vn"])   # type: ignore
        giong_chatter.doc_loat = bao("chatter", self._cu["cb"])  # type: ignore
        return self

    def __exit__(self, *_a) -> None:
        from app.core import giong_chatter, giong_vieneu
        giong_vieneu.doc_loat = self._cu["vn"]                  # type: ignore
        giong_chatter.doc_loat = self._cu["cb"]                 # type: ignore


#: arm -> máy PHẢI đọc nó. `edge_en` không có máy nhân bản nào (đúng như vậy).
MAY_CUA_ARM = {"VNB_en": "vieneu", "CB_en": "chatter"}


# -------------------------------------------------------------------- chạy
def main() -> int:
    DV.HOP.mkdir(parents=True, exist_ok=True)
    cache: dict = {}
    if DV.CACHE.exists():
        try:
            cache = json.loads(DV.CACHE.read_text(encoding="utf-8"))
        except Exception:                                       # noqa: BLE001
            cache = {}
    lam_lai = os.environ.get("BQ_VNB_LAI") == "1"
    so_vong = int(os.environ.get("BQ_VNB_VONG", "2"))
    chi = [x.strip() for x in (os.environ.get("BQ_VNB_ARM") or "").split(",")
           if x.strip()]

    print("=" * 78)
    print("GIỌNG NHÂN BẢN ĐỌC TIẾNG ANH — `vnb:` (VieNeu) vs `cb:` (Chatterbox)")
    print("=" * 78)
    mau = lam_mau()
    print(f"mẫu CHUNG cho cả hai arm: {mau.name} · {mau.stat().st_size} byte "
          f"· sinh bằng edge-tts {GIONG_MAU}")
    print(f"corpus: `_bo_cau_thu_doc.py` · en {len(DV.CORPUS['en'])} câu / "
          f"{len(DV.token_theo_nn('en'))} token rời")

    from app.core import giong_chatter as GC
    tt = GC.tinh_trang()
    print(f"Chatterbox: cài={tt['co']} · GPU NVIDIA={tt['gpu']}")

    print("\nTỰ KIỂM BỘ CHẤM (6 cặp đã biết đáp án)")
    if not bool(tu_kiem_bo_cham()):
        print("  DỪNG: bộ chấm lệch -> mọi số dưới đây vô nghĩa")
        return 2
    print("  -> bộ chấm KHỚP HẾT")

    arms = [("VNB_en", f"vnb:{mau}", "en"), ("CB_en", f"cb:en|{mau}", "en")]
    arms = [a for a in arms if not chi or a[0] in chi]

    # `edge_en` đo ĐỌC RỜI sẵn trong `DV.ARM_ROI`; hai arm mới phải khai thêm,
    # nếu không `chay_arm` bỏ hẳn cột "token ĐỌC RỜI" — cột THẬT của phép đo.
    DV.ARM_ROI = tuple(DV.ARM_ROI) + ("VNB_en", "CB_en")
    DV.NHAN_ARM.update(NHAN)

    tat: dict[str, list[dict]] = {}
    hop_le: dict[str, bool] = {}
    for vong in range(1, so_vong + 1):
        # ĐAN XEN: chạy hết arm này rồi mới arm kia thì arm sau gánh phần máy
        # đã nóng (bài học đo A/B trên đúng cái máy này, đã sai 2 lần).
        thu = arms[(vong - 1) % max(1, len(arms)):] + \
            arms[:(vong - 1) % max(1, len(arms))]
        print(f"\n--- VÒNG {vong}/{so_vong} · thứ tự: "
              f"{', '.join(a[0] for a in thu)} ---")
        for ten, voice, nn in thu:
            khoa = f"{ten}|{voice}|{nn}|v{vong}"
            da_co = bool(cache.get(khoa)) and not lam_lai
            with CanhDongCo() as canh:
                t0 = time.time()
                kq = DV.chay_arm(ten, voice, nn, vong, cache, lam_lai)
                _giay = time.time() - t0
            # CANH ĐỘNG CƠ: chỉ nói được khi lượt này ĐỌC THẬT (lấy cache thì
            # không có gì để đếm) — nên arm dùng cache thừa hưởng kết luận của
            # lượt đã đọc, KHÔNG tự cho mình là hợp lệ.
            can = MAY_CUA_ARM.get(ten, "")
            if da_co:
                print(f"  [{ten} v{vong}] (cache) — canh động cơ: bỏ qua")
                hop_le.setdefault(ten, True)
            elif can:
                n_cau = len(DV.CORPUS[nn])
                n_tok = len(DV.token_theo_nn(nn)) if ten in DV.ARM_ROI else 0
                du = canh.dem.get(can, 0) >= (n_cau + n_tok)
                khac = {k: v for k, v in canh.dem.items() if k != can and v}
                print(f"  [{ten} v{vong}] CANH ĐỘNG CƠ: {can} trả "
                      f"{canh.dem.get(can, 0)}/{n_cau + n_tok} câu"
                      + (f" · máy khác cũng chạy: {khac}" if khac else "")
                      + f" -> {'HỢP LỆ' if du else 'KHÔNG HỢP LỆ (lùi edge?)'}")
                hop_le[ten] = hop_le.get(ten, True) and du
            c = DV.cham(kq)
            thay = chen = thieu = tong = 0
            for h in kq["cau"]:
                if not h["doc_duoc"]:
                    continue
                t_, c_, k_, n_ = DA.dem_op(h["cau"], h["chep"])
                thay += t_
                chen += c_
                thieu += k_
                tong += n_
            c["thay"], c["chen"], c["thieu"], c["tu"] = thay, chen, thieu, tong
            le_d, le_c, _n = DA.do_le(ten, vong)
            c["le_dau"], c["le_cuoi"] = le_d, le_c
            c["giay_cau"] = kq.get("giay_cau")
            c["giay_moi_cau"] = (float(kq.get("giay_cau") or 0.0)
                                 / max(1, len(kq["cau"])))
            tat.setdefault(ten, []).append(c)
            print(f"  [{ten} v{vong}] token trong câu {c['tc_sai']}/{c['tc_n']}"
                  f" · đọc rời {c['tr_sai']}/{c['tr_n']} · bịa {chen}/{tong} từ"
                  f" · WER {c['wer']:.1f}% · nhãn nn {c['nn_dung']}/{c['nn_n']}"
                  f" · {c['giay_moi_cau']:.1f} s/câu")

    # ---- arm ĐỐI CHỨNG lấy thẳng từ cache lượt 19/08 (KHÔNG đọc lại)
    for ten, voice, nn in (("edge_en", "en-US-AriaNeural", "en"),
                           ("AD_en", "vn:Adam", "en")):
        if chi and ten not in chi:
            continue
        for v in (1, 2):
            if not cache.get(f"{ten}|{voice}|{nn}|v{v}"):
                continue
            kq = DV.chay_arm(ten, voice, nn, v, cache, False)
            c = DV.cham(kq)
            thay = chen = thieu = tong = 0
            for h in kq["cau"]:
                if not h["doc_duoc"]:
                    continue
                t_, c_, k_, n_ = DA.dem_op(h["cau"], h["chep"])
                thay += t_
                chen += c_
                thieu += k_
                tong += n_
            c["thay"], c["chen"], c["thieu"], c["tu"] = thay, chen, thieu, tong
            c["giay_moi_cau"] = (float(kq.get("giay_cau") or 0.0)
                                 / max(1, len(kq["cau"])))
            tat.setdefault(ten, []).append(c)
        hop_le.setdefault(ten, True)

    # -------------------------------------------------------------- BẢNG
    print("\n" + "=" * 78)
    print("BẢNG 1 — SAI CHỮ / BỊA CHỮ / WER / NHÃN TIẾNG / GIÂY MỖI CÂU")
    print("=" * 78)
    print(f"{'arm':<46}{'TRONG CÂU %':>17}{'ĐỌC RỜI %':>17}"
          f"{'bịa %':>13}{'WER %':>17}{'nhãn':>9}{'s/câu':>8}")
    for ten in THU_TU:
        rs = tat.get(ten) or []
        if not rs:
            continue
        tc = DA.dai([100 * r["tc_sai"] / max(1, r["tc_n"]) for r in rs])
        tr = (DA.dai([100 * r["tr_sai"] / max(1, r["tr_n"]) for r in rs])
              if rs[0]["tr_n"] else "—")
        bi = DA.dai([100 * r["chen"] / max(1, r["tu"]) for r in rs])
        w = DA.dai([r["wer"] for r in rs])
        nn = "/".join(f"{r['nn_dung']}/{r['nn_n']}" for r in rs)
        gc = st.mean([r.get("giay_moi_cau") or 0.0 for r in rs])
        co = "" if hop_le.get(ten, True) else "  [KHÔNG HỢP LỆ]"
        print(f"{NHAN.get(ten, ten) + co:<46}{tc:>17}{tr:>17}{bi:>13}"
              f"{w:>17}{nn:>9}{gc:>8.1f}")
    for ten in THU_TU:
        rs = tat.get(ten) or []
        if rs and rs[0].get("nn_khac"):
            print(f"  nhãn LẠ ở {NHAN.get(ten, ten)}: "
                  f"{', '.join(rs[0]['nn_khac'])}")

    print("\n" + "=" * 78)
    print("BẢNG 2 — TOKEN HỎNG Ở TỪNG ARM MÀ TRẦN edge ĐỌC ĐƯỢC")
    print("=" * 78)
    if tat.get("edge_en"):
        for ten in ("VNB_en", "CB_en"):
            if not tat.get(ten):
                continue
            print(f"\n  ### {NHAN[ten]}")
            for nhan_cot, khoa in (("TRONG CÂU", "tc"), ("ĐỌC RỜI", "tr")):
                tran_ok = {x["token"] for x in tat["edge_en"][0][khoa]
                           if x["dung"]}
                hong: dict[str, str] = {}
                for r in tat[ten]:
                    for x in r[khoa]:
                        if not x["dung"] and x["token"] in tran_ok:
                            hong.setdefault(x["token"], x["chep"][:70])
                print(f"    {nhan_cot}: {len(hong)} token")
                for tk, ch in sorted(hong.items()):
                    print(f"      «{tk}» -> máy nghe chép «{ch}»")

    print("\n" + "=" * 78)
    print("BẢNG 3 — TIỀN ĐỊNH? (hai lượt có ra CÙNG số không)")
    print("=" * 78)
    for ten in ("VNB_en", "CB_en"):
        rs = tat.get(ten) or []
        if len(rs) < 2:
            print(f"  {ten}: chỉ 1 lượt -> không kết luận được")
            continue
        giong = all(abs(rs[0][k] - rs[1][k]) < 1e-9
                    for k in ("wer",)) and rs[0]["tc_sai"] == rs[1]["tc_sai"]
        print(f"  {ten}: WER {rs[0]['wer']:.2f} vs {rs[1]['wer']:.2f} · "
              f"token sai {rs[0]['tc_sai']} vs {rs[1]['tc_sai']} -> "
              f"{'TIỀN ĐỊNH' if giong else 'KHÔNG tiền định'}")

    KQ_JSON.write_text(json.dumps(
        {"arm": {k: [{kk: vv for kk, vv in r.items() if kk not in ("tc", "tr")}
                     for r in v] for k, v in tat.items()},
         "hop_le": hop_le, "mau": str(mau), "giong_mau": GIONG_MAU,
         "luc": time.strftime("%Y-%m-%d %H:%M")},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nSố thô: {KQ_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
