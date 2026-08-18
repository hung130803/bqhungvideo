"""ĐO "MẤT TIẾNG NGƯỜI" trên bản anh Hùng ĐÃ XUẤT — so LỚP GIỌNG với LỚP GIỌNG
(18/08/2026).

Anh Hùng: *"mấy cái đoạn âm thanh gốc nói tiếng Anh nó không đọc phần đó thì
lại bị **tắt tiếng** không hiểu"* · *"cái nghe được cái không"*.

CHẨN ĐOÁN CẦN KIỂM CHỨNG: dây chuyền tách giọng khỏi nhạc -> đọc lại phần lời
-> trộn giọng MỚI với nhạc. Đoạn nào **không được đọc lại** (câu tiếng Anh mà
bộ chép lời bỏ qua, câu TTS lỗi…) thì giọng GỐC đã bị bỏ mà giọng MỚI không có
-> còn lại chỉ nhạc -> **im tiếng người**. Tức MẤT NỘI DUNG, nặng hơn hẳn
chuyện âm lượng.

**VÌ SAO PHẢI VIẾT SCRIPT THỨ HAI, KHÔNG DÙNG `_do_mat_tieng.py`:** script đó
so ĐƯỜNG BAO CỦA CẢ FILE. Bản xuất VẪN CÓ NHẠC NỀN ở đúng đoạn mất tiếng, nên
nó đo ra **IM HẲN 0,0 s (0,0% video)** — một chứng nhận SẠCH cho thứ đang hỏng.
Đã chạy thật để xác nhận điều đó trước khi viết cái này (đúng họ bẫy `astats`
cổng 53 · mức mờ 0,40 cổng 56b: *phép đo hỏng nguy hiểm hơn không đo*).

THƯỚC ĐÚNG: tách CẢ HAI file bằng Demucs rồi so **lớp GIỌNG với lớp GIỌNG**.
Nhạc bị loại khỏi cả hai vế nên chỗ mất tiếng người hiện ra.

**KHÔNG ĐỤNG FILE GỐC MỘT BYTE** — chỉ đọc; mọi thứ tạm nằm trong sandbox và
bị dọn ở `finally`.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                                           # noqa: BLE001
    pass

NGUON = Path(r"C:\Users\Admin\Downloads\longtieng")
SB = REPO / "bq_do_mat_giong"

#: Bước đo đường bao. 0,05 s = 20 mẫu/giây: đủ mịn để thấy một từ bị mất (từ
#: ngắn nhất ~0,15 s) mà không biến bảng thành hàng nghìn dòng.
BUOC = 0.05

#: Khoảng ngắn hơn mức này KHÔNG tính là mất nội dung — đó là chênh lệch ranh
#: giới giữa hai lượt tách Demucs (nó không tiền định), không phải câu bị bỏ.
DAI_MIN = 0.30

#: "CÓ tiếng" = nổi hơn SÀN NHIỄU CỦA CHÍNH FILE ĐÓ bấy nhiêu dB.
NOI_CO = 12.0
#: "IM" = không nổi quá bấy nhiêu dB trên sàn nhiễu của chính nó.
NOI_IM = 4.0


def _ff(args: list[str], mo_ta: str, timeout: int = 1800) -> None:
    r = subprocess.run([str(REPO / "bin" / "ffmpeg.exe"), "-y", "-v", "error",
                        *args], capture_output=True, text=True,
                       timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(
            f"{mo_ta}: rc={r.returncode} {(r.stderr or '')[:300]}")


def rut_wav(video: Path, ra: Path) -> None:
    """Audio -> WAV stereo 44,1 kHz (đúng cái Demucs cần)."""
    _ff(["-i", str(video), "-vn", "-ac", "2", "-ar", "44100",
         "-c:a", "pcm_s16le", str(ra)], f"rút audio {video.name}")
    if not ra.exists() or ra.stat().st_size < 1024:
        raise RuntimeError(f"WAV rỗng/quá nhỏ: {ra}")


def _san_nhieu(bao: list[float]) -> float:
    """Sàn nhiễu của một lớp giọng = bách phân vị 20 (chỗ không ai nói).

    Lấy theo CHÍNH file, KHÔNG đặt hằng số dBFS: hai lượt Demucs để lại mức
    nhiễu khác nhau, và bản xuất còn đi qua một đời AAC nữa. Đặt hằng số là
    file nào nhiễu hơn sẽ tự "có tiếng" khắp nơi.
    """
    x = sorted(v for v in bao if v > -119.0)
    return x[int(len(x) * 0.20)] if x else -120.0


def khoang_mat(bao_g: list[float], bao_x: list[float]) -> tuple[list, dict]:
    """Khoảng CÓ tiếng ở lớp giọng GỐC mà IM ở lớp giọng XUẤT."""
    sg, sx = _san_nhieu(bao_g), _san_nhieu(bao_x)
    ng, nx = sg + NOI_CO, sx + NOI_IM
    n = min(len(bao_g), len(bao_x))
    co = [bao_g[i] > ng for i in range(n)]
    im = [bao_x[i] < nx for i in range(n)]
    mat = [co[i] and im[i] for i in range(n)]

    kh: list[list[float]] = []
    i = 0
    while i < n:
        if not mat[i]:
            i += 1
            continue
        j = i
        ho = 0
        k = i
        while k < n:
            if mat[k]:
                j, ho = k, 0
            else:
                ho += 1
                if ho > 2:              # cho hở 0,10 s để một từ không bị chẻ
                    break
            k += 1
        kh.append([i * BUOC, (j + 1) * BUOC])
        i = k
    kh = [k for k in kh if (k[1] - k[0]) >= DAI_MIN]
    return kh, {
        "san_goc_db": round(sg, 2), "san_xuat_db": round(sx, 2),
        "nguong_co_db": round(ng, 2), "nguong_im_db": round(nx, 2),
        "so_o": n, "o_mat": sum(mat),
        "giay_co_tieng_goc": round(sum(co) * BUOC, 2),
        "giay_co_tieng_xuat": round((n - sum(im)) * BUOC, 2),
        "giay_mat_tho": round(sum(mat) * BUOC, 2),
        "giay_mat": round(sum(k[1] - k[0] for k in kh), 2),
        "so_khoang": len(kh),
    }


def main() -> int:
    from app.core import thay_giong as TG

    if not NGUON.is_dir():
        print(f"KHÔNG CÓ thư mục nguồn: {NGUON}")
        return 2
    cap = [(g, NGUON / "xuất" / g.name) for g in sorted(NGUON.glob("*.mp4"))
           if (NGUON / "xuất" / g.name).exists()]
    print(f"tìm được {len(cap)} cặp (gốc, xuất)")
    if not cap:
        return 2
    print(f"Demucs: {TG.tinh_trang_demucs()}")

    SB.mkdir(exist_ok=True)
    ket: list[dict] = []
    try:
        for i, (g, x) in enumerate(cap, 1):
            print(f"\n{'=' * 72}\n[{i}/{len(cap)}] {g.stem[:40]}")
            lam = SB / f"v{i}"
            lam.mkdir(exist_ok=True)
            t0 = time.time()
            wg, wx = lam / "goc.wav", lam / "xuat.wav"
            rut_wav(g, wg)
            rut_wav(x, wx)
            dg, dx = TG.probe_duration(wg), TG.probe_duration(wx)
            print(f"  audio: gốc {dg:.2f}s · xuất {dx:.2f}s")

            print("  tách lớp giọng bản GỐC (Demucs)...")
            tg = TG.tach_giong(wg, lam / "tg", cach="demucs")
            print("  tách lớp giọng bản XUẤT (Demucs)...")
            tx = TG.tach_giong(wx, lam / "tx", cach="demucs")

            bg = TG.duong_bao_muc(tg["giong"], buoc=BUOC)
            bx = TG.duong_bao_muc(tx["giong"], buoc=BUOC)
            kh, tk = khoang_mat(bg, bx)
            print(f"  sàn nhiễu lớp giọng: gốc {tk['san_goc_db']} · "
                  f"xuất {tk['san_xuat_db']} dBFS   ({time.time()-t0:.0f}s)")
            print(f"  gốc CÓ tiếng {tk['giay_co_tieng_goc']}s · "
                  f"xuất CÓ tiếng {tk['giay_co_tieng_xuat']}s")
            print(f"  >>> MẤT {tk['giay_mat']}s / {tk['so_khoang']} khoảng "
                  f"= {100 * tk['giay_mat'] / max(1e-9, dg):.1f}% video")
            if kh:
                print("  ── BẢNG GIÂY-ĐẾN-GIÂY (gốc CÓ tiếng, xuất IM) ──")
                for a, b in kh[:40]:
                    print(f"     {a:8.2f} -> {b:8.2f}   ({b - a:5.2f}s)")
                if len(kh) > 40:
                    print(f"     … còn {len(kh) - 40} khoảng, xem json")
            ket.append({"ten": g.name, "dai_goc": round(dg, 2),
                        "dai_xuat": round(dx, 2), **tk,
                        "khoang": [[round(a, 2), round(b, 2)] for a, b in kh]})
            (REPO / "_kq_mat_giong.json").write_text(
                json.dumps(ket, ensure_ascii=False, indent=1),
                encoding="utf-8")
            shutil.rmtree(lam, ignore_errors=True)
    finally:
        shutil.rmtree(SB, ignore_errors=True)

    print(f"\n{'=' * 72}\nTỔNG HỢP — MẤT TIẾNG NGƯỜI")
    print(f"{'video':<34}{'dài':>9}{'gốc nói':>10}{'MẤT':>9}{'%':>7}{'khoảng':>8}")
    tm = tv = 0.0
    for k in ket:
        tm += k["giay_mat"]
        tv += k["dai_goc"]
        print(f"{k['ten'][:32]:<34}{k['dai_goc']:>8.1f}s"
              f"{k['giay_co_tieng_goc']:>9.1f}s{k['giay_mat']:>8.1f}s"
              f"{100 * k['giay_mat'] / max(1e-9, k['dai_goc']):>6.1f}%"
              f"{k['so_khoang']:>8}")
    print(f"{'TỔNG':<34}{tv:>8.1f}s{'':>9} {tm:>7.1f}s"
          f"{100 * tm / max(1e-9, tv):>6.1f}%")
    print("=> _kq_mat_giong.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
