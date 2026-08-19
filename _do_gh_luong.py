# -*- coding: utf-8 -*-
"""ĐO: vì sao 2 LUỒNG thay giọng CHẬM HƠN 1 luồng khi bật bộ GIÓNG HÀNG.

Đo ở mức HÀM `giong_hang.giong_hang_loat` (không dựng cả dây chuyền thay
giọng) để loại hết nhiễu Groq/edge-tts/Demucs — câu hỏi là *bộ gióng hàng có
song song được không*, không phải *mạng hôm nay thế nào*.

BA THỨ ĐO, KHÔNG CHỈ THỜI GIAN TƯỜNG:
  · **wall** — thời gian tường (biết nhanh/chậm)
  · **CPU-giây** — phân biệt "xếp hàng" (wall tăng, CPU-giây KHÔNG tăng) với
    "tốn thêm sức" (cả hai cùng tăng). **`GetProcessTimes` trên tiến trình
    CON KHÔNG DÙNG ĐƯỢC trên máy này** — `_do_cpu_probe.py` đốt 1,8 giây CPU
    thuần trong tiến trình con, cả `GetProcessTimes` lẫn
    `psutil.Process.cpu_times()` đều trả **0,000s**. Nên cột CPU lấy theo
    `psutil.cpu_times()` CẢ MÁY rồi **TRỪ NỀN đo ngay trước từng arm**.
  · **VRAM POLL trong lúc chạy** — lấy mẫu trước/sau là đo mức NỀN, vì tiến
    trình thoát là trả sạch VRAM (bẫy đã sập ở cổng 71).

ĐAN XEN CÓ XOAY THỨ TỰ (B,A,A,B): đo liền mạch đã ra kết luận sai 3 lần trên
máy này — lượt đầu nuốt chi phí nạp model.
"""
from __future__ import annotations

import ctypes
import json
import os
import psutil
import statistics
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from ctypes import wintypes
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

HOP = REPO / f"_do_gh_hop_{os.getpid()}"
HOP.mkdir(parents=True, exist_ok=True)
os.environ["BQ_DATA_DIR"] = str(HOP / "data")
os.environ["BQ_DB_PATH"] = str(HOP / "data" / "studio.db")
os.environ["BQ_QSETTINGS_INI"] = str(HOP / "data" / "qs.ini")
(HOP / "data").mkdir(parents=True, exist_ok=True)

from app.core import giong_hang as gh  # noqa: E402
from config import settings  # noqa: E402

_CREATE_NO_WINDOW = 0x08000000


# ======================================================================
# CPU-GIÂY CỦA TIẾN TRÌNH CON — GetProcessTimes
# ======================================================================
class _FILETIME(ctypes.Structure):
    _fields_ = [("lo", wintypes.DWORD), ("hi", wintypes.DWORD)]


_K32 = ctypes.WinDLL("kernel32", use_last_error=True)
_K32.GetProcessTimes.argtypes = [wintypes.HANDLE] + \
    [ctypes.POINTER(_FILETIME)] * 4
_K32.GetProcessTimes.restype = wintypes.BOOL


def cpu_giay(handle) -> float | None:
    """Kernel+User giây của MỘT tiến trình, qua `GetProcessTimes`.

    **TRÊN MÁY NÀY HÀM NÀY TRẢ 0 — ĐÃ TỰ KIỂM, ĐỪNG TIN NÓ.**
    `_do_cpu_probe.py` đốt 1,8 giây CPU thuần trong tiến trình con rồi hỏi
    lại: `GetProcessTimes` **và** `psutil.Process.cpu_times()` đều ra
    **0,000s**, trong khi `psutil.cpu_times()` CẢ MÁY ra 11,8s. Tức môi
    trường không cho đọc số liệu tiến trình con, chứ không phải tiến trình
    con không tốn CPU. Giữ hàm lại để ai chạy trên máy khác còn dùng, nhưng
    bảng số lấy theo `CpuHeThong` bên dưới.
    """
    c, e, k, u = _FILETIME(), _FILETIME(), _FILETIME(), _FILETIME()
    if not _K32.GetProcessTimes(wintypes.HANDLE(int(handle)),
                                ctypes.byref(c), ctypes.byref(e),
                                ctypes.byref(k), ctypes.byref(u)):
        return None
    return (((k.hi << 32) | k.lo) + ((u.hi << 32) | u.lo)) / 1e7


class CpuHeThong:
    """CPU-giây CẢ MÁY tiêu trong một khoảng — thước THAY THẾ đo được thật.

    Không phân biệt được tiến trình nào tiêu, nên phải trừ NỀN (đo ngay
    trước lượt chạy) thì con số mới nói lên "lượt đo này tốn thêm bao nhiêu
    sức", tức mới phân biệt được XẾP HÀNG với TỐN THÊM SỨC.
    """

    @staticmethod
    def moc() -> float:
        t = psutil.cpu_times()
        return float(t.user + t.system)

    @staticmethod
    def do_nen(giay: float = 2.0) -> float:
        """CPU-giây/giây của máy lúc KHÔNG chạy phép đo."""
        a = CpuHeThong.moc()
        time.sleep(giay)
        return (CpuHeThong.moc() - a) / giay


_PROCS: list = []
_PROC_LOCK = threading.Lock()
_POPEN_THAT = subprocess.Popen


class _PopenGhiSo(_POPEN_THAT):            # type: ignore[misc,valid-type]
    """CHỈ ghi sổ tiến trình CỦA BỘ GIÓNG HÀNG.

    **BẪY ĐÃ SẬP 1 LẦN, ĐỪNG GỠ BỘ LỌC NÀY:** bản đầu ghi sổ MỌI `Popen`, mà
    chính vòng poll VRAM gọi `nvidia-smi` qua `subprocess.run` (= `Popen`) —
    arm chạy LÂU thì poll NHIỀU LẦN HƠN, nên cột "CPU-giây" hoá ra đo
    `nvidia-smi`. Đo ra 38 tiến trình (2 luồng) vs 68 (lần lượt) cho cùng
    2 lượt gióng hàng, và cột CPU vì thế tự sinh ra tỉ lệ 1,68x KHÔNG CÓ
    THẬT. Cùng họ "phép đo hỏng phát chứng nhận".
    """

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.bq_gh = False
        self.bq_cpu: float | None = None
        try:
            lenh = a[0] if a else kw.get("args")
            self.bq_gh = any("_bq_giong_runner" in str(x)
                             for x in (lenh or []))
        except Exception:                              # noqa: BLE001
            pass
        if self.bq_gh:
            with _PROC_LOCK:
                _PROCS.append(self)

    def wait(self, timeout=None):
        rc = super().wait(timeout=timeout)
        # ĐỌC CPU NGAY TẠI ĐÂY: `giong_hang_loat` trả về xong là `Popen` mất
        # tham chiếu cuối, handle đóng, `GetProcessTimes` trả 0 IM LẶNG.
        if self.bq_gh and self.bq_cpu is None:
            self.bq_cpu = cpu_giay(self._handle)       # noqa: SLF001
        return rc


# ======================================================================
# VRAM — POLL trong lúc chạy
# ======================================================================
class DoVram:
    def __init__(self, nhip: float = 0.20):
        self.nhip = nhip
        self.mau: list[int] = []
        self._chay = False
        self._t: threading.Thread | None = None

    @staticmethod
    def _doc() -> int | None:
        try:
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
                creationflags=_CREATE_NO_WINDOW)
            return int((r.stdout or "0").strip().splitlines()[0])
        except Exception:                              # noqa: BLE001
            return None

    def _vong(self):
        while self._chay:
            v = self._doc()
            if v is not None:
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
            self._t.join(timeout=2)

    @property
    def dinh(self) -> int:
        return max(self.mau) if self.mau else -1


# ======================================================================
# CORPUS — cắt tiếng THẬT ra WAV
# ======================================================================
NGUON = Path(r"C:\Users\Admin\Downloads\longtieng")


def _tim_nguon() -> Path:
    for p in sorted(NGUON.glob("*.mp4")):
        return p
    raise SystemExit("Không tìm thấy video nguồn ở " + str(NGUON))


CHU = [
    "chuong trinh hom nay se gioi thieu voi cac ban mot bo phim rat hay",
    "nhan vat chinh la mot nguoi dan ong tre tuoi song o thanh pho lon",
    "anh ta phat hien ra mot bi mat dong troi ve cong ty minh dang lam",
    "cau chuyen bat dau tro nen cang thang khi canh sat vao cuoc dieu tra",
    "khan gia se khong the roi mat khoi man hinh trong suot hai tieng dong ho",
    "day la mot tac pham dang xem neu ban thich the loai tam ly hinh su",
]


def lam_wav(thu_muc: Path, so: int, dai: float = 4.0) -> list[str]:
    thu_muc.mkdir(parents=True, exist_ok=True)
    src = _tim_nguon()
    ra = []
    for i in range(so):
        p = thu_muc / f"c{i}.wav"
        if not p.is_file():
            subprocess.run(
                [settings.FFMPEG_PATH, "-v", "error", "-y",
                 "-ss", str(20 + i * 6), "-t", str(dai), "-i", str(src),
                 "-vn", "-ac", "1", "-ar", "16000", str(p)],
                capture_output=True, timeout=120,
                creationflags=_CREATE_NO_WINDOW)
        ra.append(str(p))
    return ra


# ======================================================================
# ARM
# ======================================================================
def _goi(wavs, texts, tag, ket):
    tt: dict = {}
    t0 = time.time()
    moc = gh.giong_hang_loat(wavs, texts, "vi", thong_tin=tt)
    ket[tag] = {"giay": round(time.time() - t0, 2),
                "co_moc": sum(1 for m in moc if m),
                "n": len(moc),
                "thiet_bi": tt.get("thiet_bi"),
                "giay_align": tt.get("giay_align"),
                "giay_con": tt.get("giay")}
    return moc


def arm(che_do: str, bo: list[tuple[list, list]]) -> dict:
    """che_do='tuan_tu' (lần lượt) hoặc 'song_song' (2 luồng cùng lúc)."""
    with _PROC_LOCK:
        _PROCS.clear()
    ket: dict = {}
    nen = CpuHeThong.do_nen(2.0)        # nền NGAY TRƯỚC arm này
    cpu0 = CpuHeThong.moc()
    with DoVram() as vr:
        t0 = time.time()
        if che_do == "tuan_tu":
            for i, (w, t) in enumerate(bo):
                _goi(w, t, f"m{i}", ket)
        else:
            with ThreadPoolExecutor(max_workers=len(bo)) as ex:
                fs = [ex.submit(_goi, w, t, f"m{i}", ket)
                      for i, (w, t) in enumerate(bo)]
                for f in fs:
                    f.result()
        wall = time.time() - t0
    cpu_tho = CpuHeThong.moc() - cpu0
    cpu = cpu_tho - nen * wall            # TRỪ NỀN, không thì đo cả máy
    with _PROC_LOCK:
        procs = list(_PROCS)
    return {"che_do": che_do, "wall": round(wall, 2),
            "cpu_con": round(cpu, 2), "cpu_tho": round(cpu_tho, 2),
            "cpu_nen": round(nen, 2), "so_tien_trinh": len(procs),
            "vram_dinh": vr.dinh, "vram_mau": len(vr.mau),
            "moi_me": ket}


# ======================================================================
def main() -> int:
    vong = int(os.environ.get("BQ_VONG") or 2)
    so_cau = int(os.environ.get("BQ_SO_CAU") or 6)
    print(f"REPO {REPO}")
    print(f"VRAM nền: {DoVram._doc()} MiB · corpus {so_cau} câu/mẻ · "
          f"{vong} vòng ĐAN XEN")

    w1 = lam_wav(HOP / "w1", so_cau)
    w2 = lam_wav(HOP / "w2", so_cau)
    bo = [(w1, CHU[:so_cau]), (w2, CHU[:so_cau])]

    subprocess.Popen = _PopenGhiSo                    # type: ignore[misc]
    try:
        print("\n--- LƯỢT MỒI (nuốt chi phí lần đầu, KHÔNG tính) ---")
        r = arm("tuan_tu", [bo[0]])
        print(f"  mồi: wall {r['wall']}s · cpu_con {r['cpu_con']}s · "
              f"thiết bị {r['moi_me']['m0']['thiet_bi']}")

        do: list[dict] = []
        for v in range(vong):
            thu_tu = ["song_song", "tuan_tu"] if v % 2 == 0 \
                else ["tuan_tu", "song_song"]
            for cd in thu_tu:
                r = arm(cd, bo)
                r["vong"] = v
                do.append(r)
                me = r["moi_me"]
                print(f"  v{v} {cd:9s}: wall {r['wall']:6.2f}s · "
                      f"CPU-con {r['cpu_con']:7.2f}s · "
                      f"VRAM đỉnh {r['vram_dinh']:5d} MiB · "
                      f"mốc {[me[k]['co_moc'] for k in sorted(me)]}"
                      f"/{[me[k]['n'] for k in sorted(me)]} · "
                      f"align {[me[k]['giay_align'] for k in sorted(me)]}")
    finally:
        subprocess.Popen = _POPEN_THAT                # type: ignore[misc]

    def _lay(cd, khoa):
        return [x[khoa] for x in do if x["che_do"] == cd]

    print("\n" + "=" * 66)
    print("BẢNG — lần lượt vs 2 luồng (trung vị, đo đan xen, máy rảnh)")
    print("=" * 66)
    print(f"{'':22s}{'lần lượt':>14s}{'2 luồng':>14s}{'tỉ lệ':>12s}")
    for khoa, nhan in (("wall", "thời gian tường (s)"),
                       ("cpu_con", "CPU-giây (trừ nền)"),
                       ("vram_dinh", "VRAM đỉnh (MiB)")):
        a = statistics.median(_lay("tuan_tu", khoa))
        b = statistics.median(_lay("song_song", khoa))
        ti = a / b if b else 0
        print(f"{nhan:22s}{a:14.2f}{b:14.2f}{ti:11.2f}x")
    print(f"\n  lần lượt mỗi lượt: {_lay('tuan_tu', 'wall')}")
    print(f"  2 luồng  mỗi lượt: {_lay('song_song', 'wall')}")

    # SỐ MỐC — nếu 2 luồng trả về ÍT mốc hơn thì không phải chuyện tốc độ
    def _moc(cd):
        ra = []
        for x in do:
            if x["che_do"] != cd:
                continue
            ra.append(sum(m["co_moc"] for m in x["moi_me"].values()))
        return ra
    print(f"\n  SỐ CÂU CÓ MỐC — lần lượt {_moc('tuan_tu')} · "
          f"2 luồng {_moc('song_song')}  (mỗi lượt tối đa {so_cau * 2})")

    (HOP / "ket.json").write_text(
        json.dumps(do, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nSố thô: {HOP / 'ket.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
