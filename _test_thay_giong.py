# -*- coding: utf-8 -*-
"""CỔNG 53 — THAY GIỌNG NÓI (giữ nhạc nền + tiếng động).

Chạy bằng THÀNH PHẦN THẬT (ffmpeg thật, nguồn lavfi thật). KHÔNG mock.

VIỆC NẶNG NHẤT CỦA CỔNG NÀY: chứng minh **KHÔNG BAO GIỜ MẤT VIDEO CỦA ANH
HÙNG**. Anh Hùng nói "làm xong tự xoá video gốc" nhưng xoá hẳn là mất vĩnh
viễn — mọi đường dọn gốc phải qua thùng rác khôi phục được, và chỉ được chạy
SAU KHI file mới đã kiểm hợp lệ.

CÁC CA:
  1. `kiem_video_ra` bắt đủ 5 kiểu file hỏng mà ffmpeg vẫn trả mã 0.
  2. `thay_the_video_goc` — gốc vào thùng rác, KHÔNG mất; file mới đúng chỗ.
  3. File mới hỏng -> TỪ CHỐI đụng tới gốc (gốc còn nguyên).
  4. Thùng rác KHÔNG được nằm trong %TEMP% (bị dọn = mất video).
  5. TỰ KIỂM BỘ DÒ MÉO: `do_meo` phải NÉM khi tên chỉ số sai, không được trả
     None âm thầm (bẫy đã sập thật 14/08 — xem docstring `do_meo`).
  6. `khop_thoi_gian` — đặt đúng mốc đầu, không chồng lấn khi có đủ chỗ.
  7. `_co_the_tru_kenh_giua` chặn audio mono-nhân-đôi (trừ ra là im lặng hẳn).
  8. `cau_tu_transcript` cắt segment dài theo mốc TỪ, không nuốt chữ.

    .venv\\Scripts\\python _test_thay_giong.py
"""
from __future__ import annotations

import atexit
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = str(Path(__file__).resolve().parent)   # KHÔNG ghi cứng đường repo
sys.path.insert(0, REPO)

# stdout chuyển hướng ra file/pipe thì Python lấy **cp1252**, và dòng `print`
# tiếng Việt ĐẦU TIÊN ném `UnicodeEncodeError` -> cổng chết trong 0-1 giây với
# mã thoát 1 trong khi mã app không sai chỗ nào. `_test_guard` có vá sẵn,
# NHƯNG khối dọn hộp cát dưới đây chạy TRƯỚC nó (phải vậy: dọn xong mới tạo
# hộp mới) nên phải tự vá ở đây. Đã sập đúng bẫy này 15/08/2026 ngay trong
# lượt kiểm bản vá dọn rác.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

# ==================================================================
# HỘP CÁT PHẢI DỌN ĐƯỢC **KỂ CẢ KHI CỔNG BỊ GIẾT** — 15/08/2026
# ==================================================================
# CHUYỆN ĐÃ XẢY RA THẬT: cổng này bị `timeout` giết 3 lần. Phần dọn nằm ở
# CUỐI FILE (dòng thẳng, không `finally`, không `atexit`) nên không lượt nào
# chạy tới nó -> mỗi lượt bỏ lại một hộp cát **80-131 GB**, `%TEMP%` phình
# **420 GB**, ổ C **đầy 100% / 0 byte**, ffmpeg báo `No space left on device`.
#
# BA LỚP, KHÔNG PHẢI MỘT — mỗi lớp bịt một kiểu chết khác nhau:
#   1. **DỌN HỘP CÁT CŨ LÚC KHỞI ĐỘNG — lớp CHẮC NHẤT, và là lớp duy nhất
#      không cần tiến trình cũ hợp tác.** `timeout` giết bằng tín hiệu mà
#      Windows KHÔNG bảo đảm cho chạy handler (bị `TerminateProcess` thì
#      không một dòng Python nào chạy nữa), nên đừng đặt hết niềm tin vào
#      lớp 2/3. Lớp này chỉ hỏi "PID chủ hộp cát còn sống không".
#   2. `atexit` — thoát êm, `sys.exit`, ngoại lệ không ai bắt.
#   3. `SIGTERM`/`SIGBREAK`/`SIGINT` — bị giết "tử tế".
_TIEN_TO = "tg_gate_"


def _con_song(pid: int) -> bool:
    """PID còn sống không?

    **TUYỆT ĐỐI KHÔNG dùng `os.kill(pid, 0)` để hỏi thăm trên Windows** —
    CPython cài `os.kill` thành `TerminateProcess(handle, sig)`, nên "hỏi"
    bằng tín hiệu 0 là **GIẾT THẬT** tiến trình đó với mã thoát 0. Không có
    `psutil` thì trả True: không biết chắc -> GIỮ (luật chung của repo).
    """
    try:
        import psutil
    except ImportError:
        return True
    try:
        return psutil.pid_exists(pid)
    except Exception:  # noqa: BLE001
        return True


def _don_hop_cat_cu() -> tuple[int, float]:
    """Xoá hộp cát `tg_gate_*` của các tiến trình ĐÃ CHẾT. Trả (số, GB)."""
    goc = Path(tempfile.gettempdir())
    n, byte = 0, 0
    try:
        ds = list(goc.glob(_TIEN_TO + "*"))
    except OSError:
        return (0, 0.0)
    for d in ds:
        try:
            if not d.is_dir():
                continue
            phan = d.name[len(_TIEN_TO):].split("_")[0]
            if phan.isdigit():
                # tên MỚI mang PID -> hỏi thẳng, không phải đoán theo tuổi
                if int(phan) == os.getpid() or _con_song(int(phan)):
                    continue
            elif d.stat().st_mtime > time.time() - 7200:
                continue        # tên kiểu CŨ (không PID) -> đợi đủ 2 giờ
            byte += sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
            shutil.rmtree(d, ignore_errors=True)
            n += 1
        except OSError:
            continue
    return (n, byte / 1073741824.0)


_cu_n, _cu_gb = _don_hop_cat_cu()
if _cu_n:
    print(f"  dọn {_cu_n} hộp cát tg_gate_* còn sót của lượt TRƯỚC "
          f"({_cu_gb:.2f} GB)")

#: Tên mang PID để lượt sau biết chắc chủ nó chết hay chưa (cùng cách
#: `ffmpeg_utils._tag_moi` đánh dấu mảnh `_seg_p<pid>…`).
T = tempfile.mkdtemp(prefix=f"{_TIEN_TO}{os.getpid()}_")


def _don_hop_cat(*_a) -> None:
    """Xoá hộp cát của CHÍNH lượt này. Gọi bao nhiêu lần cũng được."""
    shutil.rmtree(T, ignore_errors=True)


def _bi_giet(_sig=None, _frame=None) -> None:
    """Bị giết -> dọn rồi thoát THẲNG (đang trong handler, đừng dựng lại)."""
    _don_hop_cat()
    try:
        sys.stdout.flush()
    except Exception:  # noqa: BLE001
        pass
    os._exit(2)


atexit.register(_don_hop_cat)
for _ten_sig in ("SIGTERM", "SIGBREAK", "SIGINT"):
    _sig_obj = getattr(signal, _ten_sig, None)
    if _sig_obj is not None:
        try:
            signal.signal(_sig_obj, _bi_giet)
        except (ValueError, OSError):
            pass                 # không phải luồng chính -> bỏ qua

os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_DB_PATH"] = str(Path(T) / "studio.db")
os.environ["BQ_FFMPEG_SLOTS"] = "1"

import _test_guard  # noqa: E402,F401 - CẤM test mở Explorer/trình phát máy user

from config import settings  # noqa: E402
from app.core import thay_giong as tg  # noqa: E402

OK: list[str] = []
FAIL: list[str] = []


def dat(dieu: str, ok: bool, chi_tiet: str = "") -> None:
    (OK if ok else FAIL).append(f"{dieu} {chi_tiet}".strip())
    print(f"  [{'ĐẠT' if ok else 'HỎNG'}] {dieu}"
          + (f" — {chi_tiet}" if chi_tiet else ""))


#: Trần thời gian cho MỘT lệnh ffmpeg dựng nguồn của cổng này.
#: **KHÔNG phải "chờ cho chắc" mà là VAN CHẶN.** Mọi nguồn ở đây là clip
#: 1-3 giây nên 120 giây đã rộng gấp bội; con số này tồn tại để một lệnh
#: ffmpeg lỡ viết VÔ HẠN không thể ghi quá ~14 GB trước khi bị giết (đo
#: 15/08/2026: **115,4 MB/giây** -> chạy tự do 15 phút là **101 GB**).
FF_HAN_GIAY = 120


def ff(args: list[str]) -> int:
    try:
        r = subprocess.run([settings.FFMPEG_PATH, "-y", "-hide_banner",
                            "-loglevel", "error", *args],
                           capture_output=True, text=True,
                           timeout=FF_HAN_GIAY)
    except subprocess.TimeoutExpired:
        # `subprocess.run` tự giết tiến trình con trước khi ném -> không để
        # lại ffmpeg mồ côi đang bơm dữ liệu vào đĩa.
        loi = f"ffmpeg quá {FF_HAN_GIAY}s, đã giết: {' '.join(args[:6])}"
        FAIL.append(loi)
        print(f"  [HỎNG] {loi}")
        return 124
    return r.returncode


def nguon_video(dst: Path, giay: float = 3.0, co_tieng: bool = True) -> Path:
    """Video thật bằng lavfi (không phụ thuộc file trên máy)."""
    args = ["-f", "lavfi", "-i", f"testsrc2=size=320x240:rate=25:d={giay}"]
    if co_tieng:
        args += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={giay}"]
    args += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", f"{giay}"]
    if co_tieng:
        args += ["-c:a", "aac", "-shortest"]
    args += [str(dst)]
    ff(args)
    return dst


# ==================================================================
print("\n=== CA 1: kiem_video_ra bat file hong ma ffmpeg van tra ma 0 ===")
d1 = Path(T) / "ca1"
d1.mkdir(parents=True, exist_ok=True)
that = nguon_video(d1 / "that.mp4", 3.0)

try:
    k = tg.kiem_video_ra(that, 3.0)
    dat("video that PHAI qua duoc", k["khung"] > 0 and k["rms"] > 0,
        f"{k['khung']} khung, RMS {k['rms']}")
except Exception as e:  # noqa: BLE001
    dat("video that PHAI qua duoc", False, str(e))

# (a) khong co file
try:
    tg.kiem_video_ra(d1 / "khong_co.mp4", 3.0)
    dat("bat file KHONG TON TAI", False, "khong nem")
except RuntimeError:
    dat("bat file KHONG TON TAI", True)

# (b) file 0 byte
(d1 / "rong.mp4").write_bytes(b"")
try:
    tg.kiem_video_ra(d1 / "rong.mp4", 3.0)
    dat("bat file 0 byte", False, "khong nem")
except RuntimeError:
    dat("bat file 0 byte", True)

# (c) file CHI CO TIENG, khong khung hinh
ff(["-f", "lavfi", "-i", "sine=frequency=440:duration=3", "-c:a", "aac",
    str(d1 / "chi_tieng.m4a")])
try:
    tg.kiem_video_ra(d1 / "chi_tieng.m4a", 3.0)
    dat("bat file 0 KHUNG HINH", False, "khong nem")
except RuntimeError:
    dat("bat file 0 KHUNG HINH", True)

# (d) file CO HINH nhung IM LANG HAN
ff(["-f", "lavfi", "-i", "testsrc2=size=320x240:rate=25:d=3",
    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-t", "3",
    "-shortest", str(d1 / "im_lang.mp4")])
try:
    tg.kiem_video_ra(d1 / "im_lang.mp4", 3.0)
    dat("bat file IM LANG HAN", False, "khong nem")
except RuntimeError:
    dat("bat file IM LANG HAN", True)

# (e) LECH DO DAI
nguon_video(d1 / "ngan.mp4", 1.0)
try:
    tg.kiem_video_ra(d1 / "ngan.mp4", 3.0)
    dat("bat LECH DO DAI (1s vs 3s)", False, "khong nem")
except RuntimeError:
    dat("bat LECH DO DAI (1s vs 3s)", True)


# ==================================================================
print("\n=== CA 2: thay the video goc — GOC PHAI VAO THUNG RAC, KHONG MAT ===")
d2 = Path(T) / "ca2" / "KenhThu"
d2.mkdir(parents=True, exist_ok=True)
goc = nguon_video(d2 / "video_goc.mp4", 3.0)
goc_bytes = goc.read_bytes()
moi = nguon_video(d2 / "ban_moi.mp4", 3.0, co_tieng=True)
thung = Path(T) / "ca2" / "ThungRac"
thung.mkdir(parents=True, exist_ok=True)

r = tg.thay_the_video_goc(goc, moi, kenh="KenhThu", thung_rac=str(thung))
dat("bao da thay", bool(r.get("thay")), str(r)[:120])
dat("video moi nam DUNG CHO/TEN cua goc", goc.exists() and goc.is_file())
dat("file moi khong con o cho cu", not moi.exists())

# GỐC PHẢI CÒN Ở ĐÂU ĐÓ — quét cả thùng rác user lẫn _DaXoa nội bộ
con = [p for p in Path(T).rglob("*.mp4") if p.read_bytes() == goc_bytes]
dat("GOC VAN CON (khoi phuc duoc)", bool(con),
    f"tim thay {len(con)} ban sao dung byte: "
    + (str(con[0].relative_to(T)) if con else "KHONG CO — MAT VIDEO!"))


# ==================================================================
print("\n=== CA 3: file moi HONG -> TU CHOI dung toi goc ===")
d3 = Path(T) / "ca3" / "Kenh3"
d3.mkdir(parents=True, exist_ok=True)
goc3 = nguon_video(d3 / "goc3.mp4", 2.0)
truoc = goc3.read_bytes()
xau = d3 / "xau.mp4"
xau.write_bytes(b"x" * 100)          # file rac, chua toi 10 KiB
try:
    tg.thay_the_video_goc(goc3, xau, kenh="Kenh3", thung_rac=str(thung))
    dat("tu choi file moi HONG", False, "khong nem")
except RuntimeError:
    dat("tu choi file moi HONG", True)
dat("goc CON NGUYEN VEN sau khi tu choi",
    goc3.exists() and goc3.read_bytes() == truoc)


# ==================================================================
print("\n=== CA 4: THUNG RAC KHONG DUOC NAM TRONG %TEMP% ===")
from app.core import pipeline as P  # noqa: E402

temp_rac = str(Path(tempfile.gettempdir()) / "thung_rac_gia")
dat("_is_safe_recycle_root TU CHOI thu muc trong %TEMP%",
    not P._is_safe_recycle_root(temp_rac), temp_rac)
# LUU Y: sandbox cua chinh cong nay NAM TRONG %TEMP%, nen KHONG duoc lay thu
# muc sandbox lam vi du "thu muc thuong" — no bi tu choi la ĐUNG.
# `_is_safe_recycle_root` la ham THUAN tren chuoi, khong can file co that.
dat("_is_safe_recycle_root NHAN thu muc BEN VUNG",
    P._is_safe_recycle_root(r"D:\KhoVideo\ThungRac"), r"D:\KhoVideo\ThungRac")

d4 = Path(T) / "ca4" / "Kenh4"
d4.mkdir(parents=True, exist_ok=True)
g4 = nguon_video(d4 / "g4.mp4", 2.0)
b4 = g4.read_bytes()
m4 = nguon_video(d4 / "m4.mp4", 2.0)
# truyen thung rac NAM TRONG %TEMP% -> phai roi ve _DaXoa noi bo, KHONG mat
r4 = tg.thay_the_video_goc(g4, m4, kenh="Kenh4", thung_rac=temp_rac)
con4 = [p for p in Path(T).rglob("*.mp4") if p.read_bytes() == b4]
noi_cat = str(r4.get("goc_da_vao_thung_rac") or "")
dat("thung rac %TEMP% -> goc VAN CON o noi khoi phuc duoc", bool(con4),
    (str(con4[0].relative_to(T)) if con4 else "MAT VIDEO!"))
# bat bien THAT: KHONG duoc dung cai thung rac %TEMP% user lo dat
dat("KHONG dung thung rac %TEMP% user lo dat",
    bool(noi_cat) and not noi_cat.lower().startswith(temp_rac.lower()),
    f"cat vao: {noi_cat[-70:]}")
dat("goc di vao _DaXoa noi bo (canh thu muc kenh)",
    P.RECYCLE_DIRNAME.lower() in noi_cat.lower(), P.RECYCLE_DIRNAME)


# ==================================================================
print("\n=== CA 5: TU KIEM BO DO MEO (bay da sap that 14/08) ===")
wav5 = Path(T) / "ca5.wav"
Path(T).mkdir(parents=True, exist_ok=True)
ff(["-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-ac", "2",
    "-ar", "44100", "-c:a", "pcm_s16le", str(wav5)])
try:
    m = tg.do_meo(wav5)
    dat("do_meo doc duoc dinh THAT", m.get("dinh") is not None,
        f"dinh {m.get('dinh')} dBFS, cham tran {m.get('cham_tran')}")
except Exception as e:  # noqa: BLE001
    dat("do_meo doc duoc dinh THAT", False, str(e))

def _ma_that(path: Path) -> str:
    """Mã NGUỒN đã BỎ comment + docstring/chuỗi.

    BÀI HỌC CỔNG 47/51 (đỏ oan): quét tĩnh bằng `in` trên cả file thì chính
    DÒNG GHI CHÚ giải thích bản vá bị kể là vi phạm. Ở đây docstring của
    `do_meo` CỐ Ý nhắc tên sai `Number_of_clipped_samples` để người sau khỏi
    dùng lại — quét thô sẽ FAIL OAN vĩnh viễn.
    """
    import io
    import tokenize
    ra = []
    with open(path, "rb") as fh:
        for tok in tokenize.tokenize(io.BytesIO(fh.read()).readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            ra.append(tok.string)
    return " ".join(ra)


_src_ma = _ma_that(Path(REPO, "app/core/thay_giong.py"))
_src_tho = Path(REPO, "app/core/thay_giong.py").read_text(encoding="utf-8")
# ten chi so nam TRONG chuoi filter nen phai doc ban THO cho ve "co dung ten
# moi khong", con ban DA BO CHUOI dung de chac chan khong con MA nao xai ten cu.
dat("do_meo dung ten chi so DUNG (Abs_Peak_count)",
    "Abs_Peak_count" in _src_tho, "ffmpeg N-121186 chi co ten nay")
dat("TU KIEM BO DO: ban bo-chuoi KHONG con ten cu (ghi chu khong bi ke la vi pham)",
    "Number_of_clipped_samples" not in _src_ma,
    "ghi chu van duoc phep nhac ten cu de canh bao")

# file KHONG PHAI audio -> phai nem, khong tra None
try:
    tg.do_meo(Path(T) / "ca1" / "rong.mp4")
    dat("do_meo NEM khi khong doc duoc (khong tra None am tham)", False,
        "khong nem")
except RuntimeError:
    dat("do_meo NEM khi khong doc duoc (khong tra None am tham)", True)


# ==================================================================
print("\n=== CA 6: khop_thoi_gian — dung moc dau, khong chong lan ===")
d6 = Path(T) / "ca6"
d6.mkdir(parents=True, exist_ok=True)
# 3 cau, moi cau khung 2s, cach nhau thoai mai
cau6 = [{"start": 0.0, "end": 2.0, "text": "a"},
        {"start": 3.0, "end": 5.0, "text": "b"},
        {"start": 6.0, "end": 8.0, "text": "c"}]
files6 = []
for i, dur in enumerate((1.5, 1.8, 1.2)):     # deu LOT khung -> tempo 1.0
    p = d6 / f"s{i}.wav"
    ff(["-f", "lavfi", "-i", f"sine=frequency=300:duration={dur}",
        "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", str(p)])
    files6.append(str(p))
kh = tg.khop_thoi_gian(cau6, files6, [True] * 3, 10.0, d6 / "ra")
# `lech_dau_ms` NAY LA SO DO (silencedetect tren chinh file da ghi), khong con
# la hang so 0.0 gan cung ("dat DUNG moc goc" = moc DAT FILE, khong phai moc
# PHAT RA TIENG). File sine lien tuc thi le im ~0 nen van phai NHO.
dat("dat DUNG moc dau (le im do duoc < 60 ms)", kh["lech_dau_ms_max"] < 60.0,
    f"{kh['lech_dau_ms_max']} ms")
# CHONG PASS OAN: file CO 0,5s im o dau thi con so phai LEN, khong duoc van 0.
d6b = d6 / "leim"
d6b.mkdir(parents=True, exist_ok=True)
p_im = d6b / "im.wav"
# `-t` PHẢI đứng TRƯỚC `-i` mà nó giới hạn — nó là tuỳ chọn ĐẦU VÀO, áp cho
# đầu vào ĐƯỢC KHAI SAU NÓ. Bản cũ viết `-i anullsrc … -t 0.5 -i sine …` nên
# 0,5 giây rơi vào SINE (vốn đã có `duration=1.0`), còn `anullsrc` **KHÔNG có
# hạn nào = VÔ HẠN**; `concat` đọc đoạn 0 tới EOF mà EOF không bao giờ tới ->
# ffmpeg bơm im lặng vào `im.wav` mãi mãi. ĐO 15/08/2026: **115,4 MB/giây**
# (1.452.015.616 byte trong 12 giây). Đây chính là chỗ làm đầy ổ C 420 GB và
# là chỗ cổng "treo ở CA 6" suốt 3 lượt — `ff()` cũ KHÔNG có hạn giờ nên nó
# không treo vì mạng hay vì Demucs, nó treo vì đang ghi đĩa không điểm dừng.
ff(["-f", "lavfi", "-t", "0.5", "-i", "anullsrc=r=44100:cl=stereo",
    "-f", "lavfi", "-i", "sine=frequency=300:duration=1.0",
    "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1[o]", "-map", "[o]",
    "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", str(p_im)])
kh_im = tg.khop_thoi_gian([{"start": 0.0, "end": 2.0, "text": "a"}],
                          [str(p_im)], [True], 10.0, d6b / "ra")
dat("lech_dau la SO DO THAT (0,5s im dau -> >= 400 ms)",
    kh_im["lech_dau_ms_max"] >= 400.0, f"{kh_im['lech_dau_ms_max']} ms")
dat("im_duoi_chu_ms do duoc (khung 2s ma tieng het som)",
    kh_im["im_duoi_chu_ms_max"] > 200.0,
    f"{kh_im['im_duoi_chu_ms_max']} ms")
dat("moc_tieng tra ve duoc", len(kh_im.get("moc_tieng") or []) == 1,
    f"{len(kh_im.get('moc_tieng') or [])} moc")
if kh_im.get("moc_tieng"):
    _i, _a, _b = kh_im["moc_tieng"][0]
    dat("moc NOI sau moc DAT FILE (0,0s)", _a > 0.4 and _b > _a,
        f"noi {_a:.3f} -> {_b:.3f}")
# dong_chu_theo_giong: ham THUAN, cong thu pha goi thang duoc
_dc = tg.dong_chu_theo_giong([(0, 1.0, 1.4), (1, 3.0, 3.9)], ["mot", "hai"])
dat("dong_chu_theo_giong lay DUNG moc tieng",
    len(_dc) == 2 and abs(_dc[0][0] - 1.0) < 1e-6
    and abs(_dc[1][0] - 3.0) < 1e-6, str(_dc))
dat("chu toi thieu 0,90s va KHONG lan sang cau ke",
    _dc[0][1] >= 1.85 and _dc[0][1] <= 3.0 - 0.05, f"{_dc[0]}")
dat("KHONG chong lan khi cau lot khung", kh["chong_lan_ms_max"] < 1.0,
    f"{kh['chong_lan_ms_max']} ms")
dat("KHONG ep toc do khi da lot khung", kh["tempo_max"] <= 1.001,
    f"tempo_max {kh['tempo_max']}")

# cau QUA DAI -> phai ep, nhung van khong duoc chong lan qua nhieu
p_dai = d6 / "dai.wav"
ff(["-f", "lavfi", "-i", "sine=frequency=300:duration=2.6", "-ac", "2",
    "-ar", "44100", "-c:a", "pcm_s16le", str(p_dai)])
kh2 = tg.khop_thoi_gian(
    [{"start": 0.0, "end": 2.0, "text": "a"},
     {"start": 2.2, "end": 4.0, "text": "b"}],
    [str(p_dai), files6[0]], [True, True], 6.0, d6 / "ra2")
dat("cau tran khung -> CO ep toc do", kh2["tempo_max"] > 1.0,
    f"tempo_max {kh2['tempo_max']}")
dat("ep xong KHONG chong lan cau ke", kh2["chong_lan_ms_max"] < 1.0,
    f"{kh2['chong_lan_ms_max']} ms")


# ==================================================================
print("\n=== CA 7: chan audio MONO-NHAN-DOI (tru kenh giua ra im lang) ===")
d7 = Path(T) / "ca7"
d7.mkdir(parents=True, exist_ok=True)
mono2 = d7 / "mono_nhan_doi.wav"
ff(["-f", "lavfi", "-i", "sine=frequency=440:duration=2",
    "-af", "pan=stereo|c0=c0|c1=c0", "-ar", "44100", "-c:a", "pcm_s16le",
    str(mono2)])
duoc, _ = tg._co_the_tru_kenh_giua(mono2)
dat("nhan ra mono-nhan-doi (KHONG tru kenh giua duoc)", not duoc)
try:
    tg.tach_giong(mono2, d7 / "ra", cach="nhe")
    dat("cach nhe TU CHOI mono-nhan-doi", False, "khong nem")
except RuntimeError:
    dat("cach nhe TU CHOI mono-nhan-doi", True)

stereo = d7 / "stereo_that.wav"
ff(["-f", "lavfi", "-i", "sine=frequency=440:duration=2",
    "-f", "lavfi", "-i", "sine=frequency=660:duration=2",
    "-filter_complex", "[0:a][1:a]join=inputs=2:channel_layout=stereo[o]",
    "-map", "[o]", "-ar", "44100", "-c:a", "pcm_s16le", str(stereo)])
duoc2, _ = tg._co_the_tru_kenh_giua(stereo)
dat("stereo THAT thi tru kenh giua duoc", duoc2)


# ==================================================================
print("\n=== CA 8: cau_tu_transcript — cat segment dai theo moc TU ===")
d = {
    "segments": [{"start": 0.0, "end": 30.0, "text": "mot hai ba bon nam sau"}],
    "words": [{"start": float(i) * 5, "end": float(i) * 5 + 4.5,
               "word": f" tu{i}"} for i in range(6)],
}
cs = tg.cau_tu_transcript(d, gop_toi_da=12.0)
dat("segment 30s bi CAT NHO", len(cs) >= 2, f"{len(cs)} cau")
dat("moi cau <= ~12s", all(c["end"] - c["start"] <= 13.0 for c in cs),
    str([round(c["end"] - c["start"], 1) for c in cs]))
dat("KHONG nuot chu", sum(len(c["text"].split()) for c in cs) == 6,
    str([c["text"] for c in cs]))
d_ngan = {"segments": [{"start": 0.0, "end": 5.0, "text": "cau ngan"}],
          "words": []}
dat("segment ngan giu nguyen", len(tg.cau_tu_transcript(d_ngan)) == 1)


# ==================================================================
print("\n=== CA 9: MAY KHONG CO DEMUCS -> BAO LOI, KHONG am tham ra video hong ===")
# Do duoc: duong lui `nhe` de sot 86-100% loi goc -> video ra nghe CA giong cu
# lan giong moi. Tu lui = xuat video hong HANG LOAT ma khong ai biet.
# May nay CO demucs nen phai gia lap may nhan vien bang cach va `co_demucs`.
d9 = Path(T) / "ca9"
d9.mkdir(parents=True, exist_ok=True)
w9 = d9 / "stereo.wav"
ff(["-f", "lavfi", "-i", "sine=frequency=440:duration=2",
    "-f", "lavfi", "-i", "sine=frequency=660:duration=2",
    "-filter_complex", "[0:a][1:a]join=inputs=2:channel_layout=stereo[o]",
    "-map", "[o]", "-ar", "44100", "-c:a", "pcm_s16le", str(w9)])

_that_co_demucs = tg.co_demucs
try:
    tg.co_demucs = lambda: False          # gia lap may nhan vien
    try:
        tg.tach_giong(w9, d9 / "ra_auto", cach="auto")
        dat("auto + KHONG demucs -> phai NEM", False,
            "khong nem — dang am tham xuat video hong")
    except RuntimeError as e:
        dat("auto + KHONG demucs -> phai NEM", "Demucs" in str(e),
            "co noi ro thieu Demucs")

    # co y chap nhan thi VAN cho, nhung phai co dau canh bao
    k9 = tg.tach_giong(w9, d9 / "ra_nhe", cach="auto", cho_phep_nhe=True)
    dat("co_phep_nhe=True thi VAN chay duoc", bool(k9.get("nhac")))
    dat("ban lui phai mang DAU vi sao", bool(k9.get("lui_vi")),
        str(k9.get("lui_vi"))[:60])

    k9b = tg.tach_giong(w9, d9 / "ra_nhe2", cach="nhe")
    dat("ep cach='nhe' thi mang CANH BAO chat luong",
        bool(k9b.get("canh_bao")), str(k9b.get("canh_bao"))[:60])
finally:
    tg.co_demucs = _that_co_demucs

dat("may NAY co Demucs that (khong thi moi so do o tren vo nghia)",
    tg.co_demucs(), f"thiet bi: {tg.thiet_bi_tach()}")


# ==================================================================
print("\n" + "=" * 62)
print(f"ĐẠT {len(OK)} · HỎNG {len(FAIL)}")
for f in FAIL:
    print("  HỎNG:", f)
try:
    shutil.rmtree(T, ignore_errors=True)
except OSError:
    pass
sys.exit(1 if FAIL else 0)
