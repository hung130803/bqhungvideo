# -*- coding: utf-8 -*-
"""ĐO LUỒNG + CPU của khâu XUẤT CLIP — chạy trên VIDEO THẬT của anh Hùng.

    python _do_luong_xuat.py --nhan goc            # đo bản HIỆN TẠI, lưu mốc
    python _do_luong_xuat.py --nhan thu1 --lanes 3 # 3 luồng cắt song song
    python _do_luong_xuat.py --so goc thu1         # in bảng so 2 lượt

VÌ SAO CẦN: anh Hùng đo 1 lượt xuất đẻ ĐỈNH 62 luồng ffmpeg / TB 54; 3 luồng
cắt = ~186 luồng trên 24 nhân (8x quá tải), CPU 96,7% mà "GPU 0 - Video Encode"
chỉ 11,3%. Trước khi chữa phải biết luồng đẻ ra TỪ ĐÂU: pha 1 (tách đoạn ra
file tạm) hay pha 2 (dựng khung + phụ đề)? decode hay filter hay encode?

Bộ đo này bám TIẾN TRÌNH CON THẬT (psutil, nhịp 100ms), tách theo PHA nhờ đọc
dòng lệnh của từng ffmpeg, và hỏi nvidia-smi mức dùng NVENC cùng lúc. Không
mock cái gì.

BẪY ĐÃ BIẾT (đừng lặp): số CPU-giây phải lấy TRƯỚC khi tiến trình chết —
psutil.cpu_times() của tiến trình đã thoát ném NoSuchProcess, lấy sau là ra 0.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Sandbox: KHÔNG đụng DB/dữ liệu thật của anh Hùng (quy tắc sắt).
_SBOX = Path(tempfile.gettempdir()) / "_do_luong_sbox"
_SBOX.mkdir(exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SBOX))
os.environ.setdefault("BQ_DB_PATH", str(_SBOX / "do.db"))

import psutil  # noqa: E402

try:                                    # console Windows mặc định cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

# ---- CPU-giây CHÍNH XÁC: giữ HANDLE tiến trình rồi hỏi GetProcessTimes SAU
# KHI nó thoát (lấy mẫu là ĐẾM THIẾU nhịp cuối). Đặt ở đây để _do_pha_xuat và
# _do_uu_tien dùng chung, tránh nhập vòng.
import ctypes                                                   # noqa: E402
from ctypes import wintypes                                     # noqa: E402

_K32 = ctypes.WinDLL("kernel32", use_last_error=True)


def _mo_handle(pid: int):
    return _K32.OpenProcess(0x0400, False, pid) or None          # QUERY_INFO


def _cpu_giay(h) -> float:
    """(kernel+user) giây — đọc được cả khi tiến trình đã thoát."""
    ft = (wintypes.FILETIME * 4)()
    if not _K32.GetProcessTimes(h, *(ctypes.byref(f) for f in ft)):
        return -1.0
    def v(f):
        return (f.dwHighDateTime << 32 | f.dwLowDateTime) / 1e7
    return v(ft[2]) + v(ft[3])


CACHE = REPO / "_do_luong_cache"
CACHE.mkdir(exist_ok=True)
FF = str(REPO / "bin" / "ffmpeg.exe")
FP = str(REPO / "bin" / "ffprobe.exe")
_NO_WIN = 0x08000000 if sys.platform == "win32" else 0

#: VIDEO THẬT của anh Hùng (thùng rác = video đã tải về để cắt)
THUNG = Path(r"C:\Users\Admin\Downloads\thùng rác")


def chon_video(n: int = 3) -> list[str]:
    """Lấy n video THẬT: ưu tiên file 30-400 MB (đủ dài, không quá to)."""
    ra: list[str] = []
    for ngay in sorted(THUNG.glob("2026-*"), reverse=True):
        for f in sorted(ngay.rglob("*.mp4")):
            try:
                sz = f.stat().st_size
            except OSError:
                continue
            if 30 * 1024 ** 2 <= sz <= 400 * 1024 ** 2:
                ra.append(str(f))
                if len(ra) >= n:
                    return ra
    return ra


def probe(path: str) -> dict:
    r = subprocess.run(
        [FP, "-v", "error", "-print_format", "json", "-show_streams",
         "-show_format", str(path)],
        capture_output=True, text=True, errors="replace",
        creationflags=_NO_WIN)
    try:
        d = json.loads(r.stdout)
    except json.JSONDecodeError:
        return {}
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    a = next((s for s in d.get("streams", []) if s.get("codec_type") == "audio"), {})
    fps = 30.0
    try:
        num, den = v.get("r_frame_rate", "30/1").split("/")
        fps = float(num) / max(1.0, float(den))
    except (ValueError, ZeroDivisionError):
        pass
    return {"w": int(v.get("width") or 0), "h": int(v.get("height") or 0),
            "fps": fps, "codec": v.get("codec_name", "?"),
            "co_tieng": bool(a),
            "dur": float(d.get("format", {}).get("duration") or 0.0)}


# ---------------------------------------------------------------- theo dõi
class TheoDoi:
    """Bám mọi ffmpeg con: đếm LUỒNG theo nhịp + gom CPU-giây theo PHA.

    Pha đọc từ dòng lệnh: có '_seg_' trong tên file ra -> 'tách đoạn' (pha 1);
    có '-filter_complex' -> 'dựng khung' (pha 2); còn lại -> 'khác'.
    """

    def __init__(self, nhip: float = 0.1):
        self.nhip = nhip
        self._chay = False
        self._t: threading.Thread | None = None
        self.mau: list[dict] = []          # mỗi nhịp: {t, tong_luong, n_proc, pha:{}}
        self.cpu_proc: dict[int, dict] = {}  # pid -> {pha, cpu, luong_dinh, cmd}
        self.nvenc: list[float] = []
        self.cpu_he: list[float] = []
        self.tre: list[float] = []      # độ trễ nhịp luồng chính (ms)

    def _pha(self, cmd: list[str]) -> str:
        s = " ".join(cmd)
        if "_seg_" in s and "-filter_complex" not in s:
            return "tach_doan"
        if "-filter_complex" in s:
            return "dung_khung"
        return "khac"

    def _vong(self) -> None:
        me = psutil.Process()
        t0 = time.time()
        while self._chay:
            tong, npr = 0, 0
            theo_pha: dict[str, int] = {}
            try:
                con = me.children(recursive=True)
            except psutil.Error:
                con = []
            for p in con:
                try:
                    ten = p.name().lower()
                    if "ffmpeg" not in ten and "ffprobe" not in ten:
                        continue
                    nl = p.num_threads()
                    ct = p.cpu_times()
                    cmd = p.cmdline()
                except (psutil.Error, OSError):
                    continue
                pha = self._pha(cmd)
                if "ffprobe" in ten:
                    pha = "probe"
                tong += nl
                npr += 1
                theo_pha[pha] = theo_pha.get(pha, 0) + nl
                # ENCODER được YÊU CẦU ở lệnh này. `_run_with_fallback` thử
                # NVENC trước, hỏng thì spawn lệnh MỚI với libx264 -> đếm số
                # tiến trình theo encoder là bắt được cú "tụt về CPU" (đúng
                # cảnh báo CLAUDE.md: phải log encoder THỰC của mỗi lệnh).
                if p.pid not in self.cpu_proc:
                    # GIỮ HANDLE: đọc CPU-giây CHÍNH XÁC sau khi nó thoát. Lấy
                    # mẫu kiểu cũ ĐẾM THIẾU — nhịp cuối cách lúc chết tới
                    # 100ms × 24 nhân = hụt tới 2,4 CPU-giây mỗi tiến trình.
                    _s = " ".join(cmd)
                    self.cpu_proc[p.pid] = {
                        "pha": pha, "cpu": 0.0, "luong_dinh": 0, "cmd": cmd,
                        "enc": ("h264_nvenc" if "h264_nvenc" in _s else
                                "libx264" if "libx264" in _s else "-"),
                        "hwdec": "-hwaccel" in cmd,
                        "h": _mo_handle(p.pid)}
                cu = self.cpu_proc[p.pid]
                cu["cpu"] = ct.user + ct.system
                cu["luong_dinh"] = max(cu["luong_dinh"], nl)
            self.mau.append({"t": time.time() - t0, "tong_luong": tong,
                             "n_proc": npr, "pha": theo_pha})
            self.cpu_he.append(psutil.cpu_percent(interval=None))
            time.sleep(self.nhip)

    def _vong_gpu(self) -> None:
        while self._chay:
            try:
                r = subprocess.run(
                    ["nvidia-smi", "--query-gpu=utilization.encoder",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=5,
                    creationflags=_NO_WIN)
                self.nvenc.append(float(r.stdout.strip().splitlines()[0]))
            except (OSError, ValueError, IndexError, subprocess.SubprocessError):
                pass
            time.sleep(0.5)

    def _vong_ui(self) -> None:
        """ĐO ĐỘ ĐƠ: hẹn nhịp 50ms, xem thực tế bị TRỄ bao nhiêu. Đây chính là
        cái làm app "Not Responding" — luồng UI xin CPU mà không được cấp.
        Ngân sách CLAUDE.md mục 14: poll < 30ms."""
        while self._chay:
            t0 = time.perf_counter()
            time.sleep(0.05)
            self.tre.append((time.perf_counter() - t0 - 0.05) * 1000.0)

    def bat_dau(self) -> None:
        self._chay = True
        psutil.cpu_percent(interval=None)          # mồi
        self._t = threading.Thread(target=self._vong, daemon=True)
        self._t.start()
        self._g = threading.Thread(target=self._vong_gpu, daemon=True)
        self._g.start()
        self._u = threading.Thread(target=self._vong_ui, daemon=True)
        self._u.start()

    def dung(self) -> None:
        self._chay = False
        if self._t:
            self._t.join(timeout=3)

    def bao_cao(self) -> dict:
        for d in self.cpu_proc.values():        # số CUỐI CÙNG, sau khi chết
            h = d.pop("h", None)
            if h:
                v = _cpu_giay(h)
                if v >= 0:
                    d["cpu"] = v
                _K32.CloseHandle(h)
        co = [m for m in self.mau if m["n_proc"] > 0]
        luong = [m["tong_luong"] for m in co] or [0]
        cpu_pha: dict[str, float] = {}
        dinh_pha: dict[str, int] = {}
        for d in self.cpu_proc.values():
            cpu_pha[d["pha"]] = cpu_pha.get(d["pha"], 0.0) + d["cpu"]
            dinh_pha[d["pha"]] = max(dinh_pha.get(d["pha"], 0), d["luong_dinh"])
        dinh_theo_pha: dict[str, int] = {}
        for m in co:
            for k, v in m["pha"].items():
                dinh_theo_pha[k] = max(dinh_theo_pha.get(k, 0), v)
        return {
            "luong_dinh": max(luong),
            "luong_tb": sum(luong) / max(1, len(luong)),
            "luong_dinh_theo_pha": dinh_theo_pha,
            "luong_dinh_1_proc": {k: v for k, v in dinh_pha.items()},
            "cpu_giay_theo_pha": {k: round(v, 1) for k, v in cpu_pha.items()},
            "cpu_giay_tong": round(sum(cpu_pha.values()), 1),
            "n_proc": len(self.cpu_proc),
            "enc_dem": {e: sum(1 for d in self.cpu_proc.values()
                               if d.get("enc") == e)
                        for e in ("h264_nvenc", "libx264")},
            "n_hwdec": sum(1 for d in self.cpu_proc.values()
                           if d.get("hwdec")),
            "tre_tb": round(sum(self.tre) / max(1, len(self.tre)), 1),
            "tre_dinh": round(max(self.tre or [0]), 1),
            "tre_p95": round(sorted(self.tre)[int(len(self.tre) * 0.95)], 1)
            if self.tre else 0.0,
            "cpu_he_tb": round(sum(self.cpu_he) / max(1, len(self.cpu_he)), 1),
            "cpu_he_dinh": round(max(self.cpu_he or [0]), 1),
            "nvenc_tb": round(sum(self.nvenc) / max(1, len(self.nvenc)), 1),
            "nvenc_dinh": round(max(self.nvenc or [0]), 1),
        }


# ------------------------------------------------------------ dựng đầu vào
def lam_ass(dst: Path, segs: list, out_w: int, out_h: int) -> str:
    """Phụ đề .ass THẬT qua captions.build_ass (giống hệt đường sản xuất)."""
    from app.core import captions
    tong = sum(e - s for s, e in segs)
    # lời nói dày ~2,2 từ/giây (đo trên transcript thật) — đúng tải libass
    tu = ["chuyện", "này", "thật", "sự", "không", "ai", "ngờ", "tới", "được",
          "và", "rồi", "mọi", "thứ", "đã", "thay", "đổi", "hoàn", "toàn"]
    words, t = [], 0.0
    i = 0
    while t < tong - 0.5:
        d = 0.45
        words.append({"word": tu[i % len(tu)], "start": t, "end": t + d})
        t += d
        i += 1
    p = dst / "phude.ass"
    captions.build_ass(words, [(0.0, tong)], str(p), out_w=out_w, out_h=out_h,
                       font="Montserrat", size=int(out_h * 0.052), ny=0.78,
                       preset="Ô sáng chạy từ (đa màu)")
    return str(p)


def _segs_vua_phim(inf: dict, n_seg: int, do_dai: float) -> list:
    """Mốc cắt PHẢI nằm trong độ dài THẬT của video này. Bản đầu dùng chung 1
    bộ mốc cho mọi làn -> video ngắn (164s) bị guard "mốc ngoài phim" chặn ->
    làn đó ra 0 KB và số đo tải nặng bị hụt 1 làn."""
    dur = max(5.0, float(inf.get("dur") or 0.0))
    moi = do_dai / max(1, n_seg)
    # chừa 2s cuối; nếu phim ngắn thì bóp đoạn lại cho vừa
    kha_dung = max(moi, dur - 2.0)
    buoc = min(moi + 40.0, max(moi, (kha_dung - moi) / max(1, n_seg)))
    goc = min(max(5.0, dur * 0.2), max(0.0, dur - 2.0 - moi * n_seg))
    ra = []
    for i in range(n_seg):
        a = goc + i * buoc
        b = min(a + moi, dur - 0.5)
        if b - a > 1.0:
            ra.append((a, b))
    return ra or [(0.0, min(moi, dur - 0.5))]


def mot_luot(src: str, dst: Path, segs: list, ass: str, lane: int) -> dict:
    """1 lượt xuất THẬT qua export_canvas_clip (tham số y đường sản xuất)."""
    from app.core.ffmpeg_utils import export_canvas_clip
    ra = dst / f"ra_lane{lane}.mp4"
    t0 = time.time()
    loi = ""
    try:
        export_canvas_clip(
            src, str(ra), segs, (0.5, 0.42, 1.0), bg="blur",
            out_w=1080, out_h=1920, ass_path=ass,
            fonts_dir=str(REPO / "app" / "assets" / "fonts"),
            blur_amt=22, fx_fade=True, fx_whoosh=True,
            join_categories=["impact"] * max(0, len(segs) - 1))
    except Exception as e:                                  # noqa: BLE001
        loi = f"{type(e).__name__}: {e}"[:400]
    return {"lane": lane, "giay": round(time.time() - t0, 1),
            "kb": (ra.stat().st_size // 1024) if ra.exists() else 0,
            "loi": loi}


def chay(nhan: str, lanes: int, n_seg: int, do_dai: float,
         video: list[str]) -> dict:
    out = Path(tempfile.mkdtemp(prefix=f"_do_luong_{nhan}_"))
    inf = probe(video[0])
    print(f"  nguồn: {Path(video[0]).name[:60]}")
    print(f"         {inf['w']}x{inf['h']} {inf['fps']:.0f}fps {inf['codec']} "
          f"{inf['dur']:.0f}s tiếng={inf['co_tieng']}")
    # các đoạn: lấy giữa phim, mỗi đoạn do_dai/n_seg giây, KHÔNG liền nhau
    # (đúng cảnh thật: AI chọn 2-3 đoạn rời)
    goc = max(30.0, inf["dur"] * 0.3)
    moi = do_dai / n_seg
    segs = [(goc + i * (moi + 40.0), goc + i * (moi + 40.0) + moi)
            for i in range(n_seg)]
    ass = lam_ass(out, segs, 1080, 1920)
    print(f"  đoạn : {n_seg} đoạn, tổng {do_dai:.0f}s · phụ đề .ass "
          f"{os.path.getsize(ass)//1024} KB")

    td = TheoDoi()
    td.bat_dau()
    t0 = time.time()
    ket: list[dict] = []
    if lanes == 1:
        ket.append(mot_luot(video[0], out, segs, ass, 0))
    else:
        ths = []
        for i in range(lanes):
            v = video[i % len(video)]
            sg = _segs_vua_phim(probe(v), n_seg, do_dai)   # mốc theo TỪNG phim
            th = threading.Thread(
                target=lambda vv=v, ii=i, ss=sg: ket.append(
                    mot_luot(vv, out, ss, ass, ii)))
            ths.append(th)
            th.start()
        for th in ths:
            th.join()
    tong_giay = time.time() - t0
    time.sleep(0.3)
    td.dung()
    bc = td.bao_cao()
    bc.update({"nhan": nhan, "lanes": lanes, "n_seg": n_seg,
               "do_dai": do_dai, "tuong_giay": round(tong_giay, 1),
               "luot": ket, "nhan_hieu": inf})
    try:
        import shutil
        shutil.rmtree(out, ignore_errors=True)
    except OSError:
        pass
    return bc


def in_bao_cao(b: dict) -> None:
    print(f"\n  ── KẾT QUẢ [{b['nhan']}] {b['lanes']} luồng cắt ──")
    print(f"  thời gian tường   : {b['tuong_giay']}s")
    for l in b["luot"]:
        print(f"    lane {l['lane']}: {l['giay']}s · {l['kb']} KB"
              + (f" · LỖI {l['loi']}" if l["loi"] else ""))
    print(f"  LUỒNG ffmpeg đỉnh : {b['luong_dinh']}   (TB {b['luong_tb']:.0f})")
    for k, v in sorted(b["luong_dinh_theo_pha"].items(),
                       key=lambda x: -x[1]):
        print(f"      · {k:<12}: đỉnh {v} luồng "
              f"(1 tiến trình cao nhất {b['luong_dinh_1_proc'].get(k, 0)})")
    print(f"  CPU-giây tổng     : {b['cpu_giay_tong']}s")
    for k, v in sorted(b["cpu_giay_theo_pha"].items(), key=lambda x: -x[1]):
        pc = 100.0 * v / max(0.1, b["cpu_giay_tong"])
        print(f"      · {k:<12}: {v}s ({pc:.0f}%)")
    print(f"  CPU máy           : TB {b['cpu_he_tb']}%  đỉnh {b['cpu_he_dinh']}%")
    print(f"  ĐỘ ĐƠ luồng chính : TB {b.get('tre_tb', 0)}ms · "
          f"p95 {b.get('tre_p95', 0)}ms · đỉnh {b.get('tre_dinh', 0)}ms"
          + ("   ⚠ QUÁ 30ms" if b.get("tre_p95", 0) > 30 else "   (ngân sách 30ms)"))
    print(f"  NVENC (GPU encode): TB {b['nvenc_tb']}%  đỉnh {b['nvenc_dinh']}%")
    ed = b.get("enc_dem", {})
    print(f"  lệnh theo encoder : NVENC {ed.get('h264_nvenc', 0)} · "
          f"libx264 {ed.get('libx264', 0)}"
          + ("   ⚠ CÓ TỤT VỀ CPU" if ed.get("libx264") else "")
          + f"   · giải mã GPU {b.get('n_hwdec', 0)} lệnh")
    print(f"  số tiến trình ffmpeg đã chạy: {b['n_proc']}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nhan", default="goc")
    ap.add_argument("--lanes", type=int, default=1)
    ap.add_argument("--seg", type=int, default=2)
    ap.add_argument("--dai", type=float, default=60.0)
    ap.add_argument("--so", nargs=2, metavar=("A", "B"))
    a = ap.parse_args()

    if a.so:
        for n in a.so:
            f = CACHE / f"{n}.json"
            if not f.exists():
                print(f"THIẾU mốc: {f}")
                return 2
        A = json.loads((CACHE / f"{a.so[0]}.json").read_text("utf-8"))
        B = json.loads((CACHE / f"{a.so[1]}.json").read_text("utf-8"))
        print(f"\n{'chỉ số':<24}{a.so[0]:>14}{a.so[1]:>14}{'đổi':>12}")
        print("-" * 64)
        for k, ten in (("luong_dinh", "luồng đỉnh"),
                       ("luong_tb", "luồng TB"),
                       ("cpu_giay_tong", "CPU-giây"),
                       ("tuong_giay", "giây tường"),
                       ("cpu_he_tb", "CPU máy TB %"),
                       ("nvenc_tb", "NVENC TB %")):
            x, y = float(A.get(k, 0)), float(B.get(k, 0))
            d = (y - x) / x * 100 if x else 0
            print(f"{ten:<24}{x:>14.1f}{y:>14.1f}{d:>11.0f}%")
        return 0

    print("═" * 64)
    print(f"ĐO LUỒNG XUẤT CLIP — nhãn '{a.nhan}' · {a.lanes} luồng cắt · "
          f"{a.seg} đoạn · {a.dai:.0f}s")
    print("═" * 64)
    from config import settings
    from app.core import ffmpeg_utils as fu
    print(f"  ECO_MODE={settings.ECO_MODE} · encoder={fu.detect_encoder()} "
          f"· encode_threads()={fu.encode_threads()} · nhân={os.cpu_count()}")
    vid = chon_video(max(3, a.lanes))
    if not vid:
        print("KHÔNG tìm thấy video thật trong thùng rác.")
        return 2
    idle = psutil.cpu_percent(interval=2.0)
    print(f"  CPU lúc nghỉ: {idle}%  (cần < 15% để số đo sạch)")
    b = chay(a.nhan, a.lanes, a.seg, a.dai, vid)
    in_bao_cao(b)
    (CACHE / f"{a.nhan}.json").write_text(
        json.dumps(b, ensure_ascii=False, indent=1), "utf-8")
    print(f"\n  đã lưu mốc: _do_luong_cache/{a.nhan}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
