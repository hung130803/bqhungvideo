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

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = str(Path(__file__).resolve().parent)   # KHÔNG ghi cứng đường repo
sys.path.insert(0, REPO)

T = tempfile.mkdtemp(prefix="tg_gate_")
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


def ff(args: list[str]) -> int:
    r = subprocess.run([settings.FFMPEG_PATH, "-y", "-hide_banner",
                        "-loglevel", "error", *args],
                       capture_output=True, text=True)
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
dat("dat DUNG moc dau (lech 0 ms)", kh["lech_dau_ms_max"] == 0.0,
    f"{kh['lech_dau_ms_max']} ms")
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
print("\n" + "=" * 62)
print(f"ĐẠT {len(OK)} · HỎNG {len(FAIL)}")
for f in FAIL:
    print("  HỎNG:", f)
try:
    shutil.rmtree(T, ignore_errors=True)
except OSError:
    pass
sys.exit(1 if FAIL else 0)
