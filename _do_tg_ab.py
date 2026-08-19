# -*- coding: utf-8 -*-
"""ĐO A/B ĐƯỜNG THAY GIỌNG THẬT: 1 luồng vs 2 luồng, BẬT/TẮT bộ gióng hàng.

Dựng lại ĐÚNG arm A/B của cổng 55 (`_test_thay_giong_ui.py` CA 2) nhưng thêm
BA thứ cổng không có:

  · **ĐẾM + BẤM GIỜ TỪNG LƯỢT `giong_hang_loat`** (bọc hàm, không sửa mã app)
    -> trả lời được câu *"gióng hàng có nằm trên đường chạy không, và mỗi
    lượt tốn bao nhiêu"*, thay vì suy từ việc tắt nó đi thì nhanh hơn.
  · **CPU-giây của TIẾN TRÌNH CON** (`GetProcessTimes` trên handle `Popen`)
    -> phân biệt XẾP HÀNG với TỐN THÊM SỨC.
  · **VRAM POLL trong lúc chạy** -> lấy mẫu trước/sau là đo mức NỀN (bẫy cổng
    71: tiến trình thoát là trả sạch VRAM).

ĐAN XEN CÓ XOAY THỨ TỰ. Đo liền mạch đã ra kết luận sai 3 lần trên máy này.
"""
from __future__ import annotations

import ctypes
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from ctypes import wintypes
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = str(Path(__file__).resolve().parent)
sys.path.insert(0, REPO)

T = Path(tempfile.mkdtemp(prefix="tgab_"))
RAC = Path(REPO) / f"bq_do_tgrac_{os.getpid()}"
RAC.mkdir(parents=True, exist_ok=True)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DATA_DIR"] = str(T)
os.environ["BQ_DB_PATH"] = str(T / "studio.db")
os.environ["BQ_QSETTINGS_INI"] = str(T / "settings.ini")
os.environ["BQ_FFMPEG_SLOTS"] = "1"
os.environ["WHISPER_PROVIDER"] = "groq"

_ENV_THAT = (Path(os.environ.get("LOCALAPPDATA") or Path.home())
             / "BQHungVideo" / ".env")
if _ENV_THAT.exists():
    for _ln in _ENV_THAT.read_text(encoding="utf-8",
                                   errors="replace").splitlines():
        _k, _, _v = _ln.partition("=")
        _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
        if _k in ("GROQ_API_KEYS", "GROQ_KEYS_FILE") and _v:
            os.environ.setdefault(_k, _v)

import _test_guard  # noqa: E402,F401
import app.queue.jobs as _JOBS  # noqa: E402,F401
from app.database import db  # noqa: E402
from app.queue.worker import WorkerPool  # noqa: E402
from config import settings  # noqa: E402
from app.core import thay_giong as TG  # noqa: E402
from app.core import giong_hang as GH  # noqa: E402

from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

QMessageBox.exec = lambda self: 0                       # type: ignore
QMessageBox.warning = staticmethod(lambda *a, **k: 0)   # type: ignore
QMessageBox.information = staticmethod(lambda *a, **k: 0)  # type: ignore
QMessageBox.critical = staticmethod(lambda *a, **k: 0)  # type: ignore
QMessageBox.question = staticmethod(
    lambda *a, **k: QMessageBox.StandardButton.No)       # type: ignore

_app = QApplication.instance() or QApplication([])
from app.ui.thay_giong_dialog import ThayGiongDialog  # noqa: E402

_CREATE_NO_WINDOW = 0x08000000


# ======================================================================
# CPU-GIÂY TIẾN TRÌNH CON
# ======================================================================
class _FILETIME(ctypes.Structure):
    _fields_ = [("lo", wintypes.DWORD), ("hi", wintypes.DWORD)]


def cpu_giay(handle) -> float:
    c, e, k, u = _FILETIME(), _FILETIME(), _FILETIME(), _FILETIME()
    if not ctypes.windll.kernel32.GetProcessTimes(
            int(handle), ctypes.byref(c), ctypes.byref(e),
            ctypes.byref(k), ctypes.byref(u)):
        return 0.0
    return (((k.hi << 32) | k.lo) + ((u.hi << 32) | u.lo)) / 1e7


_PROCS: list = []
_PLOCK = threading.Lock()
_POPEN_THAT = subprocess.Popen


class _PopenGhi(_POPEN_THAT):               # type: ignore[misc,valid-type]
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        with _PLOCK:
            _PROCS.append(self)


subprocess.Popen = _PopenGhi                # type: ignore[misc]


# ======================================================================
# BỌC giong_hang_loat — ĐẾM + BẤM GIỜ, KHÔNG SỬA MÃ APP
# ======================================================================
_GH_LOG: list = []
_GH_THAT = GH.giong_hang_loat


def _gh_boc(wavs, texts, lang="", **kw):
    t0 = time.time()
    tt: dict = kw.pop("thong_tin", None) or {}
    ra = _GH_THAT(wavs, texts, lang, thong_tin=tt, **kw)
    _GH_LOG.append({"t": round(time.time() - t0, 2), "n": len(wavs),
                    "co_moc": sum(1 for m in ra if m),
                    "thiet_bi": tt.get("thiet_bi"),
                    "align": tt.get("giay_align"),
                    "luong": threading.current_thread().name})
    return ra


GH.giong_hang_loat = _gh_boc                # type: ignore[assignment]
# `dubbing` import module rồi gọi `gh.giong_hang_loat` -> bọc ở module là đủ.


# ======================================================================
# VRAM
# ======================================================================
class DoVram:
    def __init__(self, nhip: float = 0.25):
        self.nhip, self.mau, self._chay = nhip, [], False
        self._t = None

    @staticmethod
    def doc() -> int:
        try:
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used",
                 "--format=csv,noheader,nounits"], capture_output=True,
                text=True, timeout=5, creationflags=_CREATE_NO_WINDOW)
            return int((r.stdout or "0").strip().splitlines()[0])
        except Exception:                              # noqa: BLE001
            return -1

    def _vong(self):
        while self._chay:
            v = self.doc()
            if v >= 0:
                self.mau.append(v)
            time.sleep(self.nhip)

    def __enter__(self):
        self._chay = True
        self._t = threading.Thread(target=self._vong, daemon=True)
        self._t.start()
        return self

    def __exit__(self, *a):
        self._chay = False
        if self._t:
            self._t.join(timeout=3)

    @property
    def dinh(self) -> int:
        return max(self.mau) if self.mau else -1


# ======================================================================
# NGUỒN — y hệt cổng 55
# ======================================================================
LOI = ("Chào mọi người, hôm nay chúng ta thử một thứ rất hay. "
       "Anh ấy mở cánh cửa ra, và điều bất ngờ đã xảy ra ngay lúc đó.")


def ff(args):
    return subprocess.run([settings.FFMPEG_PATH, "-y", "-hide_banner",
                           "-loglevel", "error", *args],
                          capture_output=True, text=True).returncode


def dung_nguon() -> Path:
    import asyncio
    from app.core import dubbing
    sp = T / "loi.mp3"
    ok = asyncio.run(dubbing._synth_all([LOI], "vi-VN-HoaiMyNeural",
                                        [str(sp)]))
    if not ok[0]:
        raise SystemExit("edge-tts không đọc được câu nguồn")
    d = TG.probe_duration(sp)
    dst = T / "mau.mp4"
    fc = ("[1:a][2:a]join=inputs=2:channel_layout=stereo,"
          "volume=-12dB[bed];[0:a]aformat=channel_layouts=stereo[sp];"
          "[bed][sp]amix=inputs=2:duration=first:normalize=0[a]")
    ff(["-i", str(sp),
        "-f", "lavfi", "-i", f"sine=frequency=196:duration={d:.2f}",
        "-f", "lavfi", "-i", f"sine=frequency=294:duration={d:.2f}",
        "-f", "lavfi", "-i", f"testsrc2=size=320x240:rate=25:duration={d:.2f}",
        "-filter_complex", fc, "-map", "3:v", "-map", "[a]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
        "-b:a", "128k", "-ar", "44100", "-ac", "2", "-t", f"{d:.2f}",
        str(dst)])
    return dst


MAU = dung_nguon()
print(f"video mẫu {TG.probe_duration(MAU):.2f}s")


def thu_muc_video(ten: str, n: int) -> Path:
    d = T / ten
    d.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        shutil.copy2(MAU, d / f"video_{i + 1}.mp4")
    return d


def cho_xong(pool, ids, han=900.0) -> dict:
    t0, dinh = time.time(), 0
    while time.time() - t0 < han:
        _app.processEvents()
        dinh = max(dinh, pool._dem_lan()[2])
        rows = db.query("SELECT status FROM jobs WHERE id IN ({})".format(
            ",".join("?" * len(ids))), tuple(ids))
        tt = [str(r["status"]) for r in rows]
        if tt and all(s in ("done", "failed", "canceled") for s in tt):
            break
        time.sleep(0.25)
    return {"giay": round(time.time() - t0, 2), "dinh": dinh,
            "trang_thai": tt}


# ======================================================================
POOL = WorkerPool({}, max_cpu=1, max_gpu=1, max_tg=2)
POOL.start()
_dem = [0]


def arm(luong: int, gh_bat: bool) -> dict:
    _dem[0] += 1
    ten = f"a{_dem[0]}_l{luong}_{'gh' if gh_bat else 'nogh'}"
    os.environ["BQ_GIONG_HANG"] = "1" if gh_bat else "0"
    db.execute("DELETE FROM jobs")
    _GH_LOG.clear()
    with _PLOCK:
        _PROCS.clear()
    d = thu_muc_video(ten, 2)
    POOL.set_limits(max_tg=luong)
    dl = ThayGiongDialog(POOL, None, thung_rac=str(RAC / ("R_" + ten)))
    dl.ed_thu_muc.setText(str(d))
    dl.ed_thu_muc_ra.setText(str(T / (ten + "_ra")))
    dl.cb_nn.setCurrentIndex(dl.cb_nn.findData("en"))
    dl.sp_luong.setValue(luong)
    with DoVram() as vr:
        dl._chay()
        r = cho_xong(POOL, list(dl._jobs.values()))
    dl.close()
    with _PLOCK:
        procs = list(_PROCS)
    cpu = sum(cpu_giay(p._handle) for p in procs)      # noqa: SLF001
    gh_l = list(_GH_LOG)
    ra = {"luong": luong, "gh": gh_bat, "giay": r["giay"], "dinh": r["dinh"],
          "trang_thai": r["trang_thai"], "cpu_con": round(cpu, 1),
          "so_proc": len(procs), "vram_dinh": vr.dinh,
          "gh_so_luot": len(gh_l),
          "gh_tong_giay": round(sum(x["t"] for x in gh_l), 2),
          "gh_hong": sum(1 for x in gh_l if x["co_moc"] == 0),
          "gh_chi_tiet": gh_l}
    print(f"  {ten:22s} wall {r['giay']:6.2f}s · CPU-con {cpu:7.1f}s · "
          f"VRAM {vr.dinh:5d} · đỉnh song song {r['dinh']} · "
          f"GH {len(gh_l)} lượt/{ra['gh_tong_giay']}s "
          f"(hỏng {ra['gh_hong']}) · {r['trang_thai']}")
    return ra


def main() -> int:
    print(f"VRAM nền {DoVram.doc()} MiB · gióng hàng có={GH.co_giong_hang()}")
    do: list[dict] = []
    print("\n--- BẬT gióng hàng · ĐAN XEN B,A,A,B ---")
    for luong in (2, 1, 1, 2):
        do.append(arm(luong, True))
    print("\n--- TẮT gióng hàng (BQ_GIONG_HANG=0) · ĐAN XEN B,A,A,B ---")
    for luong in (2, 1, 1, 2):
        do.append(arm(luong, False))
    os.environ["BQ_GIONG_HANG"] = "1"

    def _l(gh, luong, k="giay"):
        return [x[k] for x in do if x["gh"] == gh and x["luong"] == luong]

    print("\n" + "=" * 70)
    print("BẢNG — thời gian tường (s), 2 video mỗi arm")
    print("=" * 70)
    for gh, nhan in ((True, "BẬT gióng hàng"), (False, "TẮT gióng hàng")):
        a, b = _l(gh, 1), _l(gh, 2)
        ma, mb = statistics.median(a), statistics.median(b)
        print(f"{nhan:18s} 1 luồng {a} (tv {ma:.2f})  ·  "
              f"2 luồng {b} (tv {mb:.2f})  ->  {ma / mb:.2f}x")
        ca, cb = _l(gh, 1, "cpu_con"), _l(gh, 2, "cpu_con")
        print(f"{'':18s} CPU-giây con: 1 luồng tv {statistics.median(ca):.1f}s"
              f" · 2 luồng tv {statistics.median(cb):.1f}s")
        va, vb = _l(gh, 1, "vram_dinh"), _l(gh, 2, "vram_dinh")
        print(f"{'':18s} VRAM đỉnh: 1 luồng {max(va)} MiB · "
              f"2 luồng {max(vb)} MiB")
        ga, gb = _l(gh, 1, "gh_so_luot"), _l(gh, 2, "gh_so_luot")
        ha, hb = _l(gh, 1, "gh_hong"), _l(gh, 2, "gh_hong")
        print(f"{'':18s} gióng hàng: 1 luồng {ga} lượt/{ha} hỏng · "
              f"2 luồng {gb} lượt/{hb} hỏng")

    Path(REPO, "_do_tg_ab_ket.json").write_text(
        json.dumps(do, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nSố thô: _do_tg_ab_ket.json")
    return 0


try:
    raise SystemExit(main())
finally:
    try:
        POOL.stop(wait=False)
    except Exception:                                  # noqa: BLE001
        pass
    subprocess.Popen = _POPEN_THAT                     # type: ignore[misc]
    shutil.rmtree(T, ignore_errors=True)
    shutil.rmtree(RAC, ignore_errors=True)
