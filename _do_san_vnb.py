"""SÀN "CHỖ NHANH CHỖ CHẬM" CỦA TỪNG MÁY ĐỌC — bao nhiêu phần nhấp nhô có
SẴN trong máy đọc, KHÔNG do app sinh ra.

VÌ SAO ĐO CÁI NÀY: `_do_khop_video.py` đã đo được rằng cột **SÀN (TTS thô)**
gần bằng hệt cột arm CŨ và arm MỚI (20,48 · 20,45 · 20,49 · và 14,83 · 14,04
· 14,62) -> phần *"lúc nhanh lúc chậm"* **nằm sẵn trong bộ file TTS**. Bỏ bước
4c kéo CV từ 14,29 xuống 9,76 nhưng **KHÔNG về 0**. Câu hỏi còn nợ: **sàn đó
là bao nhiêu trên đường `vnb:` (giọng nhân bản) sau bản vá enrol v2.44.0** —
tức cái gì chữa được bằng mã và cái gì KHÔNG.

THƯỚC — DÙNG LẠI, KHÔNG ĐẺ THƯỚC THỨ HAI
-----------------------------------------
Đúng thước `_do_khop_video.toc_do_doc`: **ký tự/giây của TỪNG CÂU**, đo trên
mốc **NÓI THẬT** (`silencedetect` qua `thay_giong.do_le_im`), KHÔNG dùng
`probe_duration` — nó tính cả lề im (bẫy v2.27.0 đã ghi). Rồi lấy độ lệch
chuẩn + hệ số biến thiên giữa các câu.

ĐO GHÉP CẶP: mọi máy đọc đọc **CÙNG một bộ câu**, nên chênh lệch CV là của
MÁY ĐỌC chứ không phải của bộ câu.

BỘ CÂU PHẢI CÓ ĐỘ DÀI TRẢI RỘNG — đó chính là thứ sinh ra "chỗ nhanh chỗ
chậm" trong phụ đề thật (câu 12 ký tự và câu 90 ký tự nằm cạnh nhau).

ĐỐI CHỨNG: `vi-VN-NamMinhNeural` — máy đọc mặc định của anh Hùng, có số ở
mọi lượt đo trước.

Chạy:  .venv\\Scripts\\python -u _do_san_vnb.py
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import statistics as st
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

SAN = REPO / "bq_do_san_vnb"
KQ = REPO / "_kq_san_vnb.json"
NOWIN = 0x08000000

#: 20 câu, độ dài **13 -> 96 ký tự** — đúng dáng phụ đề dịch thật (câu thoại
#: cụt nằm cạnh câu kể dài). Bộ câu đều nhau thì CV ra thấp GIẢ, không đo
#: được thứ anh Hùng đang nghe.
CAU = [
    "Anh ta bỏ đi.",
    "Không ai nói gì cả.",
    "Cô ấy quay lại nhìn tôi một lần cuối rồi bước ra khỏi cửa.",
    "Đừng!",
    "Tôi đã nói với anh rồi mà.",
    "Chuyện xảy ra vào một buổi tối tháng Mười, khi cả thành phố đang chìm "
    "trong cơn mưa lớn nhất của mùa.",
    "Thật sao?",
    "Ông ấy đặt chiếc hộp xuống bàn, mở nắp ra, và im lặng rất lâu.",
    "Ba ngày sau.",
    "Không một ai trong số họ biết rằng đó là lần cuối cùng cả gia đình còn "
    "ngồi ăn chung với nhau.",
    "Được thôi.",
    "Tôi nhớ rõ giọng nói ấy, dù đã hơn hai mươi năm trôi qua kể từ hôm đó.",
    "Anh nghe thấy chứ?",
    "Cả căn phòng bỗng tối sầm lại.",
    "Người đàn ông đứng dậy, phủi bụi trên áo, rồi nói một câu mà đến giờ "
    "tôi vẫn không hiểu hết ý nghĩa.",
    "Im lặng.",
    "Chiếc xe dừng lại trước cổng, và từ trong xe bước ra một người phụ nữ "
    "mà không ai trong làng từng gặp.",
    "Cứ để tôi lo.",
    "Mọi thứ kết thúc nhanh hơn tất cả những gì họ tưởng tượng.",
    "Vậy là hết.",
]

#: (nhãn, mã giọng). `vnb:` điền sau — cần một FILE MẪU.
MAY_DOC_CO_DINH = [
    ("edge NamMinh (đối chứng)", "vi-VN-NamMinhNeural"),
    ("edge HoaiMy", "vi-VN-HoaiMyNeural"),
    ("VieNeu dựng sẵn Xuân Vĩnh", "vn:Xuân Vĩnh"),
    ("VieNeu dựng sẵn Ngọc Linh", "vn:Ngọc Linh"),
]

SO_LUOT_VN = 2       # VieNeu không tiền định -> đo 2 lượt, ghi DẢI


def _lech(xs: list[float]) -> tuple[float, float, float]:
    """(trung bình, độ lệch chuẩn, hệ số biến thiên %) — y `_do_khop_video`."""
    if len(xs) < 2:
        return (xs[0] if xs else 0.0), 0.0, 0.0
    tb = st.fmean(xs)
    sd = st.pstdev(xs)
    return tb, sd, (100.0 * sd / tb if tb else 0.0)


def _giay_noi_that(p: Path) -> float:
    """Giây NÓI THẬT = tổng độ dài trừ lề im hai đầu (`silencedetect`).

    KHÔNG dùng `probe_duration` — nó tính cả ~1,07 s lề im của edge-tts vào
    mẫu số, làm câu ngắn ra ký tự/giây thấp GIẢ.
    """
    from app.core import thay_giong as tg
    try:
        dau, cuoi, _tong = tg.do_le_im(p)
    except Exception:                                        # noqa: BLE001
        dau = cuoi = 0.0
    r = subprocess.run(
        [str(REPO / "bin" / "ffprobe.exe"), "-v", "error", "-show_entries",
         "format=duration", "-of", "csv=p=0", str(p)],
        capture_output=True, text=True, creationflags=NOWIN, timeout=60)
    try:
        tong = float((r.stdout or "0").strip())
    except ValueError:
        return 0.0
    return max(0.0, tong - float(dau or 0) - float(cuoi or 0))


def do_mot_may(nhan: str, voice: str, lan: int) -> dict:
    """Đọc CẢ BỘ CÂU bằng cửa chung rồi đo trải tốc độ đọc giữa các câu."""
    from app.core import dubbing
    tm = SAN / f"{nhan[:12].replace(' ', '_')}_{lan}"
    shutil.rmtree(tm, ignore_errors=True)
    tm.mkdir(parents=True, exist_ok=True)
    # ĐUÔI `.wav`: nhánh VieNeu ghi PCM, ffmpeg chọn muxer theo ĐUÔI nên
    # `.mp3` là chỗ `_ep_khung` từng chết (xem `giong_vieneu._ep_khung`).
    paths = [str(tm / f"c{i:03d}.wav") for i in range(len(CAU))]
    t0 = time.monotonic()
    try:
        ok = asyncio.run(dubbing._synth_all(list(CAU), voice, paths))
    except Exception as e:                                   # noqa: BLE001
        return {"loi": f"{type(e).__name__}: {e}"}
    giay = round(time.monotonic() - t0, 1)
    kt_giay: list[float] = []
    chi_tiet = []
    for i, (p, o) in enumerate(zip(paths, ok)):
        if not o or not Path(p).exists():
            continue
        n = len(CAU[i].strip())
        d = _giay_noi_that(Path(p))
        # Cùng bộ lọc `_do_khop_video.toc_do_doc`: câu quá ngắn -> tỉ số nhiễu.
        if n >= 8 and d > 0.25:
            kt_giay.append(n / d)
            chi_tiet.append({"i": i, "kt": n, "giay": round(d, 3),
                             "kt_giay": round(n / d, 2)})
    if len(kt_giay) < 5:
        return {"loi": f"quá ít câu đo được ({len(kt_giay)})", "giay": giay}
    tb, sd, cv = _lech(kt_giay)
    return {"kt_giay_tb": round(tb, 2), "sd": round(sd, 3),
            "cv": round(cv, 2), "so_cau": len(kt_giay),
            "so_hong": sum(1 for x in ok if not x),
            "giay": giay, "chi_tiet": chi_tiet}


def _mau_nhan_ban() -> Path | None:
    """File mẫu cho `vnb:` — LẤY LẠI mẫu do `_do_mau_dai.py` dựng (giọng
    MÁY, không phải người thật). KHÔNG dùng `adam_clone.wav`."""
    for p in (REPO / "bq_do_mau_dai").glob("mau_*.wav"):
        if "28s" in p.name and p.stat().st_size > 20000:
            return p
    for p in (REPO / "bq_do_mau_dai").glob("mau_*.wav"):
        if p.stat().st_size > 20000:
            return p
    return None


def _don_san() -> None:
    try:
        from app.core import xoa_an_toan
        xoa_an_toan.don_thu_muc(SAN, trong=REPO)
    except Exception as e:                                   # noqa: BLE001
        print(f"  (dọn hộp cát lỗi: {e})")


def main() -> int:
    SAN.mkdir(parents=True, exist_ok=True)
    kq: dict = {}
    if KQ.exists():
        try:
            kq = json.loads(KQ.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            kq = {}

    ds = list(MAY_DOC_CO_DINH)
    mau = _mau_nhan_ban()
    if mau:
        ds.append((f"NHÂN BẢN vnb: ({mau.name})", "vnb:" + str(mau)))
    else:
        print("  (chưa có file mẫu -> BỎ QUA arm `vnb:`; chạy _do_mau_dai.py "
              "trước)")

    n_kt = [len(c.strip()) for c in CAU]
    print("=" * 78)
    print(f"SÀN TRẢI TỐC ĐỘ ĐỌC — {len(CAU)} câu, độ dài "
          f"{min(n_kt)}-{max(n_kt)} ký tự (đo trên mốc NÓI THẬT)")
    print("=" * 78)
    print(f"{'máy đọc':34s} {'kt/giây':>8s} {'SD':>7s} {'CV %':>7s} "
          f"{'câu':>4s} {'giây':>6s}")

    for nhan, voice in ds:
        n_lan = SO_LUOT_VN if voice.startswith(("vn:", "vnb:")) else 1
        rs = list((kq.get(nhan) or {}).get("lan") or [])
        for lan in range(len(rs), n_lan):
            r = do_mot_may(nhan, voice, lan)
            rs.append(r)
            kq[nhan] = {"voice": voice, "lan": rs}
            KQ.write_text(json.dumps(kq, ensure_ascii=False, indent=1),
                          encoding="utf-8")        # GHI NGAY SAU MỖI LƯỢT
        for r in rs:
            if r.get("loi"):
                print(f"{nhan:34s} {'LỖI':>8s}  {r['loi']}")
                continue
            print(f"{nhan:34s} {r['kt_giay_tb']:8.2f} {r['sd']:7.3f} "
                  f"{r['cv']:7.2f} {r['so_cau']:4d} {r['giay']:6.0f}")

    print()
    print("=" * 78)
    print("BẢNG GỌN — SÀN CV (%) theo máy đọc; số CÀNG THẤP càng ĐỀU")
    print("=" * 78)
    for nhan, _v in ds:
        rs = (kq.get(nhan) or {}).get("lan") or []
        xs = [r["cv"] for r in rs if r.get("cv")]
        if not xs:
            continue
        dai = f"{min(xs):.2f}-{max(xs):.2f}" if len(xs) > 1 else f"{xs[0]:.2f}"
        print(f"  {nhan:34s} CV = {dai}")
    print(f"\n  kết quả -> {KQ}")
    return 0


if __name__ == "__main__":
    rc = 1
    try:
        rc = main()
    finally:
        pass          # giữ file cho bước NGHE THỬ; dọn ở cuối lượt
    sys.exit(rc)
