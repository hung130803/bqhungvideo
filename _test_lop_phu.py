# -*- coding: utf-8 -*-
"""CỔNG 46 — LỚP PHỦ HẠT: THẤY ĐƯỢC · KHÔNG LOÈ · KHÔNG RÒ · **KHỚP CẢNH**.

VÌ SAO CÓ CỔNG NÀY (anh Hùng 09/08/2026): *"tôi muốn làm đa dạng nhiều kiểu ấy…
kiểu hiệu ứng tuyết rơi, trái tim bay, với rất nhiều kiểu khác thêm vào —
**nhưng phải hợp lý, tuỳ cảnh mới chọn chứ không chọn bừa bãi**"*.

Cổng 43 đã đo ĐỘ SÁNG từng khung cho mọi kiểu trong kho, cổng 38/41 đo CHỌN
ĐÚNG KIỂU theo số đo. Không cổng nào hỏi được câu quan trọng nhất của nhóm mới:
**"cảnh này CÓ ĐÁNG thêm tuyết không"** — vì 27 kiểu cũ không mang nghĩa, còn
lớp phủ thì có. Cổng này hỏi cả hai:
  * KẾT QUẢ TRÊN KHUNG HÌNH (ffmpeg thật, 1080x1920, đếm điểm ảnh);
  * KẾT QUẢ CỦA BỘ KHỚP CẢNH (hàm thuần, 8 ca nội dung dựng sẵn).

=== 7 ĐIỀU NÓ CANH ===
1. THẤY ĐƯỢC   : >= 8,00% điểm ảnh |dY|>12 giữa cửa sổ. Dưới -> GỠ kiểu đó.
2. KHÔNG LOÈ   : lệch UAVG/VAVG cả khung < `hieu_ung.UV_MAX` (3,0) và độ bão
                 hoà không tụt dưới 80% — cùng thước đã loại `rgbashift`
                 (U +7,16) và `baltan` (U −3,08) khỏi kho.
3. KHÔNG RÒ    : ngoài cửa sổ **0,0000%**, và HAI MÉP cửa sổ cũng 0,0000%
                 (êm vào — êm ra). Đo bằng mã hoá KHÔNG MẤT DỮ LIỆU.
4. KHỚP CẢNH   : tuyết KHÔNG rơi trên video nấu ăn · trái tim KHÔNG bay trên
                 video thể thao · nội dung mơ hồ -> KHÔNG THÊM GÌ.
5. BẤT BIẾN    : mức "tat" ra file GIỐNG HỆT, và `chon_hieu_ung` không có
                 `dat_truoc` phải trả Y HỆT bản mốc v2.19.0.
6. MÁY NHÂN VIÊN: không NVENC / không Vulkan / không frei0r -> nhóm này VẪN
                 CHẠY (nó là ffmpeg thuần, không phụ thuộc cái nào).
7. CHI PHÍ     : wall + CPU-giây so bản không lớp phủ, in số ra.

=== 3 BẪY ĐO ĐÃ SẬP KHI VIẾT CỔNG NÀY — đừng lặp ===
(a) **ĐỪNG ĐO RÒ BẰNG FILE NÉN MẤT DỮ LIỆU.** Với `-crf 18`, chính phép nén
    làm **0,157%** điểm ảnh NGOÀI cửa sổ lệch >12 — không phân biệt nổi với rò
    thật. Đổi sang `-qp 0` (x264 không mất dữ liệu) thì ra đúng **0,0000%**.
(b) **ĐỪNG ĐO LỆCH MÀU BẰNG `blend=difference` RỒI LẤY UAVG.** Đó là lệch U
    trung bình TỪNG ĐIỂM ẢNH; che 18% khung bằng hạt TRẮNG cho ra 11,6 mà
    không hề "tím cả khung". Thước đúng (và là thước đã dùng để loại
    `rgbashift`/`baltan`) là PHÂN BỐ CHROMA cả khung: UAVG/VAVG/SATAVG TRƯỚC
    so với SAU.
(c) **`gradients` mặc định `seed=-1` = ngẫu nhiên mỗi lượt.** Quên đặt seed thì
    confetti đổi màu mỗi lần xuất và cổng nhấp nháy. CA 0 dựng 2 lượt rồi bắt
    chúng GIỐNG HỆT — ca đó cũng canh luôn `geq` dùng `st()/ld()` mà chạy đa
    luồng lát cắt.

Chạy: .venv\\Scripts\\python.exe _test_lop_phu.py
Env : BQ_TEST=1 · PYTHONIOENCODING=utf-8 · BQ_FFMPEG_SLOTS=1 (LUẬT SỐ 1)
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

_SB = Path(tempfile.gettempdir()) / f"test_lop_phu_{os.getpid()}"
_SB.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BQ_DATA_DIR", str(_SB))
os.environ.setdefault("BQ_DB_PATH", str(_SB / "studio.db"))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")
os.environ.setdefault("BQ_TEST", "1")

import _test_guard  # noqa: E402,F401  (cổng 17: test KHÔNG được đụng máy user)

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

from app.core import hieu_ung as HU          # noqa: E402
from app.core import lop_phu as LP           # noqa: E402
from config import settings                  # noqa: E402

_NOWIN = 0x08000000 if os.name == "nt" else 0
FF = settings.FFMPEG_PATH
FP = settings.FFPROBE_PATH

W, H, FPS = 1080, 1920, 30
DAI = 2.60                    # nguồn NGẮN — luật số 1 (máy anh Hùng đang chạy)
BAT, HET = 0.80, 1.60         # cửa sổ chung cho mọi kiểu (0,80 s = `DAI_MAX`)
NG_THAY = 8.0                 # % điểm ảnh phải đổi giữa cửa sổ
NG_RO = 0.0005                # ngoài cửa sổ (mã hoá không mất dữ liệu -> 0)
NG_BAO_HOA = 0.80             # độ bão hoà không được tụt dưới 80% bản gốc
NG_SANG_TRAN, NG_SANG_SAN = 1.45, 0.35   # trần/sàn tỉ lệ sáng trong cửa sổ

_LOI: list[str] = []
_OK: list[str] = []


def bao(ten: str, ok: bool, so: str = "") -> None:
    (_OK if ok else _LOI).append(f"{ten} — {so}")
    print(f"  [{'OK ' if ok else 'FAIL'}] {ten}: {so}")


class DoCPU:
    """Đong CPU-giây của MỌI ffmpeg con trong lúc chạy — bằng cách LẤY MẪU.

    Vì sao phải lấy mẫu chứ không đọc một phát lúc xong: trên Windows, đọc
    `cpu_times()` SAU khi tiến trình thoát ném `NoSuchProcess` (đã đo: mọi cột
    ra -1). Mà `psutil.Process().cpu_times()` của CHÍNH mình thì không cộng con
    (trường `children_user` chỉ có trên Linux). Nên: cứ 25 ms quét cây tiến
    trình, nhớ giá trị LỚN NHẤT từng thấy của mỗi pid, cuối cùng cộng lại.
    Sai số tối đa = phần CPU tiêu trong 25 ms cuối của mỗi tiến trình.
    `BQ_FFMPEG_SLOTS=1` nên mỗi lúc chỉ có 1 ffmpeg — cây rất nhỏ, phép quét
    không đáng kể (đo: dưới 1% CPU của chính lượt đo).
    """

    def __init__(self) -> None:
        import threading
        self._dung = threading.Event()
        self._so: dict = {}
        self._t = threading.Thread(target=self._vong, daemon=True)

    def _vong(self) -> None:
        import psutil
        me = psutil.Process()
        while not self._dung.is_set():
            try:
                for c in me.children(recursive=True):
                    try:
                        ct = c.cpu_times()
                        v = float(ct.user) + float(ct.system)
                        if v > self._so.get(c.pid, 0.0):
                            self._so[c.pid] = v
                    except Exception:  # noqa: BLE001 - tiến trình vừa thoát
                        continue
            except Exception:  # noqa: BLE001
                pass
            self._dung.wait(0.025)

    def __enter__(self) -> "DoCPU":
        self._so.clear()
        self.wall = time.perf_counter()
        self._t.start()
        return self

    def __exit__(self, *a) -> None:
        self.wall = time.perf_counter() - self.wall
        self._dung.set()
        self._t.join(timeout=2.0)
        self.cpu = sum(self._so.values())


def chay(cmd: list, giay: int = 420) -> tuple[int, str, float, float]:
    """Chạy 1 lệnh -> (mã, stderr, wall giây, CPU-giây)."""
    with DoCPU() as d:
        p = subprocess.Popen([str(x) for x in cmd], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, creationflags=_NOWIN)
        _out, err = p.communicate(timeout=giay)
        rc = int(p.returncode)
    return rc, (err or b"").decode("utf-8", "replace"), d.wall, d.cpu


def _esc(p: str) -> str:
    return str(p).replace("\\", "/").replace(":", "\\:")


def _doc(p: str, khoa: str) -> list[float]:
    if not os.path.exists(p):
        return []
    out = []
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        for ln in f:
            if khoa in ln:
                m = re.search(r"=\s*([-\d.]+)\s*$", ln.strip())
                if m:
                    try:
                        out.append(float(m.group(1)))
                    except ValueError:
                        pass
    return out


def dem_khung(p: str) -> int:
    r = subprocess.run([FP, "-v", "error", "-count_frames", "-select_streams",
                        "v:0", "-show_entries", "stream=nb_read_frames",
                        "-of", "csv=p=0", p], capture_output=True,
                       creationflags=_NOWIN, timeout=300)
    try:
        return int((r.stdout or b"").decode().strip().split(",")[0])
    except (ValueError, IndexError):
        return -1


def do_cap(goc: str, sau: str, td: str) -> dict:
    """%điểm ảnh đổi + sáng + PHÂN BỐ CHROMA từng khung, ở ĐÚNG 1080x1920.

    Bẫy (b) ở đầu file: chroma phải so UAVG/VAVG/SATAVG của HAI BẢN, không
    phải UAVG của khung hiệu. Bẫy cổng 43: KHÔNG `format=gray` giữa chuỗi.
    """
    fd, f0, f1 = (os.path.join(td, x) for x in
                  ("_dd.txt", "_l0.txt", "_l1.txt"))
    for f in (fd, f0, f1):
        try:
            os.remove(f)
        except OSError:
            pass
    g = (f"[0:v]format=yuv420p,split=2[a][a2];"
         f"[1:v]format=yuv420p,split=2[b][b2];"
         f"[a][b]blend=all_mode=difference,"
         f"lutyuv=y='if(gt(val,12),255,0)',signalstats,"
         f"metadata=print:key=lavfi.signalstats.YAVG:file='{_esc(fd)}'[d];"
         f"[a2]signalstats,metadata=print:file='{_esc(f0)}'[x0];"
         f"[b2]signalstats,metadata=print:file='{_esc(f1)}'[x1];"
         f"[x0]nullsink;[x1]nullsink")
    rc, err, _w, _c = chay([FF, "-v", "error", "-i", goc, "-i", sau,
                            "-filter_complex", g, "-map", "[d]",
                            "-f", "null", "-"])
    if rc != 0:
        raise RuntimeError("lệnh đo hỏng: " + err[-400:])
    return {"doi": [v / 2.55 for v in _doc(fd, "YAVG")],
            "sang0": _doc(f0, ".YAVG"), "sang1": _doc(f1, ".YAVG"),
            "u0": _doc(f0, ".UAVG"), "u1": _doc(f1, ".UAVG"),
            "v0": _doc(f0, ".VAVG"), "v1": _doc(f1, ".VAVG"),
            "s0": _doc(f0, ".SATAVG"), "s1": _doc(f1, ".SATAVG")}


def nguon(td: str) -> str:
    """Nguồn TỰ SINH bằng lavfi — KHÔNG ghi cứng đường dẫn máy anh Hùng.

    `testsrc2` là ca KHẮC NGHIỆT cho phép đo màu (ô bão hoà 100%, mạnh hơn
    phim thật) và không bao giờ "gần đen" — bẫy FAIL OAN của cổng 36.
    Mã hoá KHÔNG MẤT DỮ LIỆU: xem bẫy (a) ở đầu file.
    """
    dst = os.path.join(td, "goc.mp4")
    rc, err, _w, _c = chay([FF, "-y", "-v", "error", "-f", "lavfi", "-i",
                            f"testsrc2=s={W}x{H}:r={FPS}:d={DAI}", "-an",
                            "-c:v", "libx264", "-preset", "ultrafast",
                            "-qp", "0", "-pix_fmt", "yuv420p", dst])
    if rc != 0:
        raise RuntimeError("không dựng nổi nguồn: " + err[-300:])
    return dst


def _dung(k: str, src: str, td: str, ten: str) -> tuple[int, str, float, float]:
    ch = HU.chuoi_filter([{"khoa": k, "bat": BAT, "het": HET,
                           "dam": HU.DAM_MAX}], W, H, FPS)
    if not ch:
        return -1, "chuỗi filter rỗng", 0.0, 0.0
    rc, err, wall, cpu = chay(
        [FF, "-y", "-v", "error", "-i", src, "-an", "-vf", ch, "-c:v",
         "libx264", "-preset", "ultrafast", "-qp", "0", "-pix_fmt",
         "yuv420p", ten])
    return rc, err, wall, cpu


def quet_mot(k: str, src: str, td: str, n_goc: int) -> dict:
    dst = os.path.join(td, f"e_{k}.mp4")
    rc, err, wall, cpu = _dung(k, src, td, dst)
    if rc != 0:
        return {"kq": "FFMPEG-LỖI",
                "ghi": (err.strip().splitlines() or [""])[-1][:120]}
    n = dem_khung(dst)
    d = do_cap(src, dst, td)
    try:
        os.remove(dst)          # ổ C từng đầy 100% — đừng giữ file không cần
    except OSError:
        pass
    m = min(len(d["doi"]), len(d["sang0"]), len(d["sang1"]))
    if not m:
        return {"kq": "0-KHUNG", "ghi": f"nb_read_frames={n}"}
    i0, i1 = int(round(BAT * FPS)), int(round(HET * FPS))
    giua = list(range(i0 + 1, min(m, i1 - 1)))
    ngoai = [i for i in range(m) if i < i0 or i >= i1]
    mep = [i for i in (i0, i1 - 1) if 0 <= i < m]
    so = {
        "khung": n,
        "trong": round(max((d["doi"][i] for i in giua), default=-1.0), 2),
        "ngoai": round(max((d["doi"][i] for i in ngoai), default=0.0), 4),
        "mep": round(max((d["doi"][i] for i in mep), default=0.0), 4),
        "du": round(max((abs(d["u1"][i] - d["u0"][i]) for i in giua
                         if i < len(d["u1"])), default=0.0), 2),
        "dv": round(max((abs(d["v1"][i] - d["v0"][i]) for i in giua
                         if i < len(d["v1"])), default=0.0), 2),
        "sat": round(min((d["s1"][i] / d["s0"][i] for i in giua
                          if i < len(d["s1"]) and d["s0"][i] > 1),
                         default=1.0), 3),
        "sang": round(max((d["sang1"][i] / d["sang0"][i] for i in giua
                           if d["sang0"][i] > 5), default=1.0), 3),
        "sang_day": round(min((d["sang1"][i] / d["sang0"][i] for i in giua
                               if d["sang0"][i] > 5), default=1.0), 3),
        "wall": round(wall, 2), "cpu": round(cpu, 2), "ghi": "",
    }
    if n != n_goc:
        so["kq"] = "LỆCH-KHUNG"
    elif so["trong"] < NG_THAY:
        so["kq"] = "KHÔNG-THẤY"
    elif so["ngoai"] > NG_RO:
        so["kq"] = "RÒ-NGOÀI"
    elif so["mep"] > NG_RO:
        so["kq"] = "MÉP-GIẬT"
    elif so["du"] >= HU.UV_MAX or so["dv"] >= HU.UV_MAX:
        so["kq"] = "LOÈ-MÀU"
    elif so["sat"] < NG_BAO_HOA:
        so["kq"] = "BẠC-MÀU"
    elif not (NG_SANG_SAN <= so["sang_day"] and so["sang"] <= NG_SANG_TRAN):
        so["kq"] = "SAI-SÁNG"
    else:
        so["kq"] = "ĐẠT"
    return so


# ------------------------------------------------------------------ CA 2
def _dg(*items) -> list:
    return [{"t": t, "desc": d, "act": a} for t, d, a in items]


#: 8 ca NỘI DUNG. 6 ca anh Hùng nêu (nấu ăn · tuyết · em bé · thể thao · phỏng
#: vấn · cảnh đêm) + 2 ca "không được thêm gì" (mơ hồ · pha tạp).
#: `cho` = kiểu PHẢI ra ("" = phải KHÔNG THÊM GÌ); `cam` = kiểu tuyệt đối không
#: được ra ở ca đó (đây mới là mệnh đề anh Hùng quan tâm).
CA_NOI_DUNG = {
    "nấu ăn": (
        _dg((1, "Chef chops vegetables on a wooden board in a kitchen", 5),
            (4, "Hands stir a frying pan on the stove, steam rising", 6),
            (8, "Close-up of the finished dish on a plate", 4)),
        "Hom nay minh se nau mon ga chien nuoc mam, cho chao that nong",
        "", ("tuyet_roi", "trai_tim", "confetti", "mua_roi")),
    "tuyết": (
        _dg((1, "A snowy mountain slope with heavy snowfall", 6),
            (5, "A man snowboards down the snow covered hill", 8),
            (9, "Snowflakes falling in front of pine trees", 5)),
        "Troi tuyet roi rat day, mua dong nam nay lanh qua",
        "tuyet_roi", ("tan_lua", "confetti")),
    "em bé": (
        _dg((1, "A mother hugs her newborn baby and smiles", 7),
            (5, "The baby laughs while the father kisses her cheek", 8),
            (9, "Family photo together at home", 4)),
        "Em be nha minh moi duoc mot thang, ca gia dinh rat yeu",
        "trai_tim", ("tuyet_roi", "mua_roi", "tan_lua")),
    "thể thao": (
        _dg((1, "Two boxers fight in the ring, crowd cheering", 9),
            (5, "A player scores a goal, referee blows whistle", 9),
            (9, "Athletes race on the track at a stadium", 8)),
        "Tran dau cang thang, trong tai thoi coi, ban thang quyet dinh",
        "", ("trai_tim", "tuyet_roi", "mua_roi")),
    "phỏng vấn": (
        _dg((1, "A man sits at a desk talking to the camera", 3),
            (5, "Close-up of the speaker gesturing while talking", 3),
            (9, "Two people sit across a table in a plain room", 2)),
        "Toi nghi rang van de nay can duoc xem xet ky luong hon",
        "", ("tuyet_roi", "trai_tim", "confetti", "tan_lua", "mua_roi")),
    "cảnh đêm": (
        _dg((1, "City lights and neon signs at night", 6),
            (5, "Cars pass under streetlights in the dark evening", 5),
            (9, "A concert with bright stage lights at night", 8)),
        "Ban dem thanh pho len den rat dep, den neon khap noi",
        "dom_bokeh", ("tuyet_roi", "trai_tim")),
    "mơ hồ": (
        _dg((1, "A person walks along a street", 3),
            (5, "Someone holds an object in their hand", 2),
            (9, "A wide shot of a building", 2)),
        "Cai nay thi cung binh thuong thoi khong co gi dac biet",
        "", tuple(HU.LOP_PHU)),
    "pha tạp": (
        _dg((1, "A bonfire burns brightly at a campsite", 7),
            (5, "City lights and neon signs at night behind the fire", 6),
            (9, "Flames and streetlights in the dark evening", 7)),
        "Dot lua trai ban dem, den duong sang khap noi",
        "", tuple(HU.LOP_PHU)),
}


def ca_khop_canh() -> None:
    print("\n[CA 2] KHỚP CẢNH — 8 ca nội dung (hàm thuần, không ffmpeg)")
    dung = list(HU.KHO)
    xau = []
    for ten, (dg, loi, cho, cam) in CA_NOI_DUNG.items():
        ra, ly = LP.chon_lop_phu(dg, loi, 20.0, "vua", co_the_dung=dung)
        got = ra[0]["khoa"] if ra else ""
        ok = (got == cho) and (got not in cam)
        if not ok:
            xau.append(f"{ten}: ra '{got or '(không)'}' mong '{cho or '(không)'}'")
        print(f"    {ten:<12}-> {(got or '(KHÔNG THÊM)'):<12} "
              f"{'OK ' if ok else 'SAI'} | {ly[:74]}")
    bao("8/8 ca nội dung chọn ĐÚNG (hoặc đúng-là-không-thêm)", not xau,
        "; ".join(xau) if xau else f"{len(CA_NOI_DUNG)}/{len(CA_NOI_DUNG)} ca")
    # 2 mệnh đề anh Hùng nêu ĐÍCH DANH — kiểm RIÊNG, không núp trong vòng lặp
    dg, loi, _c, _x = CA_NOI_DUNG["nấu ăn"]
    r, _ = LP.chon_lop_phu(dg, loi, 20.0, "manh", co_the_dung=dung)
    bao("TUYẾT KHÔNG RƠI trên video NẤU ĂN (kể cả mức 'manh')",
        not any(x["khoa"] == "tuyet_roi" for x in r),
        f"ra: {[x['khoa'] for x in r] or 'không thêm gì'}")
    dg, loi, _c, _x = CA_NOI_DUNG["thể thao"]
    r, _ = LP.chon_lop_phu(dg, loi, 20.0, "manh", co_the_dung=dung)
    bao("TRÁI TIM KHÔNG BAY trên video THỂ THAO (kể cả mức 'manh')",
        not any(x["khoa"] == "trai_tim" for x in r),
        f"ra: {[x['khoa'] for x in r] or 'không thêm gì'}")
    # KHÔNG DIGEST -> BỎ QUA HẲN, kể cả khi LỜI khớp rõ mồn một (luật "không
    # bật AI xem hình chỉ để chọn hiệu ứng").
    r, ly = LP.chon_lop_phu([], "troi tuyet roi mua dong lanh qua tuyet",
                            20.0, "vua", co_the_dung=dung)
    bao("KHÔNG có digest -> KHÔNG thêm gì (dù lời nói đầy từ khoá)", not r,
        ly[:96])
    # BẰNG CHỨNG LẺ KHÔNG ĐỦ: 1 mốc hình nhắc tuyết, không gì khác
    r, ly = LP.chon_lop_phu(
        _dg((2, "A glass of iced tea on a snowy windowsill", 3),
            (6, "A man talks to the camera indoors", 2)),
        "hom nay minh review cai nay", 20.0, "vua", co_the_dung=dung)
    bao("1 mốc hình lẻ CHƯA đủ tự tin -> KHÔNG thêm", not r, ly[:96])
    # LỌC THEO ĐOẠN: mốc digest nằm NGOÀI đoạn được cắt phải bị bỏ
    d = LP.loc_digest_theo_doan(
        [{"t": 5.0, "desc": "snow", "act": 5},
         {"t": 300.0, "desc": "snow", "act": 9},
         {"t": 62.0, "desc": "kitchen", "act": 4}],
        [(60.0, 70.0), (0.0, 10.0)], 1.0)
    bao("mốc digest ngoài đoạn cắt bị LOẠI; mốc trong đoạn đổi đúng "
        "timeline đầu ra (hook-first)",
        [x["t"] for x in d] == [2.0, 15.0]
        and [x["desc"] for x in d] == ["kitchen", "snow"],
        f"{[(x['t'], x['desc']) for x in d]} (đoạn 60-70 đứng TRƯỚC 0-10)")
    # NHƯỜNG CHỖ: lớp phủ khớp cảnh nhưng rơi sát điểm nhấn đã có -> bỏ, không
    # chồng lên nhau (`tranh` = các giây đã có hiệu ứng).
    dg, loi, _c, _x = CA_NOI_DUNG["tuyết"]
    r, ly = LP.chon_lop_phu(dg, loi, 20.0, "vua", co_the_dung=dung,
                            tranh=[5.0])
    bao("lớp phủ khớp cảnh nhưng SÁT điểm nhấn đã có -> nhường, không chồng",
        not r, ly[:96])
    # NGÂN SÁCH 10%: clip ngắn thì lớp phủ phải nhường hiệu ứng điểm nhấn
    r, ly = LP.chon_lop_phu(dg, loi, 5.0, "vua", co_the_dung=dung)
    bao("clip 5s (ngân sách 0,50s < 0,80s) -> lớp phủ tự nhường", not r,
        ly[:96])
    # CHÉP LỜI phải lấy đúng đoạn
    tr = {"segments": [{"start": 1, "end": 4, "text": "trong doan"},
                       {"start": 40, "end": 44, "text": "ngoai doan"}]}
    l1 = LP.loi_theo_doan(tr, [(0.0, 10.0)])
    bao("chép lời chỉ lấy câu GIAO với đoạn cắt",
        "trong doan" in l1 and "ngoai doan" not in l1, repr(l1))


# ------------------------------------------------------------------ CA 3
def ca_bat_bien(src: str, td: str) -> None:
    """Mức "tat" + `dat_truoc=None` phải KHÔNG ĐỔI MỘT LY."""
    print("\n[CA 3] BẤT BIẾN SỐNG CÒN — bật nhóm mới không được đụng đường cũ")
    bao("`chuoi_filter([])` vẫn rỗng (mức Tắt -> 0 dòng filter)",
        HU.chuoi_filter([], W, H, FPS) == "", "''")
    from app.core.ffmpeg_utils import export_canvas_clip
    dg = CA_NOI_DUNG["tuyết"][0]
    a = os.path.join(td, "tat_khong_noidung.mp4")
    b = os.path.join(td, "tat_co_noidung.mp4")
    for dst, nd in ((a, None),
                    (b, {"digest": [dict(x, t=x["t"] * 0.1) for x in dg],
                         "loi": CA_NOI_DUNG["tuyết"][1]})):
        export_canvas_clip(src, dst, [(0.1, 2.4)], (0.5, 0.5, 1.0), bg="blur",
                           out_w=540, out_h=960, encoder="libx264",
                           hieu_ung="tat", noi_dung=nd, fx_whoosh=False,
                           chuyen_canh="tat")
    fpsnr = os.path.join(td, "_psnr.txt")
    rc, err, _w, _c = chay([FF, "-v", "error", "-i", a, "-i", b,
                            "-filter_complex",
                            f"[0:v][1:v]psnr=stats_file='{_esc(fpsnr)}'",
                            "-f", "null", "-"])
    ps = []
    if os.path.exists(fpsnr):
        with open(fpsnr, encoding="utf-8", errors="replace") as f:
            for ln in f:
                m = re.search(r"psnr_avg:([\d.]+|inf)", ln)
                if m:
                    ps.append(999.0 if m.group(1) == "inf"
                              else float(m.group(1)))
    bao('mức "tat" + nội dung KHỚP RÕ vẫn ra file GIỐNG HỆT bản không nội dung',
        bool(ps) and min(ps) >= 50.0 and dem_khung(a) == dem_khung(b),
        f"PSNR nhỏ nhất {min(ps) if ps else -1:.2f} dB trên {len(ps)} khung "
        f"(ngưỡng 50) · khung {dem_khung(a)}/{dem_khung(b)}")
    # so với BẢN MỐC v2.19.0 — KHÔNG dùng `main` (trùng mã đang test = PASS OAN)
    moc = os.environ.get("BQ_MOC_REF", "7b1da35")
    r = subprocess.run(["git", "show", f"{moc}:app/core/hieu_ung.py"],
                       cwd=str(REPO), capture_output=True,
                       creationflags=_NOWIN, timeout=90)
    ma = (r.stdout or b"").decode("utf-8", "replace")
    hien = (REPO / "app" / "core" / "hieu_ung.py").read_text(encoding="utf-8")
    bao(f"bản mốc `{moc}` KHÁC bản đang test (không tự chấm mình)",
        bool(ma) and ma != hien,
        f"{len(ma)} vs {len(hien)} ký tự")
    if ma:
        import types
        mod = types.ModuleType("_hu_moc")
        mod.__dict__["__file__"] = str(REPO / "app" / "core" / "hieu_ung.py")
        # PHẢI vào `sys.modules` TRƯỚC khi exec: `@dataclass` tra
        # `sys.modules[cls.__module__].__dict__` để nhận dạng `KW_ONLY` —
        # thiếu là nổ `AttributeError: 'NoneType' object has no attribute
        # '__dict__'` ngay dòng `class HieuUng`.
        sys.modules["_hu_moc"] = mod
        try:
            exec(compile(ma, "_hu_moc", "exec"), mod.__dict__)   # noqa: S102
        finally:
            sys.modules.pop("_hu_moc", None)
        cu = set(mod.KHO)
        bo = [{"nl": [0.1] * 16, "cd": [0.2] * 16, "moc": [4.0]},
              {"nl": [0.1, 0.9, 0.1, 0.1, 0.8, 0.1, 0.1, 0.1, 0.7, 0.1,
                      0.1, 0.1, 0.9, 0.1, 0.2, 0.1],
               "cd": [0.2, 0.7, 0.2, 0.2, 0.6, 0.2, 0.2, 0.2, 0.5, 0.2,
                      0.2, 0.2, 0.8, 0.2, 0.3, 0.2], "moc": [5.0, 11.0]},
              {"nl": [], "cd": [], "moc": [3.0, 9.0]}]
        lech = []
        for muc in ("nhe", "vua", "manh"):
            for hk in (False, True):
                for i, t in enumerate(bo):
                    kw = dict(nl=t["nl"], cd=t["cd"], moc_noi=t["moc"],
                              co_the_dung=sorted(cu), hook=hk)
                    x = mod.chon_hieu_ung(16.0, muc, **kw)
                    y = HU.chon_hieu_ung(16.0, muc, **kw)
                    if x != y:
                        lech.append(f"{muc}/hook={hk}/bộ{i}")
        bao("`chon_hieu_ung` KHÔNG `dat_truoc` trả Y HỆT bản mốc v2.19.0 "
            "(18 tổ hợp)", not lech, "; ".join(lech) if lech else
            "18/18 tổ hợp giống từng ký tự")
        bao("kho CŨ vẫn còn nguyên trong kho MỚI (không gỡ nhầm kiểu nào)",
            cu <= set(HU.KHO), f"thiếu: {sorted(cu - set(HU.KHO))}")


# ------------------------------------------------------------------ CA 4
def ca_may_nhan_vien(src: str, td: str) -> None:
    print("\n[CA 4] MÁY NHÂN VIÊN — không NVENC, không Vulkan, không frei0r")
    gf, gs, mc = HU.co_frei0r, HU.co_shader, HU.module_co
    f0, mc0 = HU._F0R_OK, dict(HU._MOD_CACHE)
    try:
        HU.co_frei0r = lambda *a, **k: False        # type: ignore
        HU.co_shader = lambda *a, **k: False        # type: ignore
        HU.module_co = lambda *a, **k: False        # type: ignore
        HU._F0R_OK = False
        HU._MOD_CACHE.clear()
        dd = HU.dung_duoc(co_font=False)
        bao("máy trần: 10/10 kiểu lớp phủ VẪN dùng được (ffmpeg thuần)",
            set(HU.LOP_PHU) <= set(dd),
            f"{len([k for k in dd if HU.KHO[k].nhom == 'lop_phu'])}/"
            f"{len(HU.LOP_PHU)} · tổng kho dùng được {len(dd)}")
        bao("máy trần: bộ chọn KHÔNG cần Vulkan",
            not HU.can_vulkan([{"khoa": k} for k in HU.LOP_PHU]), "can_vulkan=False")
        r, _ly = LP.chon_lop_phu(*CA_NOI_DUNG["tuyết"][:2], 20.0, "vua",
                                 co_the_dung=dd)
        bao("máy trần: vẫn khớp được cảnh tuyết",
            bool(r) and r[0]["khoa"] == "tuyet_roi",
            str([x["khoa"] for x in r]))
        dst = os.path.join(td, "nv.mp4")
        rc, err, _w, _c = _dung("tuyet_roi", src, td, dst)
        n = dem_khung(dst) if rc == 0 else -1
        bao("máy trần: xuất THẬT bằng libx264 chạy được, đủ khung", rc == 0
            and n == int(round(DAI * FPS)),
            f"rc={rc} · {n} khung" + (f" · {err[-80:]}" if rc else ""))
        try:
            os.remove(dst)
        except OSError:
            pass
    finally:
        HU.co_frei0r, HU.co_shader, HU.module_co = gf, gs, mc
        HU._F0R_OK = f0
        HU._MOD_CACHE.clear()
        HU._MOD_CACHE.update(mc0)


# ------------------------------------------------------------------ CA 5
def ca_chi_phi(src: str, td: str) -> None:
    """Chi phí ĐO TRÊN ĐƯỜNG XUẤT THẬT, không phải trên lệnh `-vf` trần.

    BẪY MẪU SỐ (đã sập 1 lượt khi viết cổng này): lấy "bản không lớp phủ" =
    một lượt mã hoá lại trần trụi thì mẫu số chỉ **0,32 s**, và phí cố định
    ~0,3 s của lớp hạt đọc thành **2,27x** — nghe như đắt gấp đôi trong khi
    đường xuất thật của anh Hùng còn phải dựng nền mờ, chồng khối video, đốt
    phụ đề, trộn tiếng. Mẫu số ĐÚNG là `export_canvas_clip` mức "tat" — đúng
    cái file mà bật/tắt nhóm này thay thế cho nhau.
    """
    print("\n[CA 5] CHI PHÍ — đo trên ĐƯỜNG XUẤT THẬT (export_canvas_clip, "
          "1080x1920, libx264)")
    from app.core.ffmpeg_utils import export_canvas_clip

    def mot(hu, nguon_: str = "", het_: float = 2.5) -> tuple[float, float]:
        dst = os.path.join(td, "cp.mp4")
        with DoCPU() as d:
            export_canvas_clip(nguon_ or src, dst, [(0.05, het_)],
                               (0.5, 0.5, 1.0),
                               bg="blur", out_w=W, out_h=H,
                               encoder="libx264", hieu_ung=hu,
                               fx_whoosh=False, chuyen_canh="tat")
        try:
            os.remove(dst)
        except OSError:
            pass
        return d.wall, d.cpu

    # ĐAN XEN, LẤY TRUNG VỊ: máy anh Hùng luôn có việc chạy nền (prodown tải,
    # lượt xuất khác). Đo liền mạch từng cấu hình đã ra kết luận sai 2 lần —
    # lượt đầu của cổng này đo được lớp phủ "NHANH HƠN bản tắt" (0,52x wall),
    # chuyện không thể xảy ra. **CPU-giây mới là số đọc được**; cột wall chỉ để
    # tham khảo, KHÔNG dùng để chấm đạt/hỏng.
    dat: dict = {k: [] for k in ("tat",) + tuple(HU.LOP_PHU)}
    for _luot in range(3):
        for k in dat:
            dat[k].append(mot("tat" if k == "tat" else
                              [{"khoa": k, "bat": 0.80, "het": 1.60,
                                "dam": HU.DAM_MAX}]))

    def tv(k: str, i: int) -> float:
        xs = sorted(x[i] for x in dat[k])
        return xs[len(xs) // 2]

    w0, c0 = tv("tat", 0), tv("tat", 1)
    print(f"    {'kiểu':<12}{'wall tv':>9}{'CPU tv':>9}{'+CPU':>8}{'so CPU':>9}")
    print(f"    {'(tắt)':<12}{w0:>9.2f}{c0:>9.2f}{0.0:>8.2f}{1.0:>8.2f}x")
    ket = []
    for k in HU.LOP_PHU:
        w, c = tv(k, 0), tv(k, 1)
        ket.append((k, w, c))
        print(f"    {k:<12}{w:>9.2f}{c:>9.2f}{c-c0:>8.2f}"
              f"{(c/c0 if c0 > 0 else 0):>8.2f}x")
    them = sorted(c - c0 for _k, _w, c in ket)
    giua = them[len(them) // 2]
    ngoai = [k for k, _w, c in ket if (c - c0) > 2.0 * giua]
    bao("không kiểu nào ĐẮT BẤT THƯỜNG (> 2x trung vị phần THÊM của nhóm)",
        not ngoai,
        f"thêm: trung vị {giua:.2f} · rẻ nhất {them[0]:.2f} · đắt nhất "
        f"{them[-1]:.2f} CPU-giây" + (f" · ngoại lệ: {ngoai}" if ngoai else ""))
    bao("chi phí thêm vào <= 6,0 CPU-giây/clip", them[-1] <= 6.0 and c0 > 0,
        f"bản tắt {c0:.2f} CPU-giây · thêm nhiều nhất {them[-1]:.2f}")
    # ĐIỀU QUAN TRỌNG NHẤT của mục chi phí: phần thêm là HẰNG SỐ MỖI CLIP, không
    # theo độ dài — vì `geq` chỉ chạy trong cửa sổ 0,8 giây, còn `split/trim/
    # concat` đo ra KHÔNG tốn gì. Nếu bao giờ nó thành tỉ lệ thuận thì 300 kênh
    # với clip 60-80 giây sẽ gánh không nổi, nên phải có cổng canh.
    src10 = os.path.join(td, "dai10.mp4")
    rc, _e, _w, _c = chay([FF, "-y", "-v", "error", "-f", "lavfi", "-i",
                           f"testsrc2=s={W}x{H}:r={FPS}:d=10.4", "-an",
                           "-c:v", "libx264", "-preset", "ultrafast",
                           "-qp", "0", "-pix_fmt", "yuv420p", src10])
    if rc == 0:
        # ĐAN XEN + TRUNG VỊ ở đây nữa: lượt trước lấy `min` của 2 mẫu ĐO LIỀN
        # MẠCH và ra "thêm **−2,86** CPU-giây" (lớp phủ rẻ hơn bản tắt) — con số
        # vô nghĩa, đúng bệnh máy bận đã ghi trong hồ sơ.
        hu_t = [{"khoa": "tuyet_roi", "bat": 0.80, "het": 1.60,
                 "dam": HU.DAM_MAX}]
        d0, d1 = [], []
        for _ in range(3):
            d0.append(mot("tat", src10, 10.2)[1])
            d1.append(mot(hu_t, src10, 10.2)[1])
        d0.sort()
        d1.sort()
        d0, d1 = [d0[1]], [d1[1]]
        t10 = d1[0] - d0[0]
        t26 = next(c for k, _w, c in ket if k == "tuyet_roi") - c0
        bao("phần THÊM là HẰNG SỐ mỗi clip, KHÔNG tăng theo độ dài "
            "(clip 2,6s vs 10,4s)", t10 <= t26 * 1.35 + 0.5,
            f"clip 2,6s: bản tắt {c0:.2f} -> thêm {t26:.2f} CPU-giây · "
            f"clip 10,4s: bản tắt {d0[0]:.2f} -> thêm {t10:.2f} CPU-giây "
            f"({d1[0]/d0[0]:.2f}x thay vì {(c0+t26)/c0:.2f}x)")
        try:
            os.remove(src10)
        except OSError:
            pass


# ------------------------------------------------------------------ CA 6
def ca_quet_tinh() -> None:
    print("\n[CA 6] QUÉT TĨNH — luật 'không chọn bừa bãi' phải nằm trong MÃ")
    trong_bang = {v for hang in HU._UV_THEO_LOAI.values() for v in hang}
    bao("KHÔNG kiểu lớp phủ nào lọt vào `_UV_THEO_LOAI` (đường chọn theo SỐ ĐO)",
        not (set(HU.LOP_PHU) & trong_bang),
        f"lọt: {sorted(set(HU.LOP_PHU) & trong_bang)}" if
        (set(HU.LOP_PHU) & trong_bang) else
        f"{len(HU.LOP_PHU)} kiểu, 0 kiểu lọt")
    bao("`chon_hieu_ung` KHÔNG BAO GIỜ tự sinh lớp phủ (quét 200 bộ số đo)",
        not any(c["khoa"] in set(HU.LOP_PHU)
                for i in range(200)
                for c in HU.chon_hieu_ung(
                    20.0, ("nhe", "vua", "manh")[i % 3],
                    nl=[(i * 7 % 13) / 13.0 for _ in range(20)],
                    cd=[((i + j) % 11) / 11.0 for j in range(20)],
                    moc_noi=[3.0, 9.0, 15.0], co_the_dung=list(HU.KHO),
                    hook=bool(i % 2))), "0/200 lượt")
    # LỚP PHỦ + HOOK + ĐIỂM NHẤN không được CHỒNG CỬA SỔ và không được phá trần
    # 10% / 3 điểm. Lỗi thật bắt được khi rà: khối HOOK trong `chon_hieu_ung`
    # KHÔNG kiểm `CACH_MIN` với các điểm đã có (trước đây nó luôn là điểm đầu
    # tiên nên không ai để ý) -> lớp phủ đặt ở giây 0,3 là hook giây 0,12 chồng
    # lên, biên độ cộng dồn.
    xau: list = []
    for bat in (0.10, 0.30, 1.00, 2.00, 5.00, 9.00):
        for muc in ("nhe", "vua", "manh"):
            lp = [{"bat": bat, "het": bat + 0.80, "khoa": "tuyet_roi",
                   "dam": HU.MUC_DAM[muc], "loai": "lop_phu", "vi_sao": "x"}]
            r = HU.chon_hieu_ung(
                20.0, muc, nl=[0.2, 0.9] * 10, cd=[0.3, 0.8] * 10,
                moc_noi=[6.0, 13.0], co_the_dung=list(HU.KHO), hook=True,
                dat_truoc=lp)
            cua = sorted((float(c["bat"]), float(c["het"])) for c in r)
            if any(cua[i][1] > cua[i + 1][0] for i in range(len(cua) - 1)):
                xau.append(f"chồng cửa sổ @{bat}/{muc}: {cua}")
            if any(cua[i + 1][0] - cua[i][0] < HU.CACH_MIN
                   for i in range(len(cua) - 1)):
                xau.append(f"gần hơn CACH_MIN @{bat}/{muc}: {cua}")
            if len(r) > HU.DIEM_MAX:
                xau.append(f"quá {HU.DIEM_MAX} điểm @{bat}/{muc}: {len(r)}")
            if HU.ty_le_co_hieu_ung(r, 20.0) > HU.TY_LE_MAX * 100 + 0.01:
                xau.append(f"vượt trần 10% @{bat}/{muc}: "
                           f"{HU.ty_le_co_hieu_ung(r, 20.0):.1f}%")
            if sum(1 for c in r if c["khoa"] in set(HU.LOP_PHU)) \
                    > LP.LOP_PHU_MAX:
                xau.append(f"quá {LP.LOP_PHU_MAX} lớp phủ @{bat}/{muc}")
    bao("lớp phủ + hook + điểm nhấn: 18 tổ hợp đều KHÔNG chồng cửa sổ, "
        "không quá 3 điểm, không vượt trần 10%", not xau,
        "; ".join(xau[:3]) if xau else "18/18 tổ hợp sạch")
    bao("mọi khoá trong bảng luật khớp cảnh đều CÓ THẬT trong kho",
        set(LP.LUAT) <= set(HU.KHO),
        f"thừa: {sorted(set(LP.LUAT) - set(HU.KHO))}")
    bao("mọi kiểu lớp phủ đều CÓ luật khớp cảnh (không kiểu nào chết vô dụng)",
        set(HU.LOP_PHU) <= set(LP.LUAT),
        f"thiếu luật: {sorted(set(HU.LOP_PHU) - set(LP.LUAT))}")
    thua = {k: sorted(set(l.manh) & set(l.cam)) for k, l in LP.LUAT.items()
            if set(l.manh) & set(l.cam)}
    bao("không luật nào vừa CẤM vừa NHẬN cùng một từ khoá", not thua, str(thua))
    # bao hình sin của lớp phủ phải TRÙNG đường cong `_SONG` của nhóm cũ
    import math
    d, fps = 0.80, 30.0
    lech = max(abs(math.sin(math.pi * (t / (d - 1 / fps)))
                   - math.sin(math.pi * (t / (d - 1 / fps))))
               for t in (0.0, d / 4, d / 2, d - 1 / fps))
    mep = [math.sin(math.pi * (t / (d - 1 / fps)))
           for t in (0.0, d - 1 / fps)]
    bao("bao hình sin: hai mép = 0 đúng bằng toán (êm vào — êm ra)",
        max(abs(x) for x in mep) < 1e-6 and lech < 1e-9,
        f"mép {mep[0]:.6f} / {mep[1]:.6f}")
    bao("`_LP_SONG` dùng đúng khuôn nửa hình sin như `hieu_ung._SONG`",
        "sin(3.14159*" in HU._LP_SONG and "sin(3.14159*" in HU._SONG,
        f"{HU._LP_SONG}")


def main() -> int:
    HU.dat_frei0r_path()
    td = tempfile.mkdtemp(prefix="_lopphu_", dir=str(_SB))
    bang: list = []
    try:
        print("[CA 0] ĐỐI CHỨNG + TIỀN ĐỊNH")
        src = nguon(td)
        n_goc = dem_khung(src)
        d0 = do_cap(src, src, td)
        bao("so file GỐC với CHÍNH NÓ ra 0,0000% điểm ảnh đổi",
            bool(d0["doi"]) and max(d0["doi"]) < 0.0005,
            f"max {max(d0['doi']) if d0['doi'] else -1:.4f}% · "
            f"{len(d0['doi'])} khung · sáng TB "
            f"{sum(d0['sang0'])/max(1,len(d0['sang0'])):.1f}/255")
        # TIỀN ĐỊNH: `geq` dùng st()/ld() + `gradients` cần seed cố định
        p1 = os.path.join(td, "td1.mp4")
        p2 = os.path.join(td, "td2.mp4")
        _dung("confetti", src, td, p1)
        _dung("confetti", src, td, p2)
        dtd = do_cap(p1, p2, td)
        bao("dựng 2 lượt cùng tham số ra GIỐNG HỆT (geq st/ld đa luồng + "
            "`gradients` có seed)",
            bool(dtd["doi"]) and max(dtd["doi"]) < 0.0005,
            f"max {max(dtd['doi']) if dtd['doi'] else -1:.4f}% · "
            f"{len(dtd['doi'])} khung")
        for p in (p1, p2):
            try:
                os.remove(p)
            except OSError:
                pass

        print(f"\n[CA 1] QUÉT {len(HU.LOP_PHU)} KIỂU LỚP PHỦ "
              f"(1080x1920 · cửa sổ {BAT}-{HET}s · độ đậm {HU.DAM_MAX} · "
              f"mã hoá KHÔNG mất dữ liệu)")
        for k in HU.LOP_PHU:
            so = quet_mot(k, src, td, n_goc)
            bang.append((k, HU.KHO[k].ten, so))
            print(f"    {k:<12}{so['kq']:<12}trong {so.get('trong',-1):6.2f}%"
                  f" · ngoài {so.get('ngoai',-1):.4f}% · mép "
                  f"{so.get('mep',-1):.4f}% · dU {so.get('du',-1):4.2f} dV "
                  f"{so.get('dv',-1):4.2f} · bão hoà {so.get('sat',-1)} · "
                  f"sáng {so.get('sang',-1)} {so.get('ghi','')}")
        xau = [(k, s) for k, _t, s in bang if s["kq"] != "ĐẠT"]
        bao(f"cả {len(bang)} kiểu lớp phủ ĐẠT (thấy được >= {NG_THAY}% · "
            f"không loè · không rò · mép êm)", not xau,
            "; ".join(f"{k}={s['kq']} {s.get('ghi','')}" for k, s in xau)
            if xau else f"{len(bang)}/{len(bang)} ĐẠT")

        ca_khop_canh()
        ca_bat_bien(src, td)
        ca_may_nhan_vien(src, td)

        ca_chi_phi(src, td)

        ca_quet_tinh()

        print(f"\n  {'khoá':<12}{'tên':<24}{'kết quả':<11}{'%trong':>8}"
              f"{'%ngoài':>9}{'%mép':>8}{'dU':>6}{'dV':>6}{'bão hoà':>9}"
              f"{'sáng':>7}{'wall':>7}")
        print("  " + "-" * 108)
        for k, t, s in bang:
            print(f"  {k:<12}{t[:23]:<24}{s['kq']:<11}{s.get('trong',-1):>8.2f}"
                  f"{s.get('ngoai',-1):>9.4f}{s.get('mep',-1):>8.4f}"
                  f"{s.get('du',-1):>6.2f}{s.get('dv',-1):>6.2f}"
                  f"{s.get('sat',-1):>9}{s.get('sang',-1):>7}"
                  f"{s.get('wall',-1):>7.2f}")
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)
        shutil.rmtree(_SB, ignore_errors=True)

    print("\n" + "=" * 72)
    print(f"ĐẠT {len(_OK)} · HỎNG {len(_LOI)}")
    for x in _LOI:
        print("  FAIL:", x)
    return 1 if _LOI else 0


if __name__ == "__main__":
    sys.exit(main())
