# -*- coding: utf-8 -*-
"""CỔNG 66 — CHUẨN HOÁ ĐỘ TO CHO **MỌI ĐƯỜNG XUẤT CLIP** (16/08/2026).

Cổng 65 canh đường THAY TIẾNG. Cổng này canh đường **CẮT THƯỜNG · GHÉP ĐOẠN ·
RECAP · MIXED-CUT · CLIP ĐƠN** — đo trước khi sửa ra 2 lỗi thật:
  * độ to trải **15,75 LU** giữa các clip (−6,65 .. −22,40)
  * **3/8 bản xuất đỉnh thật vượt 0 dBTP** = VỠ TIẾNG thật

**NGUỒN TỰ SINH BẰNG `lavfi`, KHÔNG phụ thuộc file trên máy** (bài học cổng 47:
kho video trên đĩa đổi thì cổng nhấp nháy mà không ai biết là do kho). Mỗi
nguồn dựng đúng một ca biên đã gặp thật.

**CỔNG NÀY TỰ KIỂM: gỡ chốt ra thì PHẢI ĐỎ.** `_pha_do_to_xuat.py` chạy 8 phép
phá — mỗi phép là một cách "sửa cho gọn" mà người sau có thể làm thật.

**THƯỚC LÀ `ebur128`.** `loudnorm` pha đo ĐỌC THẤP tới 0,58 LU trên nguồn dải
động rộng — đã truy bằng thước THỨ BA tự viết (BS.1770-4/numpy), xem
`_do_hai_thuoc.py`. Cổng vẫn đối chiếu thước thứ hai để bắt phép đo hỏng.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

# HỘP CÁT: đặt TRƯỚC khi nạp config, không thì ghi vào DATA_DIR THẬT.
_SB = tempfile.mkdtemp(prefix="bq_dtx_")
os.environ["BQ_DATA_DIR"] = _SB
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

import _test_guard  # noqa: E402,F401  (bắt buộc: cấm mở Explorer/trình phát)

from config import settings  # noqa: E402

DAT = 0
HONG = 0
FF = settings.FFMPEG_PATH


def ok(dieu: bool, nhan: str, chi_tiet: str = "") -> None:
    global DAT, HONG
    if dieu:
        DAT += 1
        print(f"  ĐẠT  {nhan}" + (f" — {chi_tiet}" if chi_tiet else ""))
    else:
        HONG += 1
        print(f"  HỎNG {nhan}" + (f" — {chi_tiet}" if chi_tiet else ""))


def _don() -> None:
    import shutil
    shutil.rmtree(_SB, ignore_errors=True)


import atexit  # noqa: E402

atexit.register(_don)

TAM = Path(_SB) / "clip"
TAM.mkdir(parents=True, exist_ok=True)


# ================================================================== nguồn
#: NGUỒN `lavfi` MẶC ĐỊNH LÀ PHẲNG TUYỆT ĐỐI (LRA = 0,00) — bài học cổng 42,
#: và ở cổng này nó còn nguy hơn: LRA 0 thì mệnh đề "LRA không tụt" ĐÚNG VĨNH
#: VIỄN kể cả khi bản vá nén dập. Nên nguồn phải có CAO TRÀO THẬT: nền nhỏ xen
#: đoạn to, chu kỳ **6 giây** (khối đo LRA là 3 giây — chu kỳ ngắn hơn thì hai
#: mức bị trộn trong cùng một khối và LRA lại về 0).
_NEN = ("sine=f=220:r=48000:d={d},"
        "volume='0.06+0.94*lt(mod(t,6),3)':eval=frame")
#: HỆ SỐ ĐỈNH CAO — dựng lại ĐÚNG hình dạng clip thật đã đo (I −21,90 · đỉnh
#: +0,90 = hệ số đỉnh 22,8 dB): nền rất nhỏ + cú va tắt dần mỗi 1,5 giây. Đây
#: là ca **BẤT KHẢ THI**: muốn vừa −14 LUFS vừa <= −1 dBTP thì phải gọt **9,8
#: dB** — không có cách nào không đụng dải động.
#:
#: **PHẢI DÙNG `aevalsrc` (tính TỪNG MẪU), KHÔNG dùng `volume=...:eval=frame`.**
#: Bản đầu viết `volume='1+49*lt(mod(t,2.0),0.02)':eval=frame`: khung tiếng dài
#: 1024 mẫu = 21,33 ms nên `t` chỉ nhảy theo bước 21,33 ms và **gần như không
#: bao giờ rơi vào cửa sổ 20 ms** -> KHÔNG có cú va nào, nguồn ra chỉ còn cái
#: nền. Nó vẫn "chạy", vẫn ra hệ số đỉnh 17,7 dB trông hợp lý, nhưng phần phải
#: gọt chỉ 5,2 dB nên **ca BẤT KHẢ THI không hề được thử** — và đúng vì thế
#: phép phá "bỏ bậc thang" LỌT qua cổng ở lượt thử phá đầu tiên.
#: Nguồn còn phải có **DẢI ĐỘNG THẬT** nữa, không chỉ hệ số đỉnh cao: bản chỉ
#: có cú va trên nền phẳng ra LRA 0,10, mà LRA 0,10 thì gọt bao nhiêu cũng
#: không tụt được -> bậc thang không bao giờ phải lùi -> phép phá "bỏ bậc
#: thang" LỌT tiếp lần hai. Nên nền đổi mức mỗi 3 giây (LRA 9,40) và cú va chỉ
#: nằm ở nửa TO — đúng hình dạng một đoạn phim có cao trào.
_NHON = ("aevalsrc=exprs='0.12*(0.10+0.90*lt(mod(t\\,6)\\,3))*sin(2*PI*200*t)"
         "+0.98*lt(mod(t\\,6)\\,3)*sin(2*PI*900*t)"
         "*exp(-70*mod(t\\,1.5))':s=48000:d={d}")

#: ca biên -> (mô tả tiếng, hệ số đặt trước, cửa sổ I mong muốn, cửa sổ TP).
#: Cửa sổ là **CHỐT TỰ KIỂM NGUỒN** (CA 0): nguồn không rơi đúng ca biên thì
#: cổng phải ĐỎ chứ không được lặng lẽ đo một thứ khác — chính lượt đầu của
#: cổng này đã dựng nhầm nguồn −55,8 LUFS (rơi xuống dưới SÀN) làm 3 ca TỰ
#: PASS OAN vì chúng đo file KHÔNG HỀ bị đụng tới.
NGUON = {
    # nguồn kiểu Douyin đã master sát trần: TO QUÁ + đỉnh vượt 0 dBTP
    "qua_to": (_NEN, "volume=8.0", (-9.0, -3.0), (0.0, 9.0)),
    # đoạn phim NHỎ TIẾNG: thấp hơn đích ~8 LU, còn chỗ trống ở đỉnh
    "qua_nho": (_NEN, "volume=1.1", (-25.0, -19.0), (-20.0, -12.0)),
    # HỆ SỐ ĐỈNH CAO (ca BẤT KHẢ THI) — khớp clip thật: I −22,3 · đỉnh +0,0
    "dinh_nhon": (_NHON, "volume=1.0", (-26.0, -19.0), (-2.0, 6.0)),
    # NGUỒN RIÊNG CHO PHÉP ĐO LỆCH TIẾNG-HÌNH: phải là NHIỄU, không được là
    # sin. Sin 220 Hz có chu kỳ ĐÚNG 218,2 mẫu nên tương quan chéo có NHIỀU
    # đỉnh bằng nhau — lượt đầu đo ra "-218 mẫu = -4,542 ms" và suýt bị kết
    # luận oan là quá mẫu làm lệch tiếng. Nhiễu thì đỉnh tương quan DUY NHẤT.
    "de_do_lech": ("anoisesrc=c=pink:r=48000:a=0.25:d={d}", "volume=1.0",
                   (-30.0, -14.0), (-20.0, -1.0)),
    # gần câm: dưới SÀN chống nâng điên
    "gan_cam": ("anoisesrc=c=pink:r=48000:a=0.0002:d={d}", "volume=1.0",
                (-120.0, -55.0), (-120.0, -30.0)),
}
GIAY = 18.0


def _sinh(ten: str, giay: float = GIAY) -> Path:
    """Dựng 1 clip mp4 (hình phẳng + tiếng của ca biên `ten`) bằng `lavfi`.

    `-t` đặt Ở ĐẦU VÀO (trước `-i`) — đặt sai chỗ là `anullsrc`/`sine` ghi VÔ
    HẠN 115 MB/giây, đã làm đầy ổ C 420 GB một lần. Nguồn tiếng còn tự mang
    `d=` nên KHÔNG có đường nào chạy vô hạn.
    """
    p = TAM / f"{ten}.mp4"
    if p.exists():
        return p
    aud, hs, _, _ = NGUON[ten]
    cmd = [FF, "-y", "-hide_banner", "-nostdin",
           "-f", "lavfi", "-t", f"{giay:.2f}",
           "-i", "color=c=0x1E6F5C:s=320x568:r=25",
           "-f", "lavfi", "-t", f"{giay:.2f}",
           "-i", aud.format(d=f"{giay:.2f}") + "," + hs,
           "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-shortest",
           "-movflags", "+faststart", str(p)]
    r = subprocess.run(cmd, capture_output=True, timeout=300,
                       stdin=subprocess.DEVNULL)
    if r.returncode != 0 or not p.exists() or p.stat().st_size < 1024:
        raise RuntimeError(f"không dựng được nguồn {ten}: "
                           f"{(r.stderr or b'').decode('utf-8', 'replace')[-300:]}")
    return p


def _do(p: Path) -> dict:
    from app.core.ffmpeg_utils import do_do_to_clip
    return do_do_to_clip(p)


def _md5_luong(p: Path, luong: str) -> str:
    """MD5 của RIÊNG một luồng (v/a) — chứng minh `-c:v copy` không đụng hình."""
    r = subprocess.run([FF, "-hide_banner", "-nostdin", "-i", str(p),
                        "-map", f"0:{luong}", "-c", "copy", "-f", "md5", "-"],
                       capture_output=True, timeout=300, stdin=subprocess.DEVNULL)
    return (r.stdout or b"").decode("utf-8", "replace").strip()


# ==================================================================
def ca0_nguon_dung_ca_bien(kq: dict) -> None:
    """**TỰ KIỂM NGUỒN** — không có ca này thì cả cổng có thể là con dấu.

    Lượt đầu của chính cổng này dựng nhầm nguồn "nhỏ tiếng" thành −55,8 LUFS
    (rơi xuống DƯỚI SÀN chống nâng điên) -> hàm BỎ QUA, file không bị đụng ->
    ca "hệ số là hằng số" đo file với CHÍNH NÓ ra **0,0000 dB** và ĐẠT, ca
    "hỏng thì giữ clip" ĐẠT vì chưa bao giờ chạy tới chỗ hỏng. Ba ca PASS OAN
    cùng lúc, không ca nào kêu.
    """
    print("\n== CA 0: nguồn thử có ĐÚNG là ca biên định dựng không ==")
    for ten, (_a, _h, cua_i, cua_tp) in NGUON.items():
        t = kq[ten]["truoc"]
        ok(cua_i[0] <= t["I"] <= cua_i[1],
           f"[{ten}] độ to nguồn trong cửa sổ {cua_i}", f"{t['I']:.2f} LUFS")
        ok(cua_tp[0] <= t["TP"] <= cua_tp[1],
           f"[{ten}] đỉnh nguồn trong cửa sổ {cua_tp}", f"{t['TP']:+.2f} dBTP")
    # nguồn phải có DẢI ĐỘNG THẬT, không thì ca "không nén dập" tự đúng
    lra = kq["qua_nho"]["truoc"]["LRA"]
    ok(lra >= 3.0,
       "nguồn chính có dải động THẬT (LRA >= 3) — nguồn phẳng thì mệnh đề "
       "'LRA không tụt' đúng vĩnh viễn kể cả khi bản vá nén dập",
       f"LRA {lra:.2f} LU")
    from app.core import ffmpeg_utils as _fu0
    hs_dinh = kq["dinh_nhon"]["truoc"]["TP"] - kq["dinh_nhon"]["truoc"]["I"]
    # phần PHẢI GỌT nếu ép đủ đích = hệ số đỉnh − (|đích| − biên)
    can_got = hs_dinh - (abs(_fu0.DICH_LUFS_CLIP) - _fu0.BIEN_DINH_CLIP)
    ok(hs_dinh >= 20.0,
       "có ca HỆ SỐ ĐỈNH CAO (ca BẤT KHẢ THI: không thể vừa đủ to vừa không nén)",
       f"hệ số đỉnh {hs_dinh:.1f} dB")
    ok(can_got > _fu0.NGAN_SACH_GOT_DB,
       f"ca đó THẬT SỰ vượt ngân sách gọt {_fu0.NGAN_SACH_GOT_DB} dB — nếu "
       f"không thì bậc thang không bao giờ chạy và cổng không kiểm được gì",
       f"ép đủ đích phải gọt {can_got:.1f} dB")
    # và phải có ca THẬT SỰ ĐANG VỠ TIẾNG để chứng minh bản vá chữa được
    vo = [k for k, v in kq.items() if v["truoc"]["TP"] > 0.0]
    ok(len(vo) >= 1, "có ca đỉnh nguồn VƯỢT 0 dBTP (đúng lỗi đã đo: 3/8 bản "
                     "xuất vỡ tiếng)", f"{vo}")


def ca1_hang_so() -> None:
    print("\n== CA 1: hằng số đích + thước đo ==")
    from app.core import ffmpeg_utils as fu
    ok(abs(fu.DICH_LUFS_CLIP - (-14.0)) < 1e-9, "đích −14,0 LUFS",
       f"{fu.DICH_LUFS_CLIP}")
    ok(abs(fu.TRAN_DINH_THAT_CLIP - (-1.0)) < 1e-9, "trần đỉnh −1,0 dBTP",
       f"{fu.TRAN_DINH_THAT_CLIP}")
    ok(fu.QUA_MAU_HAN_DINH >= 4 * 48000,
       "hạn đỉnh chạy ở QUÁ MẪU >= 4x (không thì đỉnh thật phụ thuộc bản ffmpeg)",
       f"{fu.QUA_MAU_HAN_DINH} Hz")
    ch = fu._chuoi_do_to(2.0, -1.5)
    ok("aresample" in ch.split("alimiter")[0], "quá mẫu đặt TRƯỚC alimiter", ch)
    ok(ch.rstrip().endswith("aresample=48000"), "hạ lại 48 kHz sau alimiter")
    ok("level=0" in ch, "alimiter level=0 (mặc định level=true TỰ NÂNG +3,1 dB)")
    ok("latency=1" in ch, "alimiter latency=1 (không có thì lệch 0,98 ms)")


def ca2_do_hong_phai_nem() -> None:
    """*Phép đo hỏng nguy hiểm hơn không đo* — nó phát chứng nhận."""
    print("\n== CA 2: đo hỏng phải NÉM, không trả None/số mặc định ==")
    from app.core.ffmpeg_utils import do_do_to_clip
    try:
        do_do_to_clip(TAM / "khong_co_that.mp4")
        ok(False, "file KHÔNG tồn tại -> phải ném")
    except RuntimeError as e:
        ok(True, "file KHÔNG tồn tại -> ném", str(e)[:50])
    except Exception as e:  # noqa: BLE001
        ok(False, "file KHÔNG tồn tại -> ném RuntimeError", f"ném {type(e).__name__}")

    # ffmpeg mã 0 mà KHÔNG in Summary (video KHÔNG có luồng tiếng) — nhánh
    # raise KHÁC hẳn nhánh trên; cổng 65 từng thiếu đúng ca này.
    cam = TAM / "khong_tieng.mp4"
    if not cam.exists():
        subprocess.run([FF, "-y", "-hide_banner", "-nostdin", "-f", "lavfi",
                        "-t", "2", "-i", "color=c=black:s=160x160:r=25",
                        "-c:v", "libx264", "-preset", "ultrafast",
                        "-pix_fmt", "yuv420p", str(cam)],
                       capture_output=True, timeout=300, stdin=subprocess.DEVNULL)
    try:
        d = do_do_to_clip(cam)
        ok(False, "video KHÔNG có tiếng -> phải ném", f"trả {d}")
    except RuntimeError as e:
        ok(True, "video KHÔNG có tiếng -> ném (không trả số bịa)", str(e)[:50])

    # ---- NHÁNH "ffmpeg MÃ 0 mà KHÔNG in Summary" ----
    # HAI CA TRÊN ĐỀU ĐI NHÁNH `returncode != 0`, KHÔNG chạm nhánh BÓC CHỮ.
    # Đúng lỗ hổng này làm phép phá "trả số mặc định thay vì NÉM" **LỌT** ở
    # lượt thử phá đầu (và là đúng lỗ mà cổng 65 đã vấp: *"ca đó đi nhánh
    # raise KHÁC"*). Ép thẳng nhánh đó bằng một `subprocess` giả.
    from app.core import ffmpeg_utils as fu

    class _Ra:
        returncode = 0
        stdout = b""
        stderr = b"ffmpeg ... chay xong, khong mot dong Summary nao"

    class _GiaSP:
        DEVNULL = subprocess.DEVNULL

        @staticmethod
        def run(*a, **k):
            return _Ra()

    that = fu.subprocess
    try:
        fu.subprocess = _GiaSP
        try:
            d = fu.do_do_to_clip(cam)
            ok(False, "ffmpeg MÃ 0 mà KHÔNG in Summary -> phải ném",
               f"trả {d} (phát chứng nhận cho phép đo hỏng)")
        except RuntimeError as e:
            ok(True, "ffmpeg MÃ 0 mà KHÔNG in Summary -> ném", str(e)[:50])

        _Ra.stderr = (b"Summary:\n\n  Loudness range:\n    LRA:  3.0 LU\n"
                      b"  True peak:\n    Peak: -2.0 dBFS\n")
        try:
            d = fu.do_do_to_clip(cam)
            ok(False, "Summary THIẾU dòng độ to -> phải ném", f"trả {d}")
        except RuntimeError as e:
            ok(True, "Summary THIẾU dòng độ to -> ném", str(e)[:50])
    finally:
        fu.subprocess = that


def ca3_he_so_la_hang_so(kq: dict) -> None:
    """CHỐT THẬT phân biệt "nâng thuần" với "nén động" (bài học cổng 65).

    LRA MỘT MÌNH là con dấu: nguồn nén sẵn thì bộ nén động cũng gần như không
    đổi LRA. Cái không thể giả được là **hệ số áp phải là HẰNG SỐ**.
    """
    print("\n== CA 3: hệ số áp là HẰNG SỐ (không phải nén động) ==")
    import wave

    goc, moi = kq["qua_nho"]["goc"], kq["qua_nho"]["moi"]

    def _mau(p: Path):
        w = TAM / (p.stem + "_pcm.wav")
        subprocess.run([FF, "-y", "-hide_banner", "-nostdin", "-i", str(p),
                        "-vn", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le",
                        str(w)], capture_output=True, timeout=300,
                       stdin=subprocess.DEVNULL)
        with wave.open(str(w), "rb") as f:
            import array
            a = array.array("h")
            a.frombytes(f.readframes(f.getnframes()))
        return a

    a, b = _mau(goc), _mau(moi)
    n = min(len(a), len(b))
    import math
    cua = 48000 // 2                       # cửa sổ 0,5 giây
    hs = []
    for i in range(0, n - cua, cua):
        ra = math.sqrt(sum(x * x for x in a[i:i + cua]) / cua) + 1e-9
        rb = math.sqrt(sum(x * x for x in b[i:i + cua]) / cua) + 1e-9
        if ra > 30:                        # bỏ cửa sổ im (chia cho nhiễu)
            hs.append(20.0 * math.log10(rb / ra))
    tb = sum(hs) / max(1, len(hs))
    do_lech = math.sqrt(sum((x - tb) ** 2 for x in hs) / max(1, len(hs)))
    ok(len(hs) >= 4, "đủ cửa sổ để đo hệ số", f"{len(hs)} cửa sổ")
    ok(do_lech <= 0.05,
       "độ lệch chuẩn hệ số <= 0,05 dB (nén động đo được 0,277 dB)",
       f"{do_lech:.4f} dB · hệ số TB {tb:+.2f} dB")


def ca4_dat_dich_va_tran(kq: dict) -> None:
    print("\n== CA 4: gom về đích + KHÔNG clip nào vỡ tiếng ==")
    from app.core import ffmpeg_utils as fu
    co = {k: v for k, v in kq.items() if k != "gan_cam"}
    Is = [v["sau"]["I"] for v in co.values()]
    TPs = [v["sau"]["TP"] for v in co.values()]
    print(f"     {'ca':12} {'I trước':>8} {'I sau':>8} {'TP trước':>9} "
          f"{'TP sau':>8} {'LRA trước':>10} {'LRA sau':>8}")
    for k, v in kq.items():
        print(f"     {k:12} {v['truoc']['I']:8.2f} {v['sau']['I']:8.2f} "
              f"{v['truoc']['TP']:9.2f} {v['sau']['TP']:8.2f} "
              f"{v['truoc']['LRA']:10.2f} {v['sau']['LRA']:8.2f}")
    ok(all(t <= fu.TRAN_DINH_THAT_CLIP + 1e-6 for t in TPs),
       "MỌI clip đỉnh thật <= −1,0 dBTP (trước khi sửa: 3/8 vượt 0 dBTP)",
       f"cao nhất {max(TPs):+.2f} dBTP")
    ok(all(i <= fu.DICH_LUFS_CLIP + fu.NGUONG_BO_QUA_LU + 1e-6 for i in Is),
       "KHÔNG clip nào bị đẩy VƯỢT đích (chuẩn hoá không được làm to quá)",
       f"to nhất {max(Is):.2f} LUFS")
    # ca `dinh_nhon` là ca BẤT KHẢ THI, cố ý KHÔNG đòi tới đích
    thuong = [k for k in co if k != "dinh_nhon" and not co[k].get("bo_qua")]
    xa = [(k, co[k]["sau"]["I"]) for k in thuong
          if abs(co[k]["sau"]["I"] - fu.DICH_LUFS_CLIP) > 1.0]
    ok(not xa, "ca thường về đúng đích (±1,0 LU)", f"lệch: {xa}")


def ca5_khong_nen_dap(kq: dict) -> None:
    print("\n== CA 5: KHÔNG NÉN DẬP (LRA trước/sau) ==")
    from app.core import ffmpeg_utils as fu
    xau = [(k, round(v["truoc"]["LRA"] - v["sau"]["LRA"], 2))
           for k, v in kq.items()
           if (v["truoc"]["LRA"] - v["sau"]["LRA"]) > fu.LRA_TUT_TOI_DA + 1e-6]
    ok(not xau, f"không clip nào LRA tụt quá {fu.LRA_TUT_TOI_DA} LU",
       f"vi phạm: {xau}" if xau else "")


def ca6_khong_dung_clip_da_dung() -> None:
    print("\n== CA 6: clip ĐÃ đúng độ to -> KHÔNG mã hoá lại ==")
    import hashlib
    from app.core.ffmpeg_utils import chuan_do_to_clip

    # dựng clip đã ở đúng −14 LUFS: chuẩn hoá 1 lượt rồi chạy LẠI lượt nữa
    p = TAM / "da_dung.mp4"
    if not p.exists():
        import shutil
        shutil.copy2(_sinh("qua_nho"), p)
        chuan_do_to_clip(p)
    truoc = hashlib.md5(p.read_bytes()).hexdigest()
    kq = chuan_do_to_clip(p)
    sau = hashlib.md5(p.read_bytes()).hexdigest()
    ok(kq["bo_qua"] is True, "lượt 2 -> bỏ qua", kq.get("ly_do", "")[:60])
    ok(truoc == sau, "file KHÔNG bị ghi lại một byte nào (không thêm đời AAC)")


def ca7_san_chong_nang_dien() -> None:
    print("\n== CA 7: SÀN chống nâng điên (clip gần câm) ==")
    import hashlib
    from app.core import ffmpeg_utils as fu

    p = _sinh("gan_cam")
    d = _do(p)
    ok(d["I"] < fu.SAN_LUFS_CLIP,
       f"nguồn thử thật sự dưới sàn {fu.SAN_LUFS_CLIP}", f"{d['I']:.2f} LUFS")
    truoc = hashlib.md5(p.read_bytes()).hexdigest()
    kq = fu.chuan_do_to_clip(p)
    ok(kq["bo_qua"] is True, "clip gần câm -> BỎ QUA (nâng lên là nâng nền nhiễu)",
       kq.get("ly_do", "")[:60])
    ok(truoc == hashlib.md5(p.read_bytes()).hexdigest(), "file giữ nguyên")


def ca8_hinh_va_do_dai(kq: dict) -> None:
    print("\n== CA 8: HÌNH không bị đụng · ĐỘ DÀI giữ nguyên + TIỀN ĐỊNH ==")
    from app.core.ffmpeg_utils import chuan_do_to_clip, probe
    import shutil

    v = kq["qua_nho"]
    ok(v["md5_v_truoc"] == v["md5_v_sau"],
       "luồng HÌNH giống TỪNG BYTE (`-c:v copy`)",
       f"{v['md5_v_truoc'][-12:]} vs {v['md5_v_sau'][-12:]}")
    ok(abs(v["dai_truoc"] - v["dai_sau"]) <= 0.05,
       "độ dài không đổi", f"{v['dai_truoc']:.3f} -> {v['dai_sau']:.3f}s")

    goc = _sinh("qua_nho")
    dais = []
    for i in range(5):
        d = TAM / f"_lap{i}.mp4"
        shutil.copy2(goc, d)
        chuan_do_to_clip(d)
        dais.append(round(probe(d).duration, 3))
        d.unlink(missing_ok=True)
    ok(len(set(dais)) == 1,
       "5 lượt ra ĐÚNG MỘT con số độ dài (bẫy `asplit` không tiền định)",
       f"{dais}")


def ca9_hai_thuoc(kq: dict) -> None:
    """Đối chiếu thước thứ hai — bắt phép đo hỏng."""
    print("\n== CA 9: hai thước độc lập nói cùng chuyện ==")
    import json as _json
    import re as _re
    xau = []
    for k, v in kq.items():
        if v.get("bo_qua"):
            continue        # clip gần câm: loudnorm trả -inf, so sánh vô nghĩa
        p = v["moi"]
        r = subprocess.run([FF, "-hide_banner", "-nostdin", "-i", str(p),
                            "-af", "loudnorm=I=-14:TP=-1:LRA=11:print_format=json",
                            "-f", "null", "-"], capture_output=True,
                           timeout=600, stdin=subprocess.DEVNULL)
        e = (r.stderr or b"").decode("utf-8", "replace")
        m = _re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", e, _re.S)
        if not m:
            xau.append((k, "loudnorm không trả JSON"))
            continue
        ln = float(_json.loads(m.group(0))["input_i"])
        if abs(ln - v["sau"]["I"]) > 0.8:
            xau.append((k, f"loudnorm {ln:.2f} vs ebur128 {v['sau']['I']:.2f}"))
    ok(not xau, "hai thước lệch <= 0,8 LU trên mọi ca "
                "(lệch có hệ thống đã đo: loudnorm đọc THẤP 0,12-0,58 LU)",
       f"{xau}" if xau else "")


def ca10_noi_vao_duong_xuat() -> None:
    """**CỬA DUY NHẤT**: phải gọi ở THÂN hàm, KHÔNG nằm trong nhánh if/elif.

    Nằm trong một nhánh nghĩa là Mixed-Cut / clip đơn KHÔNG được chuẩn hoá —
    đúng lỗ hổng của che chữ (cổng 56: *"Mixed-Cut và mẫu clip đơn KHÔNG che"*)
    và của mẫu-theo-kênh (cổng 19a). Đọc bằng **AST**, không tìm chuỗi: tìm
    chuỗi thì đổi thành `if 0: chuan_do_to_clip(...)` vẫn xanh (bẫy cổng 56d).
    """
    print("\n== CA 10: đã NỐI vào đường xuất, ở CỬA DUY NHẤT ==")
    import ast

    src = (REPO / "app" / "modules" / "m1_highlight.py").read_text(
        encoding="utf-8")
    cay = ast.parse(src)
    ham = next((n for n in ast.walk(cay)
                if isinstance(n, ast.FunctionDef)
                and n.name == "_export_clip_impl"), None)
    ok(ham is not None, "tìm thấy `_export_clip_impl`")
    if ham is None:
        return

    def _goi(node) -> int:
        n = 0
        for x in ast.walk(node):
            if isinstance(x, ast.Call):
                f = x.func
                ten = (getattr(f, "id", None) or getattr(f, "attr", None) or "")
                if "chuan_do_to_clip" in ten or ten in ("_chuan_dt",):
                    n += 1
        return n

    tong = _goi(ham)
    ok(tong >= 1, "đường xuất CÓ gọi chuẩn hoá độ to", f"{tong} chỗ")

    # Chỗ gọi phải nằm ở THÂN hàm (trong `try` thì được), KHÔNG được nằm trong
    # `if/for/while` ở BẤT KỲ ĐỘ SÂU NÀO.
    #
    # BẢN ĐẦU CHỈ XÉT ĐỘ SÂU 1 và ĐÃ CÓ LỖ: nó bỏ qua lệnh `If` ở thân hàm rồi
    # `ast.walk` cả phần còn lại, nên `try: if ...: chuan_do_to_clip(...)` vẫn
    # được đếm là "ở thân hàm". Phép phá tương ứng lúc đó làm cổng đỏ chỉ vì
    # thụt lề sai (IndentationError) — tức cổng ĐỎ OAN, chứ không phải nó bắt
    # được; đúng họ bẫy "cổng ĐẠT/ĐỎ vì lượt chạy chết trước khi tới chốt".
    def _quet(node, trong: bool) -> list:
        ra = []
        for con in ast.iter_child_nodes(node):
            if isinstance(con, ast.Call):
                f = con.func
                ten = (getattr(f, "id", None) or getattr(f, "attr", None) or "")
                if "chuan_do_to_clip" in ten or ten == "_chuan_dt":
                    ra.append(trong)
            ra += _quet(con, trong or isinstance(con,
                                                 (ast.If, ast.For, ast.While,
                                                  ast.IfExp)))
        return ra

    cho = _quet(ham, False)
    ok(bool(cho) and not any(cho),
       "gọi ở THÂN hàm — mọi nhánh (cắt thường · ghép · recap · Mixed-Cut · "
       "clip đơn) đều đi qua",
       f"{cho.count(False)}/{len(cho)} chỗ gọi nằm NGOÀI mọi if/for/while")

    # HUỶ phải nổi lên: phải có `except CanceledError: raise` bọc lượt gọi
    co_huy = False
    for lenh in ham.body:
        if not isinstance(lenh, ast.Try) or not _goi(lenh):
            continue
        for h in lenh.handlers:
            ten = (getattr(h.type, "id", None) or getattr(h.type, "attr", None)
                   or "")
            if "Canceled" in ten and any(isinstance(b, ast.Raise)
                                         for b in h.body):
                co_huy = True
    ok(co_huy, "HUỶ nổi lên nguyên vẹn (`except CanceledError: raise`) — "
               "huỷ là huỷ, không 'lùi êm'")


def ca11_hong_thi_giu_clip() -> None:
    print("\n== CA 11: chuẩn hoá HỎNG -> GIỮ NGUYÊN clip, không mất video ==")
    import hashlib
    from app.core import ffmpeg_utils as fu

    p = TAM / "hong.mp4"
    if not p.exists():
        import shutil
        shutil.copy2(_sinh("qua_nho"), p)
    truoc = hashlib.md5(p.read_bytes()).hexdigest()
    that = fu._ap_do_to
    try:
        def _no(*a, **k):
            raise RuntimeError("giả lập: đĩa đầy giữa lượt chuẩn hoá")
        fu._ap_do_to = _no
        kq = fu.chuan_do_to_clip(p)
    finally:
        fu._ap_do_to = that
    ok(kq["bo_qua"] is True, "trả bo_qua=True, KHÔNG ném ra ngoài",
       kq.get("ly_do", "")[:60])
    ok(truoc == hashlib.md5(p.read_bytes()).hexdigest(),
       "clip gốc còn NGUYÊN từng byte")
    rac = [x.name for x in p.parent.glob("_dt_*")]
    ok(not rac, "không bỏ lại file tạm `_dt_*`", f"{rac}" if rac else "")


def ca13_khong_lech_hinh_tieng(kq: dict) -> None:
    """QUÁ MẪU CÓ ĐẨY TIẾNG LỆCH KHỎI HÌNH KHÔNG — đo bằng TƯƠNG QUAN CHÉO.

    Đây là họ lỗi v1.87 (*"hình một đằng tiếng một đằng"*) và là lý do
    `alimiter` phải có `latency=1`. Thêm hai lượt `aresample` nữa thì phải
    chứng minh LẠI, không được suy: đo lệch mẫu giữa tiếng TRƯỚC và SAU.
    """
    print("\n== CA 13: tiếng KHÔNG lệch hình sau khi quá mẫu ==")
    import array
    import wave

    def _mau(p: Path, ten: str):
        w = TAM / f"{ten}.wav"
        subprocess.run([FF, "-y", "-hide_banner", "-nostdin", "-i", str(p),
                        "-vn", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le",
                        str(w)], capture_output=True, timeout=300,
                       stdin=subprocess.DEVNULL)
        with wave.open(str(w), "rb") as f:
            a = array.array("h")
            a.frombytes(f.readframes(f.getnframes()))
        return a

    a = _mau(kq["de_do_lech"]["goc"], "sync_a")
    b = _mau(kq["de_do_lech"]["moi"], "sync_b")
    n = min(len(a), len(b))
    N = min(n, 48000 * 4)
    tot, diem = 0, -1e18
    for lag in range(-240, 241):            # quét ±5 ms
        s = 0.0
        for i in range(3000, N - 3000, 7):
            s += a[i] * b[i + lag]
        if s > diem:
            tot, diem = lag, s
    ok(tot == 0, "lệch tiếng-hình = 0 mẫu (tương quan chéo, quét ±5 ms)",
       f"{tot} mẫu = {tot / 48.0:+.3f} ms")


def ca12_huy_la_huy() -> None:
    print("\n== CA 12: HUỶ giữa lúc chuẩn hoá -> nổi lên, không bị nuốt ==")
    import hashlib
    from app.core import ffmpeg_utils as fu
    from app.queue.worker import CanceledError

    p = TAM / "huy.mp4"
    if not p.exists():
        import shutil
        shutil.copy2(_sinh("qua_nho"), p)
    truoc = hashlib.md5(p.read_bytes()).hexdigest()
    that = fu._ap_do_to
    try:
        def _huy(*a, **k):
            raise CanceledError("người dùng bấm Huỷ")
        fu._ap_do_to = _huy
        try:
            fu.chuan_do_to_clip(p)
            ok(False, "phải ném CanceledError")
        except CanceledError:
            ok(True, "CanceledError NỔI LÊN nguyên vẹn")
        except Exception as e:  # noqa: BLE001
            ok(False, "phải ném CanceledError", f"ném {type(e).__name__}")
    finally:
        fu._ap_do_to = that
    ok(truoc == hashlib.md5(p.read_bytes()).hexdigest(),
       "huỷ xong clip vẫn nguyên")


# ==================================================================
def chuan_bi() -> dict:
    """Chuẩn hoá 4 nguồn, giữ lại số đo + md5 luồng hình để các ca dùng chung."""
    import shutil
    from app.core.ffmpeg_utils import chuan_do_to_clip, probe

    kq: dict = {}
    print("\n== CHUẨN BỊ: dựng nguồn + chạy `chuan_do_to_clip` THẬT ==")
    for ten in NGUON:
        goc = _sinh(ten)
        moi = TAM / f"{ten}_moi.mp4"
        shutil.copy2(goc, moi)
        v = {"goc": goc, "moi": moi,
             "md5_v_truoc": _md5_luong(moi, "v"),
             "dai_truoc": probe(moi).duration}
        r = chuan_do_to_clip(moi)
        v.update(r)
        if "sau" not in v:
            v["sau"] = v["truoc"]
        v["md5_v_sau"] = _md5_luong(moi, "v")
        v["dai_sau"] = probe(moi).duration
        kq[ten] = v
        print(f"  {ten:12} I {v['truoc']['I']:7.2f} -> {v['sau']['I']:7.2f} · "
              f"TP {v['truoc']['TP']:+6.2f} -> {v['sau']['TP']:+6.2f} · "
              f"nâng {r.get('nang_db', 0):+.2f} dB · bậc {r.get('buoc')} · "
              f"{'BỎ QUA' if r.get('bo_qua') else 'đã chỉnh'}")
    return kq


def main() -> int:
    print("=" * 78)
    print("CỔNG 66 — CHUẨN HOÁ ĐỘ TO CHO MỌI ĐƯỜNG XUẤT CLIP")
    print(f"ffmpeg: {FF}")
    print("=" * 78)
    kq = chuan_bi()
    ca0_nguon_dung_ca_bien(kq)
    ca1_hang_so()
    ca2_do_hong_phai_nem()
    ca3_he_so_la_hang_so(kq)
    ca4_dat_dich_va_tran(kq)
    ca5_khong_nen_dap(kq)
    ca6_khong_dung_clip_da_dung()
    ca7_san_chong_nang_dien()
    ca8_hinh_va_do_dai(kq)
    ca9_hai_thuoc(kq)
    ca10_noi_vao_duong_xuat()
    ca11_hong_thi_giu_clip()
    ca12_huy_la_huy()
    ca13_khong_lech_hinh_tieng(kq)
    print("\n" + "=" * 78)
    print(f"ĐẠT {DAT} · HỎNG {HONG}")
    print("=" * 78)
    return 1 if HONG else 0


if __name__ == "__main__":
    raise SystemExit(main())
