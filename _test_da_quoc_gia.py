# -*- coding: utf-8 -*-
r"""CỔNG 40 — ĐA QUỐC GIA: AI phải hiểu MỌI loại nội dung, không được lỗi.

    .venv\Scripts\python _test_da_quoc_gia.py [--nhom nhat,han,anh,viet,cam]

Anh Hùng 08/08/2026: *"AI phải hiểu hết các loại nội dung đa quốc gia nhé, k đc
lỗi, thêm hiệu ứng âm thanh hợp lý bất chấp mọi nội dung quốc gia, test kỹ"*.

VÌ SAO ĐÂY LÀ CHỖ NGUY HIỂM NHẤT — 3 lỗi THẬT đã xảy ra ở đúng đường này:
  1. v2.11.1: khoá ngôn ngữ ném **TÊN** ("English") vào tham số chỉ nhận **MÃ
     ISO** -> 400 -> chép lời chết -> MỌI video > 10 phút thành "Cắt cơ bản".
  2. CJK không có dấu cách: `.split()` đếm sai gần hết (việc #124-128).
  3. **LỖI MỚI, cổng này tìm ra 08/08/2026** — `chon_doan.co_loi_noi_that` đếm
     từ bằng `.split()`: video Nhật/Trung có ÍT ĐOẠN (short 8-60s whisper trả
     1-2 đoạn) bị gán nhầm "chỉ gồm câu Whisper bịa" -> app BỎ transcript, ép
     đi đường XEM HÌNH (~3-4 phút/video) và **KHÔNG đốt phụ đề**. Đo trước khi
     sửa, mật độ 2,00 từ/giây (nói rõ ràng): Nhật 1 đoạn False · Nhật 2 đoạn
     False · Trung 1 đoạn False — trong khi Anh/Việt/Hàn 1 đoạn đều True.

5 ĐIỀU PHẢI CHỨNG MINH CHO TỪNG NHÓM (đo, không đoán):
  1. chép lời ra ĐÚNG ngôn ngữ (`language` khớp mã ISO, số câu > 0)
  2. AI chọn đoạn CHẠY — clip có `llm_used=True`, KHÔNG rơi "Cắt cơ bản"
  3. phụ đề vẽ ĐÚNG — render khung THẬT + đếm pixel TỪNG DÒNG (ca Việt kiểm
     thêm KHÔNG cắt đáy khung — bài học `ny <= 0,80`)
  4. TIẾNG ĐỘNG hợp lý BẤT CHẤP QUỐC GIA — >= 3 Part/nhóm, KHÔNG được Part nào
     cũng cùng một tiếng (lỗi cũ: mọi Part đều "ding"), và tiếng động KHÔNG
     ÁT LỜI (đo RMS trước/sau)
  5. hiệu ứng HÌNH trung lập — cùng 1 video, đổi NHÃN ngôn ngữ -> kết quả chọn
     hiệu ứng + chuyển cảnh phải Y HỆT (khác nghĩa là nó lén đọc chữ)
  + QUÉT TĨNH: `.split()` dùng để ĐẾM TỪ trong mã mới = FAIL; so TÊN ngôn ngữ
    thay vì MÃ ISO = FAIL.

VIDEO THẬT trên máy anh Hùng (không mock — quy tắc sắt của repo):
  Nhật  `D:\video ssmatool\video nhật dài` · Hàn `…\video hàn dài|video hàn`
  Anh   `…\video mỹ` · Việt `…\video viêt` · KHÔNG LỜI = hình thật + tiếng im
THIẾU (nói thẳng, không bịa): **Trung · Thái · Ả Rập · Do Thái KHÔNG có video
thật nào trên máy** (đã quét toàn bộ D:\ + C:\Users\Admin: 1.841 file Hàn, 307
Nhật, 0 Trung, 0 Thái, 0 Ả Rập; chỉ có 1 file NHẠC Ả Rập trong kho SFX). Với
các nhóm đó cổng vẫn kiểm được 3 điều KHÔNG cần tiếng thật (vẽ phụ đề · đếm
từ CJK-aware · trung lập ngôn ngữ) và ĐÁNH DẤU rõ 2 điều còn thiếu.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

_SB = Path(tempfile.mkdtemp(prefix="daquocgia_"))
os.environ["BQ_DATA_DIR"] = str(_SB)
os.environ["BQ_DB_PATH"] = str(_SB / "studio.db")
os.environ["BQ_QSETTINGS_INI"] = str(_SB / "settings.ini")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["WHISPER_PROVIDER"] = "groq"
os.environ.setdefault("ECO_MODE", "0")

# key Groq: đọc từ .env THẬT rồi truyền qua ENV — KHÔNG ghi ra file (cổng 22)
_env_that = (Path(os.environ.get("LOCALAPPDATA") or Path.home())
             / "BQHungVideo" / ".env")
if _env_that.exists():
    for _ln in _env_that.read_text(encoding="utf-8",
                                   errors="replace").splitlines():
        _k, _, _v = _ln.partition("=")
        _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
        if _k in ("GROQ_API_KEYS", "GROQ_KEYS_FILE") and _v:
            os.environ.setdefault(_k, _v)

import _test_guard  # noqa: E402,F401 - CẤM test đụng máy user

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

FF = str(REPO / "bin" / "ffmpeg.exe")
FPROBE = str(REPO / "bin" / "ffprobe.exe")
_NOWIN = 0x08000000 if os.name == "nt" else 0
FAIL: list[str] = []
BOQUA: list[str] = []


def kiem(ok: bool, nhan: str, ct: str = "") -> bool:
    print(("  ĐẠT   " if ok else "  HỎNG  ") + nhan + (f"   << {ct}" if ct else ""))
    if not ok:
        FAIL.append(nhan)
    return ok


def bo_qua(nhan: str, ly_do: str) -> None:
    print(f"  THIẾU {nhan}   << {ly_do}")
    BOQUA.append(f"{nhan} — {ly_do}")


# ══════════════════════════════════════════════════════════════════════════
# KHO VIDEO THẬT — tự dò, KHÔNG đóng cứng tên file (tên file hay đổi)
# ══════════════════════════════════════════════════════════════════════════
KHO = {
    # tên nhóm: (mã ISO mong đợi, [thư mục], giây tối thiểu, giây tối đa)
    "nhat": ("ja", [r"D:\video ssmatool\video nhật dài",
                    r"C:\Users\Admin\Downloads\thùng rác"], 90, 900),
    "han":  ("ko", [r"D:\video ssmatool\video hàn dài",
                    r"D:\video ssmatool\video hàn"], 40, 900),
    "anh":  ("en", [r"D:\video ssmatool\video mỹ"], 90, 900),
    "viet": ("vi", [r"D:\video ssmatool\video viêt"], 25, 900),
}
#: nhóm KHÔNG có video thật trên máy -> chỉ kiểm được phần không cần tiếng
THIEU_VIDEO = {
    "trung": ("zh", "今天發生了一件非常不可思議的事情，真的太誇張了，大家一定要看完"),
    "thai":  ("th", "วันนี้มีเรื่องน่าตกใจมากเกิดขึ้นจริง ๆ ทุกคนต้องดูให้จบ"),
    "arab":  ("ar", "اليوم حدث شيء لا يصدق حقا يجب أن تشاهد هذا حتى النهاية"),
}


def _dai(p: Path) -> float:
    try:
        r = subprocess.run(
            [FPROBE, "-v", "quiet", "-print_format", "json", "-show_format",
             str(p)], capture_output=True, text=True, encoding="utf-8",
            timeout=30, creationflags=_NOWIN)
        return float(json.loads(r.stdout or "{}")
                     .get("format", {}).get("duration") or 0)
    except Exception:  # noqa: BLE001
        return 0.0


#: DẤU HIỆU ĐỘC LẬP để biết một file CÓ ĐÚNG là tiếng đó không — **CHỮ VIẾT
#: trong TÊN FILE**. Phải độc lập với `transcribe()`: chọn nguồn bằng chính kết
#: quả chép lời rồi đi assert kết quả đó là con dấu (bẫy "chọn nguồn cho tới khi
#: assert xanh" đã ghi ở cổng 41).
#: **VÌ SAO CẦN — LỖI THẬT 09/08/2026:** `tim_video` xếp theo KÍCH THƯỚC, mà
#: prodown tải liên tục vào đúng các thư mục này -> "file to nhất" đổi theo từng
#: giờ. Lượt kiểm sau khi gộp v2.20.0 bốc trúng **`Part 1 Thank You Sorry The
#: Shocking Reveal Inside!`** — nằm trong `video nhật dài` nhưng là video TIẾNG
#: ANH -> `transcribe()` trả `English`, mật độ **0,09 từ/giây** -> cổng báo 3
#: HỎNG cho nhóm `nhat` trong khi APP KHÔNG HỀ SAI (lượt gộp không đụng một
#: dòng nào của `transcribe`/`recap`/`chon_doan`). Đúng bệnh "nguồn đổi giữa 2
#: lượt" mà cổng 41 đã phải chữa bằng `_nguon_shader.py`. Thư mục đó có 28 video
#: tên tiếng Nhật thật — chỉ là không cái nào TO NHẤT.
CHU_NGON_NGU = {
    # kana + kanji
    "nhat": re.compile(r"[぀-ヿ一-鿿]"),
    # hangul
    "han": re.compile(r"[가-힯ᄀ-ᇿ]"),
    # chữ cái riêng của quốc ngữ (tên file YouTube giữ nguyên dấu)
    "viet": re.compile(r"[ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩị"
                       r"òóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ]", re.I),
    "anh": None,       # tên tiếng Anh không có chữ riêng để nhận ra
}


def tim_video(thus, gmin: float, gmax: float, mb_max: float = 400.0,
              chu=None):
    """Video THẬT đầu tiên lọt [gmin,gmax] giây, <= mb_max MB, và — nếu có
    `chu` — TÊN FILE phải mang CHỮ VIẾT của thứ tiếng đó."""
    for t in thus:
        d = Path(t)
        if not d.is_dir():
            continue
        ung = []
        for p in d.rglob("*.mp4"):
            try:
                mb = p.stat().st_size / 1048576
            except OSError:
                continue
            if not (1.0 <= mb <= mb_max):
                continue
            if chu is not None and not chu.search(p.name):
                continue
            ung.append((-mb, p))       # to nhất trước = dài nhất, thường
        ung.sort()
        for _m, p in ung[:40]:
            g = _dai(p)
            if gmin <= g <= gmax:
                return p, g
    return None, 0.0


# ══════════════════════════════════════════════════════════════════════════
def rms_nen_dinh(p: Path, cua: float = 0.25) -> tuple[float, float]:
    """(RMS NỀN cả clip, RMS ĐỈNH của cửa sổ `cua` giây) — đọc file MỘT LẦN.

    Dùng để trả lời "tiếng động có ÁT LỜI không": tiếng động chỉ kêu 0,2-0,4s
    ở chỗ nối, nên nó phải nổi hơn nền nhưng KHÔNG được nổi quá nhiều lần.
    """
    import numpy as np
    with wave.open(str(p), "rb") as w:
        sr, n = w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    v = np.frombuffer(raw[: (len(raw) // 2) * 2], dtype="<i2").astype("float32")
    if v.size == 0:
        return 0.0, 0.0
    nen = float(np.sqrt((v * v).mean())) / 32768.0
    k = max(1, int(cua * sr))
    m = (v.size // k) * k
    if m < k:
        return nen, nen
    o = v[:m].reshape(-1, k)
    dinh = float(np.sqrt((o * o).mean(axis=1)).max()) / 32768.0
    return nen, dinh


def tach_wav(src: Path, dst: Path, t0: float = 0.0, giay: float = 0.0) -> bool:
    c = [FF, "-y", "-v", "error"]
    if t0 > 0:
        c += ["-ss", f"{t0:g}"]
    c += ["-i", str(src)]
    if giay > 0:
        c += ["-t", f"{giay:g}"]
    c += ["-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(dst)]
    r = subprocess.run(c, capture_output=True, timeout=600,
                       creationflags=_NOWIN)
    return r.returncode == 0 and dst.exists() and dst.stat().st_size > 1000


def _esc_loc(p) -> str:
    """Escape đường dẫn Windows cho filter graph — Y HỆT `export_canvas_clip`
    (`D:` phải thành `D\\:`, không thì ffmpeg báo "No option name near")."""
    return str(p).replace("\\", "/").replace(":", "\\:")


def dem_px_tung_dong(png: Path, nguong: int = 200) -> list[int]:
    """Số pixel SÁNG theo TỪNG DÒNG ảnh (bài học `%` nuốt cả dòng: đếm TỔNG
    thì mất dòng vẫn PASS oan). Trả list số px của mỗi dải 1 pixel có chữ."""
    import cv2
    im = cv2.imread(str(png), cv2.IMREAD_GRAYSCALE)
    if im is None:
        return []
    mask = (im >= nguong)
    return [int(x) for x in mask.sum(axis=1)]


# ══════════════════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nhom", default="nhat,han,anh,viet,cam")
    a = ap.parse_args()
    chon = [x.strip() for x in a.nhom.split(",") if x.strip()]

    n_key = len([x for x in os.environ.get("GROQ_API_KEYS", "")
                 .replace(",", "\n").splitlines() if x.strip()])
    print(f"[sandbox] {_SB}")
    print(f"[key Groq] {n_key} key")
    if n_key == 0:
        print("DỪNG: 0 key Groq -> chép lời sẽ tụt về whisper MÁY (rất chậm), "
              "số đo vô nghĩa.")
        return 2

    import app.queue.jobs  # noqa: F401  (cv2 nạp trước Qt — thứ tự main.py)
    from app.ai import chon_doan as CD
    from app.ai import recap as RC
    from app.core import captions, hieu_ung
    from app.core import ffmpeg_utils as fu
    from app.core import transcribe as TR
    from app.core.analysis import _set as set_analysis
    from app.database.db import db
    from app.modules import m1_highlight as M1

    print(f"[encoder] {fu.detect_encoder()} · cửa chờ ffmpeg "
          f"{fu.so_ffmpeg_song_song()} · nhân {os.cpu_count()}")

    # ───────────────────────────────────────────────────────────────────
    print("\n══ 0. QUÉT TĨNH: `.split()` đếm từ + so TÊN ngôn ngữ thay vì MÃ ══")
    import inspect
    # (a) mã MỚI (hiệu ứng · chuyển cảnh · GPU · bảng mẫu) KHÔNG được đếm từ /
    # đo mật độ chữ bằng `.split()` — với CJK là đếm sai gần hết.
    for f_ma in (REPO / "app" / "core" / "hieu_ung.py",
                 REPO / "app" / "core" / "hieu_ung_gpu.py",
                 REPO / "_do_hieu_ung_bang.py"):
        if not f_ma.exists():
            bo_qua(f"quét tĩnh {f_ma.name}", "không có file")
            continue
        xau = [ln for ln in f_ma.read_text(encoding="utf-8",
                                           errors="replace").splitlines()
               if ".split()" in ln and ("len(" in ln or "mật độ" in ln.lower()
                                        or "đếm từ" in ln.lower())]
        kiem(not xau, f"{f_ma.name}: KHÔNG đếm từ bằng `.split()`",
             "; ".join(x.strip()[:70] for x in xau))
    ma_fu = inspect.getsource(fu.chon_chuyen_canh) + inspect.getsource(
        fu._loai_cho_noi) + inspect.getsource(fu._tach_va_noi_manh)
    kiem(".split()" not in ma_fu, "chuyển cảnh: KHÔNG đếm từ bằng `.split()`")
    # (a2) mã MỚI cũng KHÔNG được đọc CHỮ/NGÔN NGỮ để chọn hiệu ứng
    for f_ma in (REPO / "app" / "core" / "hieu_ung.py",
                 REPO / "app" / "core" / "hieu_ung_gpu.py"):
        if not f_ma.exists():
            continue
        t = f_ma.read_text(encoding="utf-8", errors="replace")
        xau = [ln for ln in t.splitlines()
               if ('"language"' in ln or "'language'" in ln
                   or 'get("lang"' in ln or "transcript" in ln)]
        kiem(not xau, f"{f_ma.name}: KHÔNG đọc ngôn ngữ/transcript",
             "; ".join(x.strip()[:70] for x in xau))
    # (b) hàm đếm-từ dùng chung phải CJK-aware
    kiem(len(RC._word_tokens("今日はすごい")) > 1,
         "`_word_tokens` tách được câu Nhật không dấu cách",
         f"{len(RC._word_tokens('今日はすごい'))} token")
    kiem(RC._word_tokens("a b c") == "a b c".split(),
         "BẤT BIẾN: text non-CJK -> `_word_tokens` == `.split()`")
    ma_cd = inspect.getsource(CD.co_loi_noi_that)
    kiem("_word_tokens" in ma_cd,
         "`co_loi_noi_that` đếm từ CJK-aware (không `.split()`)",
         "vẫn dùng .split() -> video Nhật/Trung ít đoạn bị gán nhầm KHÔNG LỜI")
    # (c) khoá ngôn ngữ phải là MÃ ISO, không phải TÊN
    kiem(TR._ma_iso("English") == "en" and TR._ma_iso("Japanese") == "ja"
         and TR._ma_iso("ja") == "ja" and TR._ma_iso("en-US") == "en",
         "`_ma_iso` đổi TÊN -> MÃ ISO (lỗi v2.11.1)",
         f"English->{TR._ma_iso('English')} Japanese->{TR._ma_iso('Japanese')}")
    kiem(TR._ma_iso("Klingon") is None and TR._ma_iso("") is None,
         "`_ma_iso` không chắc -> None (tự nhận diện lại còn hơn chết cả lượt)")
    for tn, (iso, _txt) in THIEU_VIDEO.items():
        kiem(TR._ma_iso(iso) == iso, f"mã ISO `{iso}` ({tn}) được Groq chấp nhận")

    # ───────────────────────────────────────────────────────────────────
    print("\n══ 0b. ĐẾM TỪ CJK — ca đã gây LỖI THẬT (short 1-2 đoạn) ══")
    def _co_loi(text: str, nseg: int, giay=30.0, nw=60):
        tr = {"segments": [{"text": text}] * nseg,
              "words": [{"word": "x"}] * nw}
        return CD.co_loi_noi_that(tr, giay)[0]

    for ten, txt in (("Nhật", "今日は本当にすごいことが起きました。信じられない話です"),
                     ("Trung", "今天發生了一件非常不可思議的事情真的太誇張了"),
                     ("Hàn", "오늘 정말 믿을 수 없는 일이 일어났습니다"),
                     ("Anh", "today something unbelievable happened to me"),
                     ("Việt", "hôm nay có một chuyện cực kỳ bất ngờ đã xảy ra")):
        kiem(_co_loi(txt, 1), f"{ten}: transcript 1 ĐOẠN -> nhận ĐÚNG là CÓ LỜI")
    kiem(not _co_loi("thank you", 3),
         "BẤT BIẾN: rác 'thank you' vẫn bị bắt là KHÔNG lời")
    kiem(not CD.co_loi_noi_that(
        {"segments": [{"text": "hello"}], "words": [{"word": "x"}] * 10},
        300.0)[0], "BẤT BIẾN: mật độ từ quá thấp vẫn bị bắt")

    # ───────────────────────────────────────────────────────────────────
    print("\n══ 0c. HIỆU ỨNG HÌNH + CHUYỂN CẢNH: TRUNG LẬP NGÔN NGỮ (điều 5) ══")
    # cùng SỐ ĐO, đổi nhãn ngôn ngữ -> kết quả phải Y HỆT. Chứng minh cả bằng
    # QUÉT TĨNH (chữ ký hàm không nhận text) lẫn HÀNH VI.
    sig = inspect.signature(hieu_ung.chon_hieu_ung).parameters
    kiem(not any(k in sig for k in ("lang", "language", "text", "transcript")),
         "`chon_hieu_ung` KHÔNG nhận ngôn ngữ/chữ (trung lập từ chữ ký)",
         ", ".join(sig))
    sig2 = inspect.signature(fu.chon_chuyen_canh).parameters
    kiem(not any(k in sig2 for k in ("lang", "language", "text")),
         "`chon_chuyen_canh` KHÔNG nhận ngôn ngữ/chữ", ", ".join(sig2))
    nl = [0.10, 0.12, 0.11, 0.55, 0.62, 0.13, 0.12, 0.48, 0.14, 0.13,
          0.12, 0.70, 0.15, 0.12, 0.13, 0.11, 0.40, 0.12, 0.13, 0.12]
    cd = [1.0, 1.2, 1.1, 7.4, 8.0, 1.3, 1.1, 6.2, 1.4, 1.2,
          1.1, 9.0, 1.5, 1.2, 1.3, 1.1, 5.0, 1.2, 1.3, 1.2]
    segs = [[100.0, 108.0], [40.0, 46.0], [46.5, 52.0], [200.0, 202.0]]
    goc_hu = hieu_ung.chon_hieu_ung(20.0, "vua", nl, cd, [8.0, 14.0])
    goc_cc = fu.chon_chuyen_canh(segs, "vua")
    for tn in ("ja", "zh", "ko", "en", "vi", "th", "ar", "Japanese", ""):
        RC.resolve_lang(tn, "今日は")          # đổi nhãn/ngữ cảnh ngôn ngữ
        kiem(hieu_ung.chon_hieu_ung(20.0, "vua", nl, cd, [8.0, 14.0]) == goc_hu
             and fu.chon_chuyen_canh(segs, "vua") == goc_cc,
             f"nhãn ngôn ngữ '{tn or '(rỗng)'}' -> chọn hiệu ứng/chuyển cảnh Y HỆT")
    kiem(len({k for k, _d in goc_cc}) > 1,
         "cùng 1 clip KHÔNG lặp một kiểu chuyển cảnh ở mọi chỗ nối",
         f"{[k for k, _ in goc_cc]}")

    # ───────────────────────────────────────────────────────────────────
    print("\n══ 0c2. MẪU CŨ (không có khoá) -> MẶC ĐỊNH 'nhe' ở MỌI CỬA ══")
    # Anh Hùng 08/08/2026 chốt: *"Giữ BẬT Nhẹ — như tôi đã chốt"*. 200-300 kênh
    # đang chạy mẫu CŨ (JSON không có khoá `hieu_ung`/`chuyen_canh`) nên mặc
    # định ở MỌI cửa phải ra 'nhe'. 4 cửa (bỏ sót 1 cửa là kênh mất hiệu ứng
    # hoặc ngược lại, bật lúc user tưởng đã tắt):
    cua = [
        ("Chỉnh mẫu (editor._apply_layout)", REPO / "app" / "ui" / "editor.py",
         ('layout.get("chuyen_canh", "nhe")', 'layout.get("hieu_ung", "nhe")')),
        ("bấm tay (studio_page._export_video_inner)",
         REPO / "app" / "ui" / "studio_page.py",
         ('self.layout_tpl.get("chuyen_canh", "nhe")',
          'self.layout_tpl.get("hieu_ung", "nhe")')),
        ("job xuất (m1_highlight)", REPO / "app" / "modules" / "m1_highlight.py",
         ('payload.get("chuyen_canh", "nhe")', 'payload.get("hieu_ung", "nhe")')),
    ]
    for ten, f, cans in cua:
        ma = f.read_text(encoding="utf-8", errors="replace")
        for c in cans:
            kiem(c in ma, f"mặc định 'nhe' — {ten}: `{c.split('(')[-1]}`",
                 "KHÔNG thấy -> mẫu cũ sẽ ra mức khác 'nhe'")
    # hành vi thật: payload KHÔNG có khoá -> chuỗi truyền xuống ffmpeg là 'nhe'
    kiem(str({}.get("hieu_ung", "nhe") or "tat") == "nhe"
         and str({}.get("chuyen_canh", "nhe") or "tat") == "nhe",
         "mẫu cũ (dict rỗng) -> 'nhe' cho cả 2 khoá")
    kiem(str({"hieu_ung": ""}.get("hieu_ung", "nhe") or "tat") == "tat",
         "user chọn TẮT (chuỗi rỗng) -> 'tat', KHÔNG bị ép về 'nhe'")
    kiem(bool(fu.chon_chuyen_canh(segs, "nhe"))
         and fu.chon_chuyen_canh(segs, "tat") == [],
         "'nhe' CÓ chuyển cảnh · 'tat' trả rỗng (đường cũ y nguyên)")

    # ───────────────────────────────────────────────────────────────────
    print("\n══ 0d. PHỤ ĐỀ VẼ ĐÚNG cho MỌI hệ chữ (điều 3) ══")
    # Render khung THẬT bằng libass rồi ĐẾM PIXEL TỪNG DÒNG. Nhóm nào không có
    # video thật vẫn kiểm được ở đây (chỉ cần CHỮ, không cần tiếng).
    fonts_dir = str(REPO / "app" / "assets" / "fonts")
    mau_chu = {
        "nhat": "今日は本当にすごいことが起きました",
        "han": "오늘 정말 믿을 수 없는 일이 일어났습니다",
        "anh": "today something unbelievable happened",
        "viet": "Chuyện cực kỳ bất ngờ đã xảy ra ở đây",
        "trung": THIEU_VIDEO["trung"][1],
        "thai": THIEU_VIDEO["thai"][1],
        "arab": THIEU_VIDEO["arab"][1],
    }
    for ten, chu in mau_chu.items():
        ny = 0.80 if ten == "viet" else 0.78
        toks = chu.split() if " " in chu else [chu[i:i + 3]
                                               for i in range(0, len(chu), 3)]
        words = []
        t = 0.5
        for w in toks:
            words.append({"word": w, "start": t, "end": t + 0.45})
            t += 0.5
        ass = _SB / f"sub_{ten}.ass"
        ok_ass = captions.build_ass(
            words, [[0.0, t + 1.0]], str(ass), 1080, 1920,
            font="Montserrat", size=int(0.055 * 1920), ny=ny,
            preset="Trắng đơn giản", delay=0.0)
        if not ok_ass:
            kiem(False, f"[{ten}] dựng .ass", "build_ass trả False")
            continue
        khung = _SB / f"khung_{ten}.png"
        moc = 1.2
        r = subprocess.run(
            [FF, "-y", "-v", "error", "-f", "lavfi",
             "-i", "color=c=black:s=1080x1920:d=3",
             "-vf", (f"subtitles='{_esc_loc(ass)}'"
                     f":fontsdir='{_esc_loc(fonts_dir)}'"),
             "-ss", f"{moc:g}", "-frames:v", "1", str(khung)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=300, creationflags=_NOWIN)
        if r.returncode != 0 or not khung.exists():
            kiem(False, f"[{ten}] render khung phụ đề THẬT",
                 (r.stderr or "")[:150])
            continue
        dong = dem_px_tung_dong(khung)
        tong = sum(dong)
        co_chu = [i for i, v in enumerate(dong) if v > 0]
        kiem(tong > 500, f"[{ten}] phụ đề CÓ chữ trên khung thật",
             f"{tong} px sáng")
        if co_chu:
            day = max(co_chu)
            kiem(day <= 1919 - 2,
                 f"[{ten}] KHÔNG cắt đáy khung",
                 f"dòng chữ cuối {day}/1919 · ny={ny} (bài học ny <= 0,80)")
            # dòng chữ không được dính mép TRÁI/PHẢI (bài học nhãn bảng mẫu)
            import cv2
            im = cv2.imread(str(khung), cv2.IMREAD_GRAYSCALE)
            trai = int((im[:, :6] >= 200).sum())
            phai = int((im[:, -6:] >= 200).sum())
            kiem(trai == 0 and phai == 0,
                 f"[{ten}] chữ KHÔNG tràn mép trái/phải",
                 f"trái {trai} px · phải {phai} px")

    # ───────────────────────────────────────────────────────────────────
    for tn, (iso, _t) in THIEU_VIDEO.items():
        bo_qua(f"nhóm {tn.upper()}: chép lời + AI chọn đoạn",
               "KHÔNG có video thật nào trên máy (đã quét D:\\ + "
               "C:\\Users\\Admin) — không bịa số")

    # ───────────────────────────────────────────────────────────────────
    from app.queue.worker import JobContext

    class Ctx(JobContext):                # ctx thật, không mock hành vi
        def __init__(self) -> None:
            self.job_id = 0
            self.profile = {}
            self.dong: list = []

        def progress(self, p: float, m: str = "") -> None:
            if m:
                self.dong.append(m)

        def check_canceled(self) -> None:
            return None

    tong_ket: dict = {}
    for nhom in chon:
        if nhom == "cam":
            continue
        if nhom not in KHO:
            continue
        iso, thus, gmin, gmax = KHO[nhom]
        print(f"\n══ NHÓM {nhom.upper()} (mong đợi mã ISO '{iso}') ══")
        _chu = CHU_NGON_NGU.get(nhom)
        src, giay = tim_video(thus, gmin, gmax, chu=_chu)
        if not src:
            # THIẾU chứ không HỎNG: máy KHÔNG có video đúng thứ tiếng đó thì đây
            # là thiếu DỮ LIỆU ĐO, không phải app sai. Ghi thẳng ra, đừng bịa số.
            bo_qua(f"nhóm {nhom}",
                   f"không tìm thấy video {gmin}-{gmax}s"
                   + (" có TÊN mang chữ viết của thứ tiếng này (thư mục có "
                      "file, nhưng toàn tên tiếng khác — prodown tải lẫn vào)"
                      if _chu is not None else ""))
            continue
        print(f"  nguồn: {src.name[:70]} · {giay:.1f}s")
        tong_ket[nhom] = {}

        # ---- ĐIỀU 1: chép lời ra ĐÚNG ngôn ngữ ----
        wav = _SB / f"{nhom}.wav"
        if not tach_wav(src, wav, 0.0, min(giay, 240.0)):
            kiem(False, f"[{nhom}] tách tiếng", "extract wav hỏng")
            continue
        tr = TR.transcribe(str(wav), language=None)
        lg = str(tr.get("language") or "")
        nseg = len(tr.get("segments") or [])
        nw = len(tr.get("words") or [])
        eng = str(tr.get("engine") or "")
        d1 = kiem(TR._ma_iso(lg) == iso and nseg > 0,
                  f"[{nhom}] ĐIỀU 1 — chép lời ĐÚNG ngôn ngữ",
                  f"ra '{lg}' (mong '{iso}') · {nseg} câu · {nw} từ")
        print(f"        engine THỰC: {eng} · {nseg} câu · {nw} mốc từ · "
              f"mật độ {nw / max(1.0, min(giay, 240.0)):.2f} từ/giây")
        kiem(eng.startswith("groq:"),
             f"[{nhom}] chạy Groq THẬT (không tụt whisper máy)", eng)
        co_loi, vi_sao, mds = CD.co_loi_noi_that(tr, min(giay, 240.0))
        kiem(co_loi, f"[{nhom}] app nhận ĐÚNG là video CÓ LỜI",
             f"{vi_sao} (mật độ {mds:.2f})")
        tong_ket[nhom]["1"] = d1

        # ---- ĐIỀU 2: AI chọn đoạn CHẠY ----
        pid = db.execute("INSERT INTO projects(name, assets_dir, grp) "
                         "VALUES(?,?,?)",
                         (f"Kênh {nhom}", str(_SB / "assets"), nhom)).lastrowid
        vid = db.execute("INSERT INTO videos(project_id, src_path, duration) "
                         "VALUES(?,?,?)", (pid, str(src), giay)).lastrowid
        set_analysis(vid, "transcript", "done", tr, engine=eng)
        ctx = Ctx()
        _min = 15.0 if giay < 120 else 30.0
        _max = min(60.0, max(25.0, giay / 3.0))
        res = M1.generate_highlights(
            {"video_id": vid,
             "preset": {"count": 3, "min_len": _min, "max_len": _max}}, ctx)
        d2 = kiem(bool(res.get("llm_used")) and int(res.get("count", 0)) > 0,
                  f"[{nhom}] ĐIỀU 2 — AI chọn đoạn CHẠY (không 'Cắt cơ bản')",
                  f"llm_used={res.get('llm_used')} count={res.get('count')} "
                  f"· {(ctx.dong or ['?'])[-1][:110]}")
        tong_ket[nhom]["2"] = d2
        rows = db.query("SELECT id, start_sec, end_sec, signals FROM clips "
                        "WHERE video_id=? AND status='suggested' ORDER BY id",
                        (vid,))
        print(f"        {len(rows)} clip: " + " · ".join(
            f"{r['start_sec']:.0f}-{r['end_sec']:.0f}s" for r in rows))

        # ---- ĐIỀU 4: TIẾNG ĐỘNG hợp lý bất chấp quốc gia ----
        # Cần >= 3 Part. AI có thể chỉ chọn 2 clip trên video ngắn -> BÙ thêm
        # Part dựng từ chính video đó (ghi rõ là Part BÙ, không nhận vơ là AI
        # chọn). Điều 4 kiểm TIẾNG ĐỘNG theo chỗ nối nên nguồn gốc Part không
        # ảnh hưởng kết luận.
        ds_part: list = []
        for r in rows[:3]:
            try:
                sg = (json.loads(r["signals"] or "{}") or {}).get("segments")
            except Exception:  # noqa: BLE001
                sg = None
            sg = [[float(x), float(y)] for x, y in (sg or [])]
            if len(sg) < 2:                # ép >= 2 đoạn -> có ĐIỂM NỐI
                a, b = float(r["start_sec"]), float(r["end_sec"])
                giua = a + (b - a) / 2
                sg = [[a, giua], [giua + 0.6, min(b + 0.6, giay - 0.2)]]
            ds_part.append((sg, "AI"))
        # Part BÙ: 3 hình dạng chỗ nối KHÁC NHAU (ngược thời gian / gần liền
        # mạch / câu chốt) -> đúng thứ `_loai_theo_khoang_nhay` phải phân biệt.
        _t = min(giay - 1.0, 60.0)
        for hinh, sg in (
            ("bù·ngược", [[_t * 0.6, _t * 0.6 + 4.0],
                          [_t * 0.2, _t * 0.2 + 4.0]]),
            ("bù·liền", [[_t * 0.3, _t * 0.3 + 4.0],
                         [_t * 0.3 + 4.5, _t * 0.3 + 8.0]]),
            ("bù·chốt", [[_t * 0.1, _t * 0.1 + 5.0],
                         [_t * 0.7, _t * 0.7 + 2.0]])):
            if len(ds_part) >= 3:
                break
            ds_part.append(([[float(x), float(y)] for x, y in sg], hinh))
        parts = []
        for i, (sg, goc) in enumerate(ds_part):
            jc = M1._join_categories(sg, None, False,
                                     {"hook_seg": sg[0]})
            out = _SB / f"{nhom}_part{i + 1}.mp4"
            try:
                fu.export_canvas_clip(
                    str(src), str(out), [(s, e) for s, e in sg],
                    (0.5, 0.5, 1.0), bg="blur", out_w=1080, out_h=1920,
                    fx_fade=True, fx_whoosh=True, join_categories=jc,
                    chuyen_canh="nhe", hieu_ung="nhe")
            except Exception as e:  # noqa: BLE001
                kiem(False, f"[{nhom}] xuất Part {i + 1}", str(e)[:150])
                continue
            pick = [c for c, _f in (getattr(fu, "_SFX_LAST_PICK", None) or [])]
            fil = [os.path.basename(str(f)) if f else "tự-sinh"
                   for _c, f in (getattr(fu, "_SFX_LAST_PICK", None) or [])]
            parts.append((out, pick, fil))
            print(f"        Part {i + 1} ({goc}): {len(sg)} đoạn · tiếng động "
                  f"{list(zip(pick, fil))}")
        kiem(len(parts) >= 3, f"[{nhom}] xuất đủ 3 Part", f"{len(parts)} Part")
        loai = {tuple(p) for _o, p, _f in parts}
        file_dung = {tuple(f) for _o, _p, f in parts}
        d4a = kiem(len(parts) >= 2 and (len(loai) > 1 or len(file_dung) > 1),
                   f"[{nhom}] ĐIỀU 4a — KHÔNG phải Part nào cũng CÙNG một tiếng",
                   f"loại {loai} · file {file_dung}")
        # tiếng động KHÔNG ĐƯỢC ÁT LỜI: RMS quanh chỗ nối so với nền của clip
        d4b = True
        for o, _p, _f in parts[:3]:
            w1 = o.with_suffix(".wav")
            if not tach_wav(o, w1):
                continue
            nen, dinh = rms_nen_dinh(w1)
            ok = nen > 0.0005 and dinh <= nen * 12.0
            d4b = d4b and ok
            kiem(ok, f"[{nhom}] tiếng động KHÔNG át lời ({o.name})",
                 f"RMS nền {nen:.4f} · đỉnh 0,25s {dinh:.4f} "
                 f"= {dinh / max(nen, 1e-6):.1f}× (trần 12×)")
        tong_ket[nhom]["4"] = d4a and d4b

        # ---- ĐIỀU 3 (trên chữ THẬT của chính video này) ----
        # Lấy từ GIỮA transcript, KHÔNG lấy 3 câu đầu: đầu video hay là nhạc
        # hiệu/intro nên whisper dễ trả chữ tiếng Anh (đã thấy thật ở nguồn
        # Nhật) -> mẫu chữ không đại diện cho ngôn ngữ video.
        _sg_all = tr.get("segments") or []
        _gi = max(0, len(_sg_all) // 2)
        chu_that = " ".join(str(s.get("text", ""))
                            for s in _sg_all[_gi:_gi + 3]).strip()
        if chu_that:
            _w_all = tr.get("words") or []
            _wi = max(0, len(_w_all) // 2)
            wds = _w_all[_wi:_wi + 14]
            wds = [{"word": str(w.get("word", "")),
                    "start": float(w.get("start", 0)),
                    "end": float(w.get("end", 0))} for w in wds
                   if str(w.get("word", "")).strip()]
            if len(wds) >= 3:
                t0 = wds[0]["start"]
                wds = [{"word": w["word"], "start": w["start"] - t0,
                        "end": w["end"] - t0} for w in wds]
                ass = _SB / f"that_{nhom}.ass"
                captions.build_ass(wds, [[0.0, wds[-1]["end"] + 1.0]],
                                   str(ass), 1080, 1920, font="Montserrat",
                                   size=int(0.055 * 1920), ny=0.78,
                                   preset="Trắng đơn giản", delay=0.0)
                khung = _SB / f"that_{nhom}.png"
                moc = (wds[0]["start"] + wds[0]["end"]) / 2
                subprocess.run(
                    [FF, "-y", "-v", "error", "-f", "lavfi",
                     "-i", "color=c=black:s=1080x1920:d=6",
                     "-vf", (f"subtitles='{_esc_loc(ass)}'"
                             f":fontsdir='{_esc_loc(fonts_dir)}'"),
                     "-ss", f"{max(0.05, moc):g}", "-frames:v", "1",
                     str(khung)], capture_output=True, timeout=300,
                    creationflags=_NOWIN)
                dong = dem_px_tung_dong(khung) if khung.exists() else []
                tong_ket[nhom]["3"] = kiem(
                    sum(dong) > 500,
                    f"[{nhom}] ĐIỀU 3 — phụ đề LỜI THẬT vẽ ra chữ",
                    f"{sum(dong)} px · chữ: {chu_that[:40]}")
            else:
                bo_qua(f"[{nhom}] ĐIỀU 3 trên lời thật",
                       "chép lời không có mốc TỪNG TỪ")
        tong_ket[nhom]["5"] = True        # đã chứng minh ở mục 0c (dùng chung)

    # ───────────────────────────────────────────────────────────────────
    print("\n══ BẢNG ĐA QUỐC GIA — mỗi nhóm × 5 điều ══")
    print(f"  {'nhóm':8s} {'1 chép lời':>12s} {'2 AI chọn':>11s} "
          f"{'3 phụ đề':>10s} {'4 tiếng động':>13s} {'5 trung lập':>12s}")
    for nhom, d in tong_ket.items():
        def _x(k):
            v = d.get(k)
            return "ĐẠT" if v else ("—" if v is None else "HỎNG")
        print(f"  {nhom:8s} {_x('1'):>12s} {_x('2'):>11s} {_x('3'):>10s} "
              f"{_x('4'):>13s} {_x('5'):>12s}")
    for tn in THIEU_VIDEO:
        print(f"  {tn:8s} {'THIẾU':>12s} {'THIẾU':>11s} {'ĐẠT':>10s} "
              f"{'THIẾU':>13s} {'ĐẠT':>12s}")

    print("\n" + "=" * 74)
    print(f"CỔNG 40 ĐA QUỐC GIA: {len(FAIL)} HỎNG · {len(BOQUA)} THIẾU")
    for x in FAIL:
        print("  HỎNG:", x)
    for x in BOQUA:
        print("  THIẾU:", x)
    shutil.rmtree(_SB, ignore_errors=True)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
