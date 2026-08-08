# -*- coding: utf-8 -*-
r"""CỔNG 42 — DỌN SẠCH RÁC TẠM · THẤY ĐƯỢC HIỆU ỨNG · ĐANG ĐỢI THÌ PHẢI NÓI.

Chạy: .venv\Scripts\python _test_rac_va_bao.py
Env: BQ_TEST=1 · PYTHONIOENCODING=utf-8 · **BQ_FFMPEG_SLOTS=1** (máy anh Hùng
đang làm việc thật — TUYỆT ĐỐI không đẻ nhiều ffmpeg).

3 việc anh Hùng nêu ngày 08/08/2026, mỗi việc 1 phần:

A. **RÒ FILE TẠM `_seg_*` KHI XUẤT LỖI / BỊ HUỶ.** Đo trước khi sửa
   (`_do_ro_seg.py`, ffmpeg thật, mảnh còn bị Windows khoá 2 giây đúng như lúc
   ffmpeg vừa bị kill): **6 file / 8,9 MB** nằm lại vĩnh viễn trong `%TEMP%`.
   Gốc: `_cleanup_dst` xoá 1 phát rồi `except OSError: pass` — nuốt
   PermissionError IM LẶNG; và đường "lùi nối cả clip" `del temps[:]` vô điều
   kiện nên mảnh chưa xoá được bị **xoá khỏi sổ** -> caller hết đường dọn.
   Phải đủ 3 lớp: THỬ LẠI có chờ · SỔ NỢ · QUÉT MỒ CÔI lúc mở app.
   BẤT BIẾN AN TOÀN: chỉ đụng đúng mẫu tên app đặt, TUYỆT ĐỐI không xoá file
   của user, không đụng mảnh của lượt xuất ĐANG chạy.

B. **NHÌN THẤY CLIP CÓ HIỆU ỨNG / TIẾNG ĐỘNG KHÔNG.** Anh Hùng: *"làm sao để
   biết có thêm hiệu ứng hay âm thanh gì k"*. Thẻ clip phải hiện
   "3 hiệu ứng · 2 tiếng động" (0 -> "không hiệu ứng"), bấm ra xem chi tiết
   giây/kiểu/LÝ DO KÈM SỐ. Chỉ hiện SỐ ĐÃ CÓ (`hieu_ung_log` /
   `tieng_dong_log` mà `export_canvas_clip` trả về) — cấm bịa.
   Nhãn KHÔNG EMOJI (máy anh Hùng thiếu glyph -> ô đen; cổng 9 và 27).

C. **THANH TIẾN TRÌNH ĐỨNG IM.** Anh Hùng: *"xuất đến 1 ngưỡng r đứng im k báo
   gì cả, phải 3 4 phút k hiện 1%"*. Gốc: `_run` xin chỗ ở cửa chờ TRƯỚC khi
   spawn ffmpeg; lúc đợi thì chưa có `time=` nào nên `_run_with_fallback` không
   nhích % và cũng không đổi chữ. Nay cửa chờ gọi hàm báo theo THREAD
   (`dat_bao_cho`) + XUẤT được ưu tiên hơn PHÂN TÍCH, kèm VAN CHỐNG ĐÓI
   (`_DOI_TOI_DA`) — cổng này ĐO CẢ HAI CHIỀU, vì ưu tiên trần trụi chính là
   lỗi "làn cắt chết đói vì LIMIT 50" đã sập một lần.

BẪY ĐO (đừng lặp):
  * ffmpeg trả rc=0 mà file 0 KHUNG -> mọi ca xuất phải `ffprobe` ĐẾM KHUNG.
  * đếm tiến trình ffmpeg phải theo `p.name()`, KHÔNG theo cmdline.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

_SB = Path(tempfile.gettempdir()) / f"racbao_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("BQ_QSETTINGS_INI", str(_SB / "s.ini"))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
os.environ.setdefault("ECO_MODE", "0")

import _test_guard  # noqa: E402,F401  (cổng 17: test KHÔNG được đụng máy user)

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

from app.core import ffmpeg_utils as fu  # noqa: E402
from config import settings  # noqa: E402

_NOWIN = 0x08000000
FF, FP = settings.FFMPEG_PATH, settings.FFPROBE_PATH
TMP = Path(tempfile.gettempdir())

_LOI: list[str] = []
_OK: list[str] = []


def bao(ten: str, dat: bool, so: str = "") -> None:
    (_OK if dat else _LOI).append(f"{ten} — {so}")
    print(f"  [{'OK  ' if dat else 'FAIL'}] {ten}" + (f": {so}" if so else ""))


# ===================== tiện ích đo =====================
def rac_seg() -> set:
    return {p.name for p in TMP.glob("_seg_*")}


def mb(names) -> float:
    t = 0
    for n in names:
        try:
            t += (TMP / n).stat().st_size
        except OSError:
            pass
    return t / 1e6


def so_khung(p) -> int:
    """ĐẾM KHUNG THẬT — bẫy 'rc=0 mà file 0 khung' (đã sập nhiều lần)."""
    r = subprocess.run(
        [FP, "-v", "error", "-select_streams", "v:0", "-count_frames",
         "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(p)],
        capture_output=True, text=True, creationflags=_NOWIN, timeout=180)
    try:
        return int((r.stdout or "0").strip().splitlines()[0])
    except (ValueError, IndexError):
        return -1


def nguon(ten: str, giay: float) -> Path:
    """Nguồn thử NGẮN tự sinh bằng lavfi (không phụ thuộc file trên máy)."""
    p = _SB / ten
    if p.exists():
        return p
    subprocess.run(
        [FF, "-y", "-hide_banner", "-v", "error",
         "-f", "lavfi", "-i", f"testsrc2=s=640x360:r=30:d={giay:g}",
         "-f", "lavfi", "-i", f"sine=f=440:r=48000:d={giay:g}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-shortest",
         str(p)], capture_output=True, timeout=300, creationflags=_NOWIN)
    return p


def nguon_dong(ten: str, giay: float) -> Path:
    """Nguồn NGẮN nhưng CÓ CAO TRÀO THẬT — nếu không thì `chon_hieu_ung` ĐÚNG
    khi trả 0 điểm ("clip phẳng không thêm gì ngớ ngẩn", luật anh Hùng đặt), và
    cổng sẽ FAIL OAN. Tiếng nền nhỏ + 2 cú nổ to -> dải động ~20 lần (ngưỡng
    `hieu_ung.PHANG` = 1,35)."""
    p = _SB / ten
    if p.exists():
        return p
    env = ("0.04+0.96*between(t,6,7)+0.96*between(t,13,14)")
    subprocess.run(
        [FF, "-y", "-hide_banner", "-v", "error",
         "-f", "lavfi", "-i", f"testsrc2=s=640x360:r=30:d={giay:g}",
         "-f", "lavfi", "-i", f"sine=f=440:r=48000:d={giay:g}",
         "-filter_complex", f"[1:a]volume=volume='{env}':eval=frame[a]",
         "-map", "0:v", "-map", "[a]",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-shortest",
         str(p)], capture_output=True, timeout=300, creationflags=_NOWIN)
    return p


def _cua_so_khoa(giay: float):
    """Dựng lại CỬA SỔ KHOÁ của Windows: file `_seg_*` vừa bị kill thì `giay`
    giây đầu KHÔNG xoá được (PermissionError), sau đó xoá được.

    Đây KHÔNG phải mock ffmpeg (ffmpeg vẫn chạy thật) — chỉ tái hiện hành vi
    của HỆ ĐIỀU HÀNH, đúng thứ `_cleanup_dst` đang nuốt im lặng."""
    goc = Path.unlink
    het = time.time() + giay

    def vaunlink(self, missing_ok=False):
        if "_seg_" in self.name and time.time() < het:
            raise PermissionError(32, "The process cannot access the file")
        return goc(self, missing_ok=missing_ok)

    Path.unlink = vaunlink                              # type: ignore[assignment]
    return goc


# =====================================================================
# PHẦN A — RÒ FILE TẠM `_seg_*`
# =====================================================================
def a1_thu_lai_khi_khoa() -> None:
    print("\n[A1] file bị khoá TẠM THỜI -> phải THỬ LẠI cho tới khi xoá được")
    p = TMP / f"_seg_p{os.getpid()}h0a0a0a_tam.mkv"
    p.write_bytes(b"x" * 2048)
    fh = open(p, "rb")
    threading.Timer(0.8, fh.close).start()      # nhả khoá sau 0,8s
    t0 = time.time()
    sach = fu._cleanup_dst(str(p))
    dt = time.time() - t0
    bao("khoá 0,8s -> vẫn xoá được (bản cũ bỏ cuộc ngay lần đầu)",
        sach and not p.exists(), f"chờ {dt:.2f}s · còn file = {p.exists()}")
    try:
        p.unlink()
    except OSError:
        pass


def a2_so_no() -> None:
    print("\n[A2] xoá KHÔNG được -> phải VÀO SỔ NỢ, không mất dấu")
    p = TMP / f"_seg_p{os.getpid()}h0b0b0b_no.mkv"
    p.write_bytes(b"y" * 2048)
    fh = open(p, "rb")
    try:
        sach = fu._cleanup_dst(str(p))
        con = fu._cleanup_paths([str(p)])
        bao("file khoá suốt -> báo CHƯA sạch (không nói dối là đã dọn)",
            not sach and con == [str(p)], f"sạch={sach} · còn={len(con)}")
        bao("file khoá suốt -> nằm trong SỔ NỢ để dọn lại sau",
            str(p) in fu.rac_ton(), f"sổ nợ {len(fu.rac_ton())} mục")
    finally:
        fh.close()
    n = fu.don_rac_ton()
    bao("nhả khoá + `don_rac_ton()` -> dọn nốt, sổ nợ sạch",
        not p.exists() and str(p) not in fu.rac_ton(),
        f"dọn {n} mục · còn file = {p.exists()}")


def a3_xuat_loi_khi_khoa() -> None:
    """SỐ ĐO CHÍNH của việc 1: xuất LỖI trong cửa sổ khoá 2 giây."""
    print("\n[A3] XUẤT LỖI + mảnh còn bị KHOÁ 2 giây (ffmpeg THẬT)")
    src = nguon("a3.mp4", 20.0)
    segs = [(12.0, 18.0), (1.0, 7.0), (7.5, 11.5)]   # hook-first (ngược t/gian)
    xau = _SB / "la_thu_muc.mp4"
    xau.mkdir(exist_ok=True)                          # đích KHÔNG ghi được
    truoc = rac_seg()
    goc_unlink = _cua_so_khoa(2.0)
    try:
        fu.export_canvas_clip(src, xau, segs, (0.5, 0.45, 0.98), bg="blur",
                              out_w=540, out_h=960, encoder="libx264",
                              chuyen_canh="vua")
        e = None
    except Exception as ex:                           # noqa: BLE001
        e = ex
    finally:
        Path.unlink = goc_unlink                      # type: ignore[assignment]
    bao("đích không ghi được -> NÉM LỖI (không im lặng báo xong)",
        e is not None, f"{type(e).__name__ if e else 'KHÔNG NÉM GÌ'}")
    time.sleep(2.4)                                   # hết cửa sổ khoá
    fu.don_rac_ton()
    sot = sorted(rac_seg() - truoc)
    bao("xuất lỗi + khoá 2s -> KHÔNG rò mảnh `_seg_*` (trước: 6 file / 8,9 MB)",
        not sot, f"sót {len(sot)} file / {mb(sot):.1f} MB {sot[:4]}")
    for s in sot:
        try:
            (TMP / s).unlink()
        except OSError:
            pass


def a4_huy_giua_chung() -> None:
    print("\n[A4] HUỶ giữa lúc xuất (kill ffmpeg đúng kiểu app) — ffmpeg THẬT")
    from app.queue import worker as W
    src = nguon("a4.mp4", 20.0)
    segs = [(12.0, 18.0), (1.0, 7.0), (7.5, 11.5)]
    out = _SB / "a4_out.mp4"
    truoc = rac_seg()
    goc = W.current_job_canceled
    co_huy = threading.Event()
    W.current_job_canceled = lambda: co_huy.is_set()  # type: ignore[assignment]
    ket: dict = {}

    def chay() -> None:
        try:
            fu.export_canvas_clip(src, out, segs, (0.5, 0.45, 0.98), bg="blur",
                                  out_w=540, out_h=960, encoder="libx264",
                                  chuyen_canh="vua")
            ket["e"] = None
        except Exception as ex:                       # noqa: BLE001
            ket["e"] = ex

    t = threading.Thread(target=chay, daemon=True)
    t.start()
    time.sleep(1.6)
    with fu._PROC_LOCK:
        procs = list(fu._ACTIVE_PROCS)
    co_huy.set()
    for p in procs:                                   # kill KHÔNG chờ (như app)
        try:
            if p.poll() is None:
                p.kill()
        except OSError:
            pass
    t.join(timeout=180)
    W.current_job_canceled = goc                      # type: ignore[assignment]
    e = ket.get("e")
    bao("huỷ -> ném CanceledError", e is not None
        and type(e).__name__ == "CanceledError",
        f"{type(e).__name__ if e else 'KHÔNG NÉM GÌ'}")
    bao("huỷ -> KHÔNG để lại file đích dở", not out.exists(),
        "không có file" if not out.exists() else f"{out.stat().st_size} byte")
    fu.don_rac_ton()
    sot = sorted(rac_seg() - truoc)
    bao("huỷ -> DỌN SẠCH mảnh `_seg_*`", not sot,
        f"sót {len(sot)} file / {mb(sot):.1f} MB {sot[:4]}")


def a5_lui_khong_mat_dau() -> None:
    """Đường 'lùi nối cả clip' KHÔNG được xoá sổ mảnh chưa dọn được."""
    print("\n[A5] lùi 'nối cả clip' -> mảnh chưa xoá được PHẢI CÒN TRONG SỔ")
    goc_dst = fu._cleanup_dst
    fu._cleanup_dst = lambda p: False                 # type: ignore[assignment]
    try:
        temps = ["/tmp/_seg_pX_b0.mkv", "/tmp/_seg_pX_g0.mkv"]
        con = fu._cleanup_paths(list(temps))
        bao("`_cleanup_paths` TRẢ VỀ danh sách chưa xoá được",
            con == temps, f"{len(con)}/2 còn nợ")
    finally:
        fu._cleanup_dst = goc_dst                     # type: ignore[assignment]
    src = Path(REPO, "app", "core", "ffmpeg_utils.py").read_text(
        encoding="utf-8", errors="replace")
    i = src.find("lùi nối cả clip")
    than = src[max(0, i - 400):i + 500]
    bao("mã nguồn: sau `del temps[:]` phải TRẢ LẠI phần chưa xoá được",
        "temps.extend(con)" in than and "_cleanup_paths(list(temps))" in than,
        "có `con = _cleanup_paths(...)` + `temps.extend(con)`")
    bao("file danh sách concat `_seg_*_list.txt` cũng vào SỔ",
        src.count("temps.append(lst)") >= 2,
        f"{src.count('temps.append(lst)')}/2 chỗ tạo list.txt")


def a6_quet_mo_coi() -> None:
    print("\n[A6] QUÉT MỒ CÔI lúc mở app (app thoát bằng os._exit)")
    d = _SB / "motcoi"
    d.mkdir(exist_ok=True)
    pid_chet = 999_999_990          # PID không tồn tại
    chet = d / f"_seg_p{pid_chet}h1a2b3c_b0.mkv"
    song = d / f"_seg_p{os.getpid()}h1a2b3c_b0.mkv"
    cu = d / "_seg_06759624_b0.mkv"          # tên bản app CŨ (không có PID)
    user = d / "video cua anh Hung.mp4"      # FILE CỦA USER — cấm đụng
    khac = d / "_segment_gi_do.mkv"          # tên gần giống nhưng KHÔNG khớp
    for p in (chet, song, cu, user, khac):
        p.write_bytes(b"z" * 1024)
    n, byte = fu.don_seg_mo_coi(str(d))
    bao("xoá mảnh của tiến trình ĐÃ CHẾT", not chet.exists() and n == 1,
        f"{n} file / {byte} byte")
    bao("KHÔNG đụng mảnh của tiến trình CÒN SỐNG (lượt xuất đang chạy)",
        song.exists(), f"còn = {song.exists()}")
    bao("KHÔNG đụng file VIDEO CỦA USER trong %TEMP%", user.exists(),
        f"còn = {user.exists()}")
    bao("KHÔNG đụng tên gần giống mà không khớp mẫu", khac.exists(),
        f"còn = {khac.exists()}")
    bao("KHÔNG đụng mảnh tên kiểu CŨ (để `tempsweep` dọn theo tuổi 2 giờ)",
        cu.exists(), f"còn = {cu.exists()}")
    # tên mảnh THẬT phải mang dấu PID thì quét mồ côi mới có căn cứ
    src = Path(REPO, "app", "core", "ffmpeg_utils.py").read_text(
        encoding="utf-8", errors="replace")
    i = src.find("def _extract_segments_to_temp")
    bao("mảnh tạm THẬT được đặt tên có đóng dấu PID (`_tag_moi`)",
        "tag = _tag_moi()" in src[i:i + 4000],
        "`_seg_p<pid>h<hex>_...`")
    # nối vào lúc mở app
    ts = Path(REPO, "app", "core", "tempsweep.py").read_text(
        encoding="utf-8", errors="replace")
    bao("`tempsweep.quet_tat` (chạy lúc mở app) CÓ gọi `don_seg_mo_coi`",
        "don_seg_mo_coi" in ts, "đã nối vào bước dọn rác khởi động")
    from app.core import tempsweep as TS
    chet2 = TMP / f"_seg_p{pid_chet}h9f9f9f_b0.mkv"
    chet2.write_bytes(b"z" * 4096)
    TS.quet_tat(None, gio_min=999.0)     # tuổi 999h -> luật cũ KHÔNG dọn nổi
    bao("mở app -> mảnh mồ côi VỪA MỚI (chưa đủ 2 giờ) vẫn bị dọn",
        not chet2.exists(), f"còn = {chet2.exists()}")


# =====================================================================
# PHẦN B — NHÌN THẤY HIỆU ỨNG / TIẾNG ĐỘNG
# =====================================================================
def b0_manh_cung_pix_fmt() -> None:
    """LỖI THẬT tìm được khi làm việc 2 (CÓ TỪ BẢN `main`, không phải hồi quy).

    `_enc_mezz` thiếu `-pix_fmt yuv420p` ở nhánh **libx264** (nhánh nvenc thì
    có) -> mảnh CHUYỂN CẢNH (qua `filter_complex`) ra **yuv444p** còn mảnh THÂN
    ra yuv420p. Lệch pix_fmt giữa các file làm ffmpeg DỰNG LẠI filter graph mỗi
    mảnh, mà `metadata=print:file=` ghi đè file mỗi lần dựng lại -> `do_nhip`
    chỉ còn số của MẢNH CUỐI (4s/16s) -> clip "phẳng" -> **0 ĐIỂM NHẤN**.
    Đo trước khi sửa, CÙNG clip CÙNG máy: libx264 0 điểm · nvenc 3 điểm.
    Hậu quả: MÁY NHÂN VIÊN (không NVENC) mất sạch hiệu ứng, im lặng.
    """
    print("\n[B0] mảnh mezzanine phải CÙNG pix_fmt (nếu không: mất hiệu ứng)")
    from app.core import hieu_ung as HU
    src = nguon_dong("b0.mp4", 20.0)
    segs = [(12.0, 18.0), (1.0, 7.0), (7.5, 11.5)]
    temps: list = []
    lst, _ = fu._extract_segments_to_temp(
        str(src), segs, "libx264", None,
        chuyen_canh=fu.chon_chuyen_canh(segs, "nhe"), temps_out=temps)
    px = set()
    for t in temps:
        if not str(t).endswith(".mkv"):
            continue
        r = subprocess.run([FP, "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "stream=pix_fmt", "-of",
                            "csv=p=0", str(t)], capture_output=True, text=True,
                           creationflags=_NOWIN, timeout=60)
        px.add((r.stdout or "").strip())
    nl, cd = HU.do_nhip("", ffmpeg=FF,
                        dau_vao=["-f", "concat", "-safe", "0", "-i", lst])
    fu._cleanup_paths(temps)
    bao("libx264: MỌI mảnh cùng pix_fmt (trước: thân 420p / chuyển cảnh 444p)",
        px == {"yuv420p"}, f"pix_fmt các mảnh = {sorted(px)}")
    bao("nhờ vậy `do_nhip` đo được CẢ clip (trước: chỉ mảnh cuối 4s/16s)",
        len(nl) >= 15 and len(cd) >= 15,
        f"đo được {len(nl)}s tiếng · {len(cd)}s hình / 16s")
    r = HU.chon_hieu_ung(16.0, "manh", nl=nl, cd=cd, moc_noi=[6.0, 12.0],
                         co_the_dung=HU.dung_duoc())
    bao("=> máy KHÔNG NVENC vẫn chọn được điểm nhấn (trước: 0 điểm)",
        len(r) > 0, f"{len(r)} điểm nhấn")
    src_py = Path(REPO, "app", "core", "ffmpeg_utils.py").read_text(
        encoding="utf-8", errors="replace")
    i = src_py.find("def _enc_mezz")
    than = src_py[i:src_py.find("\ndef ", i + 10)]
    bao("CẢ HAI nhánh encoder mezzanine đều ép `-pix_fmt yuv420p`",
        than.count('"-pix_fmt", "yuv420p"') == 2,
        f"{than.count('-pix_fmt')} chỗ ép pix_fmt")


def b1_log_that() -> None:
    print("\n[B1] xuất THẬT -> trả về ĐÚNG hiệu ứng + tiếng động đã đưa vào file")
    src = nguon_dong("b1.mp4", 20.0)
    segs = [(12.0, 18.0), (1.0, 7.0), (7.5, 11.5)]
    out = _SB / "b1_out.mp4"
    hu: list = []
    td: list = []
    t0 = time.time()
    fu.export_canvas_clip(src, out, segs, (0.5, 0.45, 0.98), bg="blur",
                          out_w=540, out_h=960, encoder="libx264",
                          chuyen_canh="nhe", hieu_ung="manh",
                          hieu_ung_log=hu, tieng_dong_log=td)
    dt = time.time() - t0
    k = so_khung(out)
    bao("clip xuất được + ĐẾM KHUNG THẬT > 0 (bẫy rc=0 mà 0 khung)",
        k > 100, f"{k} khung · {dt:.1f}s · {out.stat().st_size // 1024} KB")
    bao("`hieu_ung_log` có điểm nhấn (không rỗng)", len(hu) > 0,
        f"{len(hu)} điểm: " + ", ".join(str(c.get("khoa")) for c in hu))
    # 08/08/2026 — ĐỔI KỲ VỌNG (MẠNH HƠN, không phải nới): tiếng động nay chèn
    # ở CẢ ĐIỂM NHẤN HÌNH chứ không chỉ điểm nối. Anh Hùng xem clip thật và
    # nói *"có hiệu ứng mà không có âm thanh"* — đo ra ĐÚNG 0,0 dB ở mốc điểm
    # nhấn (cổng 44). Nên ở đây kiểm ĐỦ CẢ HAI VAI, không kiểm mỗi con số 2.
    _noi = [t for t in td if t.get("vai") == "nối"]
    _nhan = [t for t in td if t.get("vai") == "điểm nhấn"]
    bao("`tieng_dong_log` có đúng 2 điểm NỐI (3 đoạn = 2 chỗ nối)",
        len(_noi) == 2, f"{len(_noi)} nối / {len(td)} tổng: "
        + ", ".join(f"{t['giay']}s/{t.get('vai')}/{t['loai']}" for t in td))
    _xa = [c for c in hu
           if all(abs(float(c["bat"]) - float(t["giay"])) >= 0.8 for t in _noi)]
    bao("MỖI điểm nhấn hình (không trùng chỗ nối) đều CÓ tiếng đi kèm",
        len(_nhan) == len(_xa),
        f"{len(_nhan)} tiếng / {len(_xa)} điểm nhấn: "
        + ", ".join(f"{c['bat']}s {c['khoa']}" for c in _xa))
    bao("mỗi hiệu ứng có LÝ DO KÈM SỐ (không chung chung)",
        bool(hu) and all(len(str(c.get("vi_sao", ""))) > 10
                         and any(ch.isdigit() for ch in str(c.get("vi_sao", "")))
                         for c in hu),
        (hu[0].get("vi_sao", "") if hu else "(0 điểm)")[:90])
    bao("mỗi tiếng động ghi rõ giây + loại + TÊN FILE",
        all(t.get("ten") and t.get("loai") is not None
            and t.get("giay") is not None for t in td),
        str(td[:1]))
    # `tieng_dong_log` là của LƯỢT NÀY, không phải biến toàn cục dùng chung
    td2: list = []
    fu.export_canvas_clip(src, _SB / "b1b_out.mp4", [(2.0, 6.0)],
                          (0.5, 0.45, 0.98), bg="blur", out_w=540, out_h=960,
                          encoder="libx264", tieng_dong_log=td2)
    bao("lượt 1 ĐOẠN + KHÔNG hiệu ứng -> log riêng của nó RỖNG, KHÔNG dính "
        "lượt trước", td2 == [] and len(td) >= 2,
        f"lượt A {len(td)} điểm · lượt B {len(td2)} điểm")
    return hu, td


def b2_luu_va_nhan(hu: list, td: list) -> None:
    print("\n[B2] lưu vào `clips.signals` + nhãn trên thẻ clip")
    from app import services
    from app.database.db import db
    from app.modules.m1_highlight import _luu_da_ap
    from app.ui.studio_page import StudioPage

    pid = services.create_project("Kênh đo hiệu ứng", "Nhóm test")
    vid = db.execute("INSERT INTO videos(project_id,src_path,duration) "
                     "VALUES(?,?,?)", (pid, str(_SB / "b1.mp4"),
                                       20.0)).lastrowid
    cid = db.execute(
        "INSERT INTO clips(video_id,title,start_sec,end_sec,status,signals,"
        "score,reason) VALUES(?,?,?,?,'suggested',?,?,?)",
        (vid, "Đoạn cãi nhau to", 1.0, 18.0,
         db.dumps({"segments": [[12, 18], [1, 7], [7.5, 11.5]], "n_seg": 3}),
         88, "cao trào rõ")).lastrowid
    _luu_da_ap(cid, hu, td, "manh", "canvas")
    row = db.query_one("SELECT signals FROM clips WHERE id=?", (cid,))
    sig = db.loads(row["signals"], {}) or {}
    da = sig.get("da_ap") or {}
    bao("`da_ap` ghi vào signals, KHÔNG đè mất dữ liệu cũ",
        bool(da) and sig.get("n_seg") == 3,
        f"{len(da.get('hieu_ung', []))} hiệu ứng · "
        f"{len(da.get('tieng_dong', []))} tiếng động · giữ n_seg")
    bao("hiệu ứng lưu kèm TÊN TIẾNG VIỆT (anh Hùng đọc được)",
        all(h.get("ten") for h in da.get("hieu_ung", [])),
        ", ".join(h.get("ten", "?") for h in da.get("hieu_ung", []))[:80])

    chu, mau, tip = StudioPage._nhan_hieu_ung(sig)
    bao("nhãn thẻ clip ghi ĐÚNG SỐ đã áp",
        chu == f"{len(hu)} hiệu ứng · {len(td)} tiếng động", chu)
    bao("0 hiệu ứng + 0 tiếng động -> ghi 'không hiệu ứng'",
        StudioPage._nhan_hieu_ung(
            {"da_ap": {"hieu_ung": [], "tieng_dong": []}})[0]
        == "không hiệu ứng · không tiếng động",
        StudioPage._nhan_hieu_ung(
            {"da_ap": {"hieu_ung": [], "tieng_dong": []}})[0])
    bao("clip CHƯA XUẤT (chưa có `da_ap`) -> KHÔNG hiện nhãn, không đoán bừa",
        StudioPage._nhan_hieu_ung({"n_seg": 2}) is None, "None")
    bao("mẫu THIẾU KHUNG VIDEO -> nhãn nói thẳng lý do",
        "mẫu thiếu khung video" in StudioPage._nhan_hieu_ung(
            {"da_ap": {"duong": "don", "hieu_ung": [], "tieng_dong": []}})[0],
        StudioPage._nhan_hieu_ung(
            {"da_ap": {"duong": "don", "hieu_ung": [],
                       "tieng_dong": []}})[0])
    return pid, vid, cid


def b3_ui_that(pid: int, vid: int, cid: int) -> None:
    print("\n[B3] UI THẬT: thẻ clip có nhãn + bấm ra hộp chi tiết")
    from PyQt6.QtWidgets import (QApplication, QDialog, QLabel, QPlainTextEdit,
                                 QPushButton, QWidget)

    from app.database.db import db
    from app.ui import theme
    from app.ui.studio_page import StudioPage

    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.QSS)          # QSS THẬT (bài học v2.6.23)
    sp = StudioPage.__new__(StudioPage)
    QWidget.__init__(sp)                  # thiếu dòng này là QMessageBox nổ

    class _St:
        project_id = pid
        video_id = vid

    sp.state = _St()
    c = db.query_one("SELECT * FROM clips WHERE id=?", (cid,))
    w = sp._clip_row(c, None, 1)
    nhan = [l for l in w.findChildren(QLabel)
            if "hiệu ứng" in (l.text() or "")]
    bao("thẻ clip THẬT có nhãn hiệu ứng", len(nhan) == 1,
        (nhan[0].text() if nhan else "KHÔNG THẤY")[:90])
    # bấm vào nhãn -> hộp chi tiết
    mo: dict = {}
    goc_exec = QDialog.exec

    def gia(self):
        mo["d"] = self
        return 0

    QDialog.exec = gia                    # type: ignore[assignment]
    try:
        sp._xem_hieu_ung(c, 1)
    finally:
        QDialog.exec = goc_exec           # type: ignore[assignment]
    d = mo.get("d")
    txt = ""
    if d is not None:
        for te in d.findChildren(QPlainTextEdit):
            txt = te.toPlainText()
    bao("bấm nhãn -> mở được hộp chi tiết", bool(txt), f"{len(txt)} ký tự")
    bao("hộp chi tiết nêu GIÂY + KIỂU + LÝ DO KÈM SỐ",
        "giây" in txt and "vì sao" in txt and "HIỆU ỨNG ĐIỂM NHẤN" in txt,
        [ln.strip() for ln in txt.splitlines()
         if "vì sao" in ln][:1] or ["(thiếu)"])
    bao("hộp chi tiết nêu TIẾNG ĐỘNG chỗ nối (loại + tên file)",
        "TIẾNG ĐỘNG CHỖ NỐI" in txt
        and any(t in txt for t in ("transition", "impact", "pop", "reveal",
                                   "riser", "tự sinh")),
        [ln.strip() for ln in txt.splitlines()
         if ln.strip().startswith("· giây")][-1:] or ["(thiếu)"])
    # KHÔNG EMOJI (máy anh Hùng thiếu glyph -> ô đen)
    def _emoji(s: str) -> list:
        return [ch for ch in s
                if ord(ch) > 0x2100 and ch not in "·—–…“”‘’≥≤×"]

    chu_ui = [l.text() or "" for l in w.findChildren(QLabel)]
    chu_ui += [b.text() or "" for b in w.findChildren(QPushButton)]
    if d is not None:
        chu_ui += [b.text() or "" for b in d.findChildren(QPushButton)]
        chu_ui += [d.windowTitle()]
    xau = [ch for s in chu_ui for ch in _emoji(s)]
    bao("KHÔNG emoji trong nhãn/nút/hộp chi tiết (máy thiếu glyph -> ô đen)",
        not xau, f"thấy {xau[:5]}" if xau else "0 ký tự emoji")
    bao("hộp chi tiết KHÔNG emoji trong nội dung", not _emoji(txt),
        f"thấy {_emoji(txt)[:5]}" if _emoji(txt) else "0 ký tự emoji")
    # nối vào đường xuất thật
    m1 = Path(REPO, "app", "modules", "m1_highlight.py").read_text(
        encoding="utf-8", errors="replace")
    bao("m1 truyền `tieng_dong_log` xuống `export_canvas_clip`",
        "tieng_dong_log=_td_log" in m1, "đã nối")
    bao("m1 gọi `_luu_da_ap` sau khi xuất xong", "_luu_da_ap(" in m1,
        "ghi vào clips.signals")


# =====================================================================
# PHẦN C — ĐANG ĐỢI THÌ PHẢI NÓI + ƯU TIÊN CÓ VAN CHỐNG ĐÓI
# =====================================================================
def c1_quet_tinh() -> None:
    print("\n[C1] quét tĩnh: cửa chờ CÒN + có đường báo trạng thái")
    src = Path(REPO, "app", "core", "ffmpeg_utils.py").read_text(
        encoding="utf-8", errors="replace")
    i = src.find("def _run(")
    than = src[i:src.find("\ndef ", i + 10)]
    bao("`_run` VẪN đi qua cửa chờ (bất biến cổng 36)",
        "_xin_cho_ffmpeg" in than, "còn nguyên")
    i2 = src.find("def _xin_cho_ffmpeg")
    than2 = src[i2:src.find("\ndef _tra_cho_ffmpeg", i2)]
    bao("`_xin_cho_ffmpeg` CÓ báo trạng thái lúc đợi",
        "_bao_cho(" in than2 and "đang đợi lượt" in than2, "có")
    bao("đường PHÂN TÍCH (tách audio) xin chỗ với ƯU TIÊN THẤP",
        "uu_tien=UT_PHAN_TICH" in src, "extract_audio_wav_why")
    m1 = Path(REPO, "app", "modules", "m1_highlight.py").read_text(
        encoding="utf-8", errors="replace")
    bao("job xuất GẮN hàm báo và GỠ ở finally (thread worker dùng lại)",
        "dat_bao_cho(_bao_cho)" in m1 and "dat_bao_cho(None)" in m1, "đủ 2 vế")
    an = Path(REPO, "app", "core", "analysis.py").read_text(
        encoding="utf-8", errors="replace")
    bao("đường PHÂN TÍCH cũng gắn/gỡ hàm báo",
        an.count("dat_bao_cho") >= 2, f"{an.count('dat_bao_cho')} chỗ")
    # ĐO TRƯỚC/SAU: bản TRƯỚC KHI có tính năng thì KHÔNG có đường báo nào.
    #
    # SỬA 08/08/2026 — CỔNG NÀY ĐÃ TỰ HỎNG SAU KHI GỘP VÀO `main`: mốc đối
    # chứng cứng là `main`, mà tính năng "đang đợi lượt" ĐÃ NẰM TRONG `main`
    # từ commit 8f41aea -> phép "đo TRƯỚC" luôn thấy tính năng và FAIL vĩnh
    # viễn (mặt trái của bẫy PASS-OAN-sau-merge trong CLAUDE.md: cùng gốc bệnh
    # "so với chính mình"). ĐÚNG: tìm ĐÚNG commit ĐƯA VÀO rồi lấy CHA của nó —
    # mốc đó chắc chắn là "bản trước khi sửa", không phụ thuộc merge sau này.
    moc = os.environ.get("BQ_MOC_REF", "main")
    r = subprocess.run(
        ["git", "-C", str(REPO), "log", "--format=%H", "--reverse",
         "-S", "dat_bao_cho", "--", "app/core/ffmpeg_utils.py"],
        capture_output=True, creationflags=_NOWIN, timeout=120)
    dua_vao = (r.stdout or b"").decode().split()
    truoc = f"{dua_vao[0]}^" if dua_vao else moc
    r2 = subprocess.run(["git", "-C", str(REPO), "show",
                         f"{truoc}:app/core/ffmpeg_utils.py"],
                        capture_output=True, creationflags=_NOWIN, timeout=60)
    cu = (r2.stdout or b"").decode("utf-8", errors="replace")
    if r2.returncode != 0 or len(cu) < 5000:
        bao(f"lấy được ffmpeg_utils.py của `{truoc}` để đối chứng", False,
            f"git rc={r2.returncode} · {len(cu)} ký tự")
        return
    bao(f"CHỐNG PASS OAN: bản mốc `{truoc[:12]}` phải KHÁC nhánh này",
        cu != src, f"mốc {len(cu)} ký tự vs nay {len(src)} ký tự")
    bao(f"ĐO TRƯỚC: bản `{truoc[:12]}` đợi slot mà KHÔNG báo một chữ nào",
        "dat_bao_cho" not in cu and "đang đợi lượt" not in cu,
        "0 đường báo (đúng triệu chứng 'đứng im 3-4 phút')")


def c2_bao_khi_doi() -> None:
    print("\n[C2] cửa chờ ĐẦY -> phải báo 'đang đợi lượt (N việc trước)'")
    bao("cửa chờ đang đo ở mức 1 chỗ (BQ_FFMPEG_SLOTS=1, luật máy anh Hùng)",
        fu.so_ffmpeg_song_song() == 1, f"{fu.so_ffmpeg_song_song()} chỗ")
    giu = fu._xin_cho_ffmpeg()             # chiếm chỗ duy nhất
    tin: list = []
    xong = threading.Event()

    def cho():
        fu.dat_bao_cho(lambda m: tin.append(m))
        try:
            if fu._xin_cho_ffmpeg():
                fu._tra_cho_ffmpeg()
        finally:
            fu.dat_bao_cho(None)
            xong.set()

    t = threading.Thread(target=cho, daemon=True)
    t.start()
    time.sleep(2.0)
    n_luc_doi = len(tin)
    if giu:
        fu._tra_cho_ffmpeg()
    xong.wait(10)
    t.join(timeout=10)
    bao("đợi 2 giây -> app nói ít nhất 3 lần (bản cũ: 0 lần)",
        n_luc_doi >= 3, f"{n_luc_doi} thông báo trong 2,0s")
    bao("câu báo nêu RÕ còn mấy việc đứng trước",
        any("đang đợi lượt" in m and "việc trước" in m for m in tin),
        tin[0] if tin else "(không có)")
    bao("tới lượt -> báo tiếp (thanh không kẹt ở chữ 'đang đợi')",
        any("đã tới lượt" in m for m in tin), tin[-1] if tin else "(không)")


def c3_uu_tien() -> None:
    print("\n[C3] ƯU TIÊN: XUẤT được đi trước PHÂN TÍCH khi tranh chỗ")
    giu = fu._xin_cho_ffmpeg()             # chiếm chỗ duy nhất
    thu_tu: list = []
    kloc = threading.Lock()

    def viec(ten: str, ut: int, san_sang: threading.Event):
        san_sang.set()
        if fu._xin_cho_ffmpeg(ut):
            with kloc:
                thu_tu.append(ten)
            time.sleep(0.05)
            fu._tra_cho_ffmpeg()

    ts = []
    for i in range(3):                     # PHÂN TÍCH vào hàng TRƯỚC
        ev = threading.Event()
        t = threading.Thread(target=viec, args=(f"phân tích{i}",
                                                fu.UT_PHAN_TICH, ev),
                             daemon=True)
        t.start()
        ev.wait(2)
        ts.append(t)
    time.sleep(0.4)
    for i in range(3):                     # XUẤT vào hàng SAU
        ev = threading.Event()
        t = threading.Thread(target=viec, args=(f"xuất{i}", fu.UT_XUAT, ev),
                             daemon=True)
        t.start()
        ev.wait(2)
        ts.append(t)
    time.sleep(0.4)
    bao("6 việc đang xếp hàng thật (phép đo có ý nghĩa)",
        fu.dang_doi_ffmpeg() == 6, f"{fu.dang_doi_ffmpeg()} việc trong hàng")
    if giu:
        fu._tra_cho_ffmpeg()
    for t in ts:
        t.join(timeout=30)
    bao("3 việc XUẤT được cấp chỗ TRƯỚC 3 việc phân tích (dù vào hàng sau)",
        [x.startswith("xuất") for x in thu_tu] == [True] * 3 + [False] * 3,
        " -> ".join(thu_tu))


def c4_khong_chet_doi() -> None:
    """ƯU TIÊN TRẦN TRỤI = BỎ ĐÓI. Phải chứng minh chiều ngược lại KHÔNG chết."""
    print("\n[C4] CHỐNG ĐÓI: dòng XUẤT chảy liên tục, phân tích vẫn tới lượt")
    goc_doi = fu._DOI_TOI_DA
    fu._DOI_TOI_DA = 1.5                   # hạ để đo nhanh (thật là 20s)
    dung = threading.Event()
    ket: dict = {}
    try:
        giu = fu._xin_cho_ffmpeg()

        def phan_tich():
            t0 = time.time()
            if fu._xin_cho_ffmpeg(fu.UT_PHAN_TICH):
                ket["cho"] = time.time() - t0
                time.sleep(0.05)
                fu._tra_cho_ffmpeg()

        tp = threading.Thread(target=phan_tich, daemon=True)
        tp.start()
        time.sleep(0.3)

        def dong_xuat():
            """Dòng việc XUẤT tới liên tục — đúng cảnh 200-300 kênh chạy loạt."""
            while not dung.is_set():
                if fu._xin_cho_ffmpeg(fu.UT_XUAT):
                    time.sleep(0.08)
                    fu._tra_cho_ffmpeg()
                time.sleep(0.02)

        tx = [threading.Thread(target=dong_xuat, daemon=True)
              for _ in range(4)]
        for t in tx:
            t.start()
        time.sleep(0.2)
        if giu:
            fu._tra_cho_ffmpeg()
        tp.join(timeout=30)
        dung.set()
        for t in tx:
            t.join(timeout=10)
    finally:
        fu._DOI_TOI_DA = goc_doi
        dung.set()
    cho = ket.get("cho", -1.0)
    bao("phân tích KHÔNG chết đói: được chỗ trong ~van chống đói (1,5s + 1 lượt)",
        0 <= cho <= 1.5 + 1.5, f"đợi {cho:.2f}s (trần {1.5}s + 1 lượt)")
    bao("van chống đói mặc định là 20 giây (đủ để xuất chen, đủ để không đói)",
        abs(fu._DOI_TOI_DA - 20.0) < 0.01, f"{fu._DOI_TOI_DA}s")


def c5_huy_va_dong_app() -> None:
    print("\n[C5] HUỶ / ĐÓNG APP lúc đang đợi -> không treo, không rò chỗ")
    from app.queue import worker as W
    giu = fu._xin_cho_ffmpeg()
    goc = W.current_job_canceled
    co_huy = threading.Event()
    W.current_job_canceled = lambda: co_huy.is_set()   # type: ignore[assignment]
    ket: dict = {}

    def cho():
        try:
            if fu._xin_cho_ffmpeg():
                fu._tra_cho_ffmpeg()
            ket["e"] = None
        except Exception as ex:                        # noqa: BLE001
            ket["e"] = ex

    t = threading.Thread(target=cho, daemon=True)
    t.start()
    time.sleep(0.6)
    co_huy.set()
    t.join(timeout=10)
    W.current_job_canceled = goc                       # type: ignore[assignment]
    bao("bấm Huỷ lúc ĐANG ĐỢI -> ném CanceledError NGAY (không đợi tới lượt)",
        ket.get("e") is not None
        and type(ket["e"]).__name__ == "CanceledError",
        type(ket.get("e")).__name__)
    bao("huỷ -> hàng chờ SẠCH (không rò chỗ, không kẹt người sau)",
        fu.dang_doi_ffmpeg() == 0, f"{fu.dang_doi_ffmpeg()} việc còn treo")
    # đóng app lúc đang đợi
    ket2: dict = {}

    def cho2():
        ket2["r"] = fu._xin_cho_ffmpeg()

    t2 = threading.Thread(target=cho2, daemon=True)
    t2.start()
    time.sleep(0.5)
    fu._SHUTDOWN.set()
    t2.join(timeout=10)
    fu._SHUTDOWN.clear()
    if giu:
        fu._tra_cho_ffmpeg()
    bao("đóng app lúc đang đợi -> trả False và ĐI LUÔN (không treo bước thoát)",
        ket2.get("r") is False, f"trả {ket2.get('r')}")
    bao("sau tất cả: cửa chờ về 0 chỗ đang giữ, 0 việc chờ",
        fu.dang_chay_ffmpeg() == 0 and fu.dang_doi_ffmpeg() == 0,
        f"{fu.dang_chay_ffmpeg()} chạy · {fu.dang_doi_ffmpeg()} chờ")


def c6_ffmpeg_that() -> None:
    """END-TO-END: 1 lệnh ffmpeg THẬT đi qua `_run` trong lúc cửa chờ bị chiếm."""
    print("\n[C6] ffmpeg THẬT qua `_run` lúc cửa chờ bị chiếm -> phải báo")
    giu = fu._xin_cho_ffmpeg()
    tin: list = []
    ket: dict = {}

    def chay():
        fu.dat_bao_cho(lambda m: tin.append(m))
        try:
            ket["rc"] = fu._run([FF, "-y", "-hide_banner", "-v", "error",
                                 "-f", "lavfi", "-i", "testsrc2=s=160x120:d=1",
                                 "-c:v", "libx264", "-preset", "ultrafast",
                                 str(_SB / "c6.mp4")])
        finally:
            fu.dat_bao_cho(None)

    t = threading.Thread(target=chay, daemon=True)
    t.start()
    time.sleep(1.5)
    n_doi = len(tin)
    if giu:
        fu._tra_cho_ffmpeg()
    t.join(timeout=60)
    k = so_khung(_SB / "c6.mp4")
    bao("lúc XẾP HÀNG: app báo đều đặn (bản cũ im lặng hoàn toàn)",
        n_doi >= 2, f"{n_doi} thông báo trong 1,5s chờ")
    bao("hết chờ -> ffmpeg THẬT chạy xong, file có khung hình",
        ket.get("rc") == 0 and k > 10, f"rc={ket.get('rc')} · {k} khung")


# =====================================================================
def main() -> int:
    print(f"ffmpeg: {FF} · cửa chờ {fu.so_ffmpeg_song_song()} chỗ "
          f"· sandbox {_SB}")
    print("\n########## PHẦN A — RÒ FILE TẠM `_seg_*` ##########")
    a1_thu_lai_khi_khoa()
    a2_so_no()
    a3_xuat_loi_khi_khoa()
    a4_huy_giua_chung()
    a5_lui_khong_mat_dau()
    a6_quet_mo_coi()
    print("\n########## PHẦN B — THẤY ĐƯỢC HIỆU ỨNG / TIẾNG ĐỘNG ##########")
    b0_manh_cung_pix_fmt()
    hu, td = b1_log_that()
    pid, vid, cid = b2_luu_va_nhan(hu, td)
    b3_ui_that(pid, vid, cid)
    print("\n########## PHẦN C — ĐANG ĐỢI THÌ PHẢI NÓI ##########")
    c1_quet_tinh()
    c2_bao_khi_doi()
    c3_uu_tien()
    c4_khong_chet_doi()
    c5_huy_va_dong_app()
    c6_ffmpeg_that()

    # KHÔNG ĐỂ RÁC MÁY USER (luật 4). Phải NHẢ HANDLE sqlite trước khi xoá,
    # nếu không `rmtree` bỏ lại `studio.db` (ignore_errors nuốt im lặng).
    import shutil
    for p in TMP.glob("_seg_*"):
        try:
            if p.is_file() and f"p{os.getpid()}h" in p.name:
                p.unlink()
        except OSError:
            pass
    try:
        from app.database.db import db as _db
        _db._reset_conn()
    except Exception:  # noqa: BLE001
        pass
    shutil.rmtree(_SB, ignore_errors=True)
    print(f"dọn sandbox: còn {_SB.exists()}")

    print(f"\n{'=' * 66}\nĐẠT {len(_OK)} · SAI {len(_LOI)}")
    if _LOI:
        for x in _LOI:
            print(f"  FAIL {x}")
        print("CỔNG 42 KHÔNG ĐẠT")
        return 1
    print("CỔNG 42 ĐẠT — hết rò rác tạm · thấy được hiệu ứng · "
          "đang đợi thì có báo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
