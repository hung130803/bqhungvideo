# -*- coding: utf-8 -*-
"""ĐO QUÁ TẢI LUỒNG ffmpeg của đường XUẤT CLIP (giai đoạn 0 của việc hiệu ứng).

VÌ SAO PHẢI CÓ FILE NÀY (bài học 07/08/2026):
  - Mọi phép đo bằng WALL-TIME hôm 07/08 đều SAI vì app thật của anh Hùng đang
    chạy 96,7% CPU: CÙNG 1 cấu hình ra 61,2s / 51,8s / 141,8s / 12,1s.
    => phải đo **CPU-GIÂY** (`cpu_times().user + .system` của TIẾN TRÌNH ffmpeg
    con) — số này không phụ thuộc máy đang bận hay rảnh.
  - Lần thử trước thêm `-threads`+`-filter_threads` vào `_build_seg` rồi đo
    **1 lượt xuất đơn độc** -> thấy chậm 3,4 lần rồi revert. ĐÓ LÀ PHÉP ĐO SAI
    CÂU HỎI: giới hạn luồng được thiết kế cho 10 LƯỢT SONG SONG, đo 1 lượt thì
    đương nhiên chậm. Câu hỏi thật là: **10 lượt song song xong lúc nào**.
    File này đo cả 2 chế độ: N=1 (đối chứng) và N=10 (cảnh sản xuất thật).

CÁCH DÙNG:
    .venv\\Scripts\\python _do_luong_ffmpeg.py --luot 1 --lap 3
    .venv\\Scripts\\python _do_luong_ffmpeg.py --luot 10 --lap 1

CANH CỔNG: máy phải RẢNH (cpu < 20% trong 5 giây, không có BQHungVideo.exe /
ffmpeg.exe lạ) — máy bận thì DỪNG, báo lỗi, không cho ra số rác.
"""
from __future__ import annotations

import argparse
import os
import statistics
import sys
import tempfile
import threading
import time
from pathlib import Path

# ---- sandbox TRƯỚC khi import app: không đụng DB/dữ liệu thật của anh Hùng ----
_SB = Path(tempfile.gettempdir()) / f"do_luong_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))

import psutil  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))

# console Windows mặc định cp1252 -> print tên video Nhật là nổ UnicodeEncodeError
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass

THUNG = Path(r"C:\Users\Admin\Downloads\thùng rác")


def _may_ranh(giay: float = 5.0) -> tuple[bool, str]:
    """True nếu máy đủ rảnh để đo. Kiểm CẢ tiến trình lạ CẢ mức CPU.

    BẪY ĐÃ SẬP (07/08/2026): chặn MỌI `ffmpeg.exe` thì phép đo không bao giờ
    chạy được trên máy anh Hùng — tool TẢI (`bqhungdown`) cũng spawn ffmpeg để
    mux `-c copy` (gần 0 CPU, chỉ I/O) suốt ngày. Nay chỉ DỪNG HẲN khi thấy
    ffmpeg của chính app CẮT (cha là BQHungVideo/python) hoặc CPU >= 20%;
    ffmpeg của cây tải chỉ ghi CẢNH BÁO (CPU-giây miễn nhiễm, wall-time nhiễu
    nhẹ -> đã lấy trung vị nhiều lần).
    """
    nang, nhe = [], []
    for p in psutil.process_iter(["name"]):
        n = (p.info["name"] or "").lower()
        if n == "bqhungvideo.exe":
            nang.append(f"{n}(pid {p.pid})")
        elif n == "ffmpeg.exe":
            try:
                par = p.parent()
                pn = (par.name() or "").lower() if par else ""
            except psutil.Error:
                pn = ""
            (nhe if pn in ("yt-dlp.exe", "bqhungdown.exe") else nang).append(
                f"{n}(pid {p.pid}, cha {pn or '?'})")
    if nang:
        return False, "Có tiến trình CẮT đang chạy: " + ", ".join(nang[:6])
    vals = [psutil.cpu_percent(interval=1.0) for _ in range(int(giay))]
    tb = sum(vals) / len(vals)
    ghi = f"CPU {tb:.1f}% {vals}"
    if nhe:
        ghi += f" · [chấp nhận] ffmpeg TẢI: {', '.join(nhe[:4])}"
    if tb >= 20.0:
        return False, f"CPU đang {tb:.1f}% (cần < 20%): {vals}"
    return True, ghi


def tim_video_nhat(so: int = 3) -> list[Path]:
    """Tìm video có ký tự tiếng Nhật trong tên THƯ MỤC KÊNH hoặc tên file."""
    ra: list[Path] = []
    if not THUNG.exists():
        return ra
    for p in THUNG.rglob("*.mp4"):
        try:
            if p.stat().st_size < 5_000_000:
                continue
        except OSError:
            continue
        txt = str(p)
        if any("぀" <= c <= "ヿ" or "一" <= c <= "鿿"
               for c in txt):
            ra.append(p)
            if len(ra) >= so:
                break
    return ra


class DoLuong:
    """Lấy mẫu 20 lần/giây: tổng số LUỒNG của mọi ffmpeg con + CPU-giây cộng dồn.

    CPU-giây phải đọc TRƯỚC khi tiến trình chết (Windows: proc chết là mất
    cpu_times) -> giữ bản ghi cuối cùng theo pid rồi cộng lại.
    """

    def __init__(self, goc_pid: int | None = None) -> None:
        self.goc = goc_pid or os.getpid()
        self._stop = threading.Event()
        self.dinh_luong = 0
        self.mau_luong: list[int] = []
        self.dinh_tt = 0                    # đỉnh SỐ tiến trình ffmpeg
        self._cpu: dict[int, float] = {}    # pid -> CPU-giây cuối đọc được
        self._rss: dict[int, int] = {}
        self.th = threading.Thread(target=self._vong, daemon=True)

    def _con_ffmpeg(self) -> list[psutil.Process]:
        ra = []
        try:
            me = psutil.Process(self.goc)
        except psutil.Error:
            return ra
        try:
            for c in me.children(recursive=True):
                try:
                    if "ffmpeg" in (c.name() or "").lower():
                        ra.append(c)
                except psutil.Error:
                    continue
        except psutil.Error:
            pass
        return ra

    def _vong(self) -> None:
        while not self._stop.is_set():
            tong = 0
            n = 0
            for c in self._con_ffmpeg():
                try:
                    tong += c.num_threads()
                    ct = c.cpu_times()
                    self._cpu[c.pid] = float(ct.user) + float(ct.system)
                    self._rss[c.pid] = int(c.memory_info().rss)
                    n += 1
                except psutil.Error:
                    continue
            if n:
                self.mau_luong.append(tong)
                self.dinh_luong = max(self.dinh_luong, tong)
                self.dinh_tt = max(self.dinh_tt, n)
            time.sleep(0.05)

    def __enter__(self):
        self.th.start()
        return self

    def __exit__(self, *a):
        self._stop.set()
        self.th.join(timeout=3)
        return False

    @property
    def cpu_giay(self) -> float:
        return round(sum(self._cpu.values()), 2)

    @property
    def tb_luong(self) -> float:
        return round(statistics.mean(self.mau_luong), 1) if self.mau_luong else 0.0

    @property
    def dinh_rss_gb(self) -> float:
        return round(sum(self._rss.values()) / 1e9, 2) if self._rss else 0.0


def _ass_mau(dst: Path, dai: float) -> Path:
    """File .ass tối giản có chữ chạy — để phép đo có CẢ phần đốt phụ đề
    (chỗ ăn CPU nặng nhất trong graph, theo số đo 07/08)."""
    dong = []
    t = 0.0
    i = 0
    while t < dai:
        a, b = t, min(dai, t + 0.6)

        def _hms(v: float) -> str:
            return (f"{int(v // 3600)}:{int(v // 60) % 60:02d}:"
                    f"{v % 60:05.2f}")
        dong.append(f"Dialogue: 0,{_hms(a)},{_hms(b)},D,,0,0,0,,"
                    f"{{\\an2}}CHU CHAY SO {i}")
        t += 0.6
        i += 1
    dst.write_text(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
        "[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,"
        "SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,"
        "StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,"
        "Alignment,MarginL,MarginR,MarginV,Encoding\n"
        "Style: D,Arial,110,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,"
        "-1,0,0,0,100,100,0,0,1,6,0,2,60,60,180,1\n\n"
        "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,"
        "MarginV,Effect,Text\n" + "\n".join(dong) + "\n",
        encoding="utf-8")
    return dst


def mot_luot(src: Path, out: Path, ass: Path, **kw) -> float:
    """1 lượt xuất y như app: 2 đoạn (hook-first = NGƯỢC thời gian), nền mờ,
    phụ đề .ass đốt vào, 1080x1920. Trả wall-time."""
    from app.core import ffmpeg_utils as fu
    t0 = time.perf_counter()
    fu.export_canvas_clip(
        str(src), str(out),
        segments=[(60.0, 70.0), (20.0, 30.0)],   # NGƯỢC thời gian = hook-first
        video_rect=(0.5, 0.42, 0.98), bg="blur",
        out_w=1080, out_h=1920,
        ass_path=str(ass), fx_fade=True, fx_whoosh=True, **kw)
    return round(time.perf_counter() - t0, 2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--luot", type=int, default=1, help="số lượt xuất SONG SONG")
    ap.add_argument("--lap", type=int, default=3, help="lặp lại mấy lần (lấy trung vị)")
    ap.add_argument("--bo-canh", action="store_true", help="bỏ kiểm máy rảnh")
    a = ap.parse_args()

    ok, vi = _may_ranh()
    print(f"[máy] {vi}")
    if not ok and not a.bo_canh:
        print("DỪNG: máy đang bận -> mọi số đo sẽ sai. "
              "Tắt app/ffmpeg rồi chạy lại (hoặc --bo-canh nếu chỉ thử chạy).")
        return 2

    vids = tim_video_nhat(1)
    if not vids:
        print("DỪNG: không tìm được video Nhật trong thùng rác.")
        return 2
    src = vids[0]
    from app.core import ffmpeg_utils as fu
    info = fu.probe(str(src))
    print(f"[nguồn] {src.name[:60]}… {info.width}x{info.height} "
          f"{info.fps:g}fps {info.duration:.0f}s audio={info.has_audio}")
    print(f"[encoder] {fu.detect_encoder()} · "
          f"_encode_budget={fu._encode_budget()} "
          f"encode_threads={fu.encode_threads()} "
          f"nhân={os.cpu_count()} ECO={os.environ.get('ECO_MODE', '(mặc định)')}")

    tmp = _SB / "out"
    tmp.mkdir(exist_ok=True)
    ass = _ass_mau(_SB / "sub.ass", 20.0)

    ket: list[dict] = []
    for lan in range(a.lap):
        outs = [tmp / f"l{lan}_{i}.mp4" for i in range(a.luot)]
        with DoLuong() as d:
            t0 = time.perf_counter()
            errs: list[str] = []

            def _work(i: int) -> None:
                try:
                    mot_luot(src, outs[i], ass)
                except Exception as e:  # noqa: BLE001
                    errs.append(f"{i}: {e}")

            ths = [threading.Thread(target=_work, args=(i,))
                   for i in range(a.luot)]
            for t in ths:
                t.start()
            for t in ths:
                t.join()
            wall = round(time.perf_counter() - t0, 2)
        cores = os.cpu_count() or 1
        r = {"wall": wall, "cpu_giay": d.cpu_giay, "dinh_luong": d.dinh_luong,
             "tb_luong": d.tb_luong, "dinh_tt": d.dinh_tt,
             "qua_tai": round(d.dinh_luong / cores, 2),
             "rss_gb": d.dinh_rss_gb,
             "kb": sum(o.stat().st_size for o in outs if o.exists()) // 1024,
             "loi": errs}
        ket.append(r)
        print(f"  lần {lan + 1}: wall {wall}s · CPU {d.cpu_giay}s · "
              f"đỉnh {d.dinh_luong} luồng ({r['qua_tai']}x nhân) · "
              f"TB {d.tb_luong} · {d.dinh_tt} tiến trình · "
              f"RSS {d.dinh_rss_gb}GB · out {r['kb']}KB"
              + (f" · LỖI {errs}" if errs else ""))
        for o in outs:
            o.unlink(missing_ok=True)

    print("\n=== TRUNG VỊ " + str(a.lap) + " lần, "
          + str(a.luot) + " lượt song song ===")
    for k in ("wall", "cpu_giay", "dinh_luong", "tb_luong", "qua_tai"):
        print(f"  {k:12s} = {statistics.median(r[k] for r in ket)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
