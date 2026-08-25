# -*- coding: utf-8 -*-
"""ĐO THẬT bộ chữa viết tắt trên **VieNeu** (đường giọng nhân bản) — MẪU NHỎ.

VÌ SAO PHẢI ĐO: bảng `doc_viet_tat.CHU_ANH` được hiệu chuẩn trên **edge-tts**.
Chuyển sang VieNeu là chuyển sang một MODEL ÂM KHÁC; lập luận "cùng tiếng Việt
nên đọc giống nhau" nghe hợp lý nhưng đó đúng là loại lập luận đã sai một lần
(*"đọc mã tới `lang='vi'` rồi kết luận là DỪNG QUÁ SỚM"*, `_kq_adam_en.txt`).

NÓI THẲNG VỀ CỠ MẪU: **2 câu · 1 lượt mỗi arm · KHÔNG đan xen**. Máy anh Hùng
đang chạy app thật (`BQHungVideo.exe`) nên lượt đo phải nhẹ. Đây là **phép DÒ**
để loại sớm ca "bản vá làm hỏng thêm", KHÔNG phải bảng số để khoe tỉ lệ.

HAI ARM ĐI CHUNG ĐÚNG MỘT CỬA `dubbing._synth_all_words`, khác nhau đúng một
biến môi trường:
  · `BQ_VIET_TAT=0` -> arm **THÔ** = hành vi hôm nay (chưa vá)
  · mặc định        -> arm **ĐÃ ĐỔI** = hành vi sau bản vá
Nhờ vậy mọi thứ khác (model, giọng, gióng hàng, ép khung) giống hệt nhau.

THƯỚC: Groq `whisper-large-v3` chép ngược chính file tiếng vừa đọc, rồi hỏi
token `GDP` / `CEO` có hiện ra không. **Máy nghe là MÔ HÌNH NGÔN NGỮ nên nó
chữa hộ máy đọc** (bài học `_do_doc_sai.py` vs `_do_doc_roi.py`) — vì vậy đây
là thước DỄ DÃI: arm thô mà đã trượt thì bệnh là thật.

  .venv\\Scripts\\python -u _do_viet_tat_vieneu.py
"""
from __future__ import annotations

import asyncio
import os
import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                        # noqa: BLE001
        pass

#: ĐÚNG 6 TTOKEN của bộ đã hiệu chuẩn trên edge-tts (`_do_phien_am.py`) —
#: `AI` `MV` `CEO` `GDP` `OST` `USB`. Dùng lại y nguyên để hai bảng so được
#: với nhau; đổi bộ token là hai bảng nói về hai thứ khác nhau.
CAU = [
    "GDP của cả nước năm nay tăng khá mạnh.",
    "Vị CEO này giá gì cũng nghĩ ra được.",
    "Anh nhớ cắm cái USB vào máy giúp tôi nhé.",
    "MV mới của cô ấy đạt triệu lượt xem sau một ngày.",
    "Công nghệ AI đang thay đổi cách chúng ta làm việc.",
    "Bài OST của phim này rất hay, nghe mãi không chán.",
]
TOKEN = ["GDP", "CEO", "USB", "MV", "AI", "OST"]
VONG = 2                          # 2 vòng ĐAN XEN: VieNeu KHÔNG tiền định
                                  # (một lượt đọc rồi báo số là tự lừa mình).
#: Giọng đo. Mặc định là VieNeu DỰNG SẴN; truyền mã giọng ở tham số dòng lệnh
#: để đo đúng đường NHÂN BẢN (`vnb:<file mẫu>`) — đó mới là đường anh Hùng
#: kêu. Hai đường chung `doc_loat` / `_lay_moc`, khác đúng ở `voice=` thay vì
#: `ref_audio=`, nên phải đo CẢ HAI: chất lượng bản sao thấp hơn hẳn bản dựng
#: sẵn (mẫu điện thoại đo được 21-31% sai so với 7,7%).
#: `vnb:AUTO` -> tự sinh mẫu bằng edge-tts rồi đo đường NHÂN BẢN. Phải có chế
#: độ này vì `_mau_giong/*.wav` trên máy dev chỉ là **fixture 4 byte** của một
#: cổng khác -> đo thẳng vào đó ra "KHÔNG ra file" ở CẢ HAI arm, tức bảng số
#: TỰ ĐẠT vì lý do NGƯỢC HẲN (không có tiếng thì không có gì để sai).
GIONG = sys.argv[1] if len(sys.argv) > 1 else "vn:Ngọc Huyền"
SB = REPO / f"bq_do_viettat_vn_{os.getpid()}"


def sinh_mau(d: Path) -> str:
    """Sinh MẪU GIỌNG bằng edge-tts để đo đường `vnb:`. Trả đường dẫn WAV.

    Mẫu là **GIẢ LẬP**, đúng tiền lệ `_do_giong_toi.py` — và là ca DỄ NHẤT
    (mẫu sạch tuyệt đối). Chưa đo trên giọng thật của anh Hùng.
    """
    import subprocess
    from app.core import dubbing as DUB
    from config import settings
    d.mkdir(parents=True, exist_ok=True)
    mp3, wav = d / "mau.mp3", d / "mau.wav"
    cau = ("Hôm nay trời rất đẹp, tôi muốn kể cho các bạn nghe một câu chuyện "
           "khá thú vị mà tôi vừa mới trải qua ngày hôm qua.")
    if not DUB.synth_demo("vi-VN-NamMinhNeural", mp3, text=cau):
        raise RuntimeError("edge-tts không sinh được mẫu giọng")
    r = subprocess.run([settings.FFMPEG_PATH, "-y", "-hide_banner",
                        "-loglevel", "error", "-i", str(mp3),
                        "-ac", "1", "-ar", "24000", str(wav)],
                       capture_output=True, text=True)
    if r.returncode != 0 or not wav.exists() or wav.stat().st_size < 10000:
        raise RuntimeError(f"ffmpeg đổi mẫu hỏng (rc={r.returncode})")
    print(f"  mẫu GIẢ LẬP: {wav} ({wav.stat().st_size} byte)")
    return str(wav)


def chep_nguoc(wav: str) -> str:
    """Groq chép ngược 1 file tiếng -> chữ. Rỗng nếu không gọi được."""
    from openai import OpenAI
    from app.ai import llm
    from config import settings
    for key in llm.pick_keys("groq"):
        try:
            cl = OpenAI(api_key=key,
                        base_url="https://api.groq.com/openai/v1",
                        timeout=180, max_retries=1)
            with open(wav, "rb") as f:
                r = cl.audio.transcriptions.create(
                    file=f, model=settings.GROQ_WHISPER_MODEL,
                    response_format="json", language="vi")
            llm.mark_ok("groq", key)
            return (getattr(r, "text", "") or "").strip()
        except Exception as e:                               # noqa: BLE001
            print(f"    (key hỏng: {type(e).__name__})", flush=True)
    return ""


def mot_arm(ten: str, tat: bool) -> dict:
    """Chạy ĐÚNG cửa chung `_synth_all_words` một lượt. Trả số đo của arm."""
    from app.core import dubbing as DUB
    from app.core import doc_viet_tat as DVT
    # VieNeu MẶC ĐỊNH TẮT (số đo dưới chính là lý do), nên arm "ĐÃ ĐỔI" phải
    # bật công tắc đo `BQ_VIET_TAT_VN=1`. Thiếu dòng này thì HAI ARM GIỐNG HỆT
    # NHAU và bảng ra "TỐT LÊN 0 · TỆ ĐI 0" — TỰ ĐẠT vì lý do NGƯỢC HẲN. Mục
    # "chữ GỬI có đổi thật không" ở cuối là chốt bắt đúng ca đó.
    cu = os.environ.get("BQ_VIET_TAT")
    cu_vn = os.environ.get("BQ_VIET_TAT_VN")
    if tat:
        os.environ["BQ_VIET_TAT"] = "0"
        os.environ.pop("BQ_VIET_TAT_VN", None)
    else:
        os.environ.pop("BQ_VIET_TAT", None)
        os.environ["BQ_VIET_TAT_VN"] = "1"
    d = SB / ten
    d.mkdir(parents=True, exist_ok=True)
    paths = [str(d / f"c{i}.wav") for i in range(len(CAU))]
    t0 = time.time()
    try:
        gui, _thay = DVT.sua_loat(CAU, GIONG)       # đúng thứ cửa chung gửi đi
        ok, moc = asyncio.run(DUB._synth_all_words(CAU, GIONG, paths))
    finally:
        for ten_b, gt in (("BQ_VIET_TAT", cu), ("BQ_VIET_TAT_VN", cu_vn)):
            if gt is None:
                os.environ.pop(ten_b, None)
            else:
                os.environ[ten_b] = gt
    giay = time.time() - t0
    ra = {"ten": ten, "gui": gui, "ok": ok, "moc": moc, "giay": giay,
          "chep": [], "co_token": [], "co_moc": []}
    for i, p in enumerate(paths):
        if not (ok[i] and os.path.exists(p) and os.path.getsize(p) > 1000):
            ra["chep"].append("(KHÔNG ra file)")
            ra["co_token"].append(False)
            ra["co_moc"].append(False)
            continue
        txt = chep_nguoc(p)
        ra["chep"].append(txt)
        ra["co_token"].append(TOKEN[i].lower() in txt.lower())
        ra["co_moc"].append(any(str(m[2]) == TOKEN[i] for m in moc[i]))
    return ra


def main() -> int:                                           # noqa: C901
    global GIONG
    from app.core import giong_vieneu as VN
    from app.core import giong_hang as GH
    print("=" * 72)
    print("ĐO THẬT — viết tắt trên VieNeu (MẪU NHỎ: 2 câu · 1 lượt/arm)")
    print("=" * 72)
    tt = VN.tinh_trang_vieneu()
    print(f"VieNeu có = {tt.get('co')} · thiếu = {tt.get('thieu')}")
    print(f"gióng hàng có = {GH.co_giong_hang()} · giọng = {GIONG}")
    if not tt.get("co"):
        print("KHÔNG có VieNeu trên máy này -> KHÔNG đo được, dừng.")
        return 2

    SB.mkdir(parents=True, exist_ok=True)
    try:
        if GIONG.strip().lower() == "vnb:auto":
            GIONG = "vnb:" + sinh_mau(SB / "mau")
            print(f"giọng đo (nhân bản, mẫu giả lập) = {GIONG}")
        tho_all: list = []
        doi_all: list = []
        for v in range(VONG):
            for ten, tat in (("THÔ", True), ("ĐÃ ĐỔI", False)):
                print(f"\n--- vòng {v + 1} · arm {ten} ---", flush=True)
                r = mot_arm(("tho" if tat else "doi") + str(v), tat)
                (tho_all if tat else doi_all).append(r)
                for i in range(len(CAU)):
                    print(f"  «{TOKEN[i]}» gửi «{r['gui'][i][:34]}...» -> "
                          f"nghe «{r['chep'][i][:38]}» -> "
                          f"{'ĐÚNG' if r['co_token'][i] else 'SAI '}"
                          f" · mốc gốc "
                          f"{'CÓ' if r['co_moc'][i] else 'KHÔNG'}")
                print(f"  ({r['giay']:.1f} giây cả arm, kể cả nạp model)")

        print("\n" + "=" * 72)
        print(f"BẢNG — {len(CAU)} token × {VONG} vòng ĐAN XEN "
              f"(= {len(CAU) * VONG} phép so GHÉP CẶP mỗi arm)")
        print("=" * 72)
        n = len(CAU) * VONG
        s_tho = sum(sum(r["co_token"]) for r in tho_all)
        s_doi = sum(sum(r["co_token"]) for r in doi_all)
        m_tho = sum(sum(r["co_moc"]) for r in tho_all)
        m_doi = sum(sum(r["co_moc"]) for r in doi_all)
        print(f"{'arm':<34}{'token nghe ĐÚNG':>18}{'mốc về token gốc':>20}")
        print(f"{'THÔ (hành vi hôm nay)':<34}{s_tho:>13}/{n}{m_tho:>15}/{n}")
        print(f"{'ĐÃ ĐỔI (sau bản vá)':<34}{s_doi:>13}/{n}{m_doi:>15}/{n}")

        # GHÉP CẶP từng token từng vòng — đúng cách `_do_phien_am.py` đã chấm.
        # Tổng số che mất chiều: phải biết TỐT LÊN mấy cái, TỆ ĐI mấy cái.
        tot = te = y_nguyen = 0
        chi_tiet: list = []
        for v in range(VONG):
            for i in range(len(CAU)):
                a = tho_all[v]["co_token"][i]
                b = doi_all[v]["co_token"][i]
                if a == b:
                    y_nguyen += 1
                elif b and not a:
                    tot += 1
                    chi_tiet.append(f"TỐT LÊN «{TOKEN[i]}» vòng {v + 1}")
                else:
                    te += 1
                    chi_tiet.append(f"TỆ ĐI  «{TOKEN[i]}» vòng {v + 1}: "
                                    f"thô «{tho_all[v]['chep'][i][:34]}» -> "
                                    f"đổi «{doi_all[v]['chep'][i][:34]}»")
        print(f"\nGHÉP CẶP: TỐT LÊN {tot} · TỆ ĐI {te} · y nguyên {y_nguyen}")
        for d in chi_tiet:
            print("   " + d)
        print()
        print("ĐỌC BẢNG:")
        print(f"  · chữ GỬI máy đọc có đổi thật không: "
              f"{'CÓ' if doi_all[0]['gui'] != list(CAU) else 'KHÔNG (vá KHÔNG ăn)'}")
        print(f"  · MỐC về token GỐC (bất biến sống còn của bản vá): "
              f"{m_doi}/{n}")
        if m_doi < n:
            print("    ‼ MỐC KHÔNG VỀ ĐƯỢC TOKEN GỐC -> chữ sẽ lệch tiếng.")
        if te > tot:
            print(f"  · ‼ TỆ ĐI ({te}) NHIỀU HƠN TỐT LÊN ({tot}) -> bản vá "
                  f"KHÔNG dùng được cho máy đọc này.")
        elif tot == 0 and te == 0:
            print("  · KHÔNG đổi gì (máy đọc này vốn đã đọc đúng) -> bật là "
                  "RỦI RO THUẦN, 0 lợi ích đo được.")
        return 0
    finally:
        try:
            p = SB.resolve()
            if p.name.startswith("bq_do_viettat_vn_") and REPO.resolve() in p.parents:
                shutil.rmtree(p, ignore_errors=True)
        except Exception:                                    # noqa: BLE001
            pass


if __name__ == "__main__":
    raise SystemExit(main())
