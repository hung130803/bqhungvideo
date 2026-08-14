# -*- coding: utf-8 -*-
r"""ĐO TIẾNG TRUNG — 5 phép kiểm đầu-cuối trên VIDEO THẬT của anh Hùng.

    .venv\Scripts\python _do_trung.py

Video THẬT: C:\Users\Admin\Downloads\Video\*我的观影报告*.mp4
Đây là SCRIPT ĐO (tạm) — kết quả sẽ được đóng thành cổng trong
`_test_da_quoc_gia.py`.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import unicodedata
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

WORK = Path(os.environ.get("BQ_TRUNG_WORK") or (REPO / "_tq_work"))
WORK.mkdir(parents=True, exist_ok=True)
os.environ["BQ_DATA_DIR"] = str(WORK / "data")
os.environ["BQ_DB_PATH"] = str(WORK / "data" / "studio.db")
os.environ["BQ_QSETTINGS_INI"] = str(WORK / "settings.ini")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["WHISPER_PROVIDER"] = "groq"
os.environ["BQ_FFMPEG_SLOTS"] = "1"          # máy anh Hùng đang chạy việc thật
os.environ.setdefault("ECO_MODE", "0")

# key Groq: đọc .env THẬT rồi truyền qua ENV — KHÔNG ghi ra file nào (cổng 22)
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
VIDEO_DIR = Path(r"C:\Users\Admin\Downloads\Video")
HAN = re.compile(r"[一-鿿]")
KANA = re.compile(r"[぀-ヿ]")
HANGUL = re.compile(r"[가-힯]")


def _dai(p: Path) -> float:
    r = subprocess.run(
        [FPROBE, "-v", "quiet", "-print_format", "json", "-show_format", str(p)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=60, creationflags=_NOWIN)
    return float(json.loads(r.stdout or "{}").get("format", {})
                 .get("duration") or 0)


def tim_video_trung():
    """Video THẬT tiếng Trung: tên có chữ HÁN, KHÔNG kana/hangul (né Nhật/Hàn).
    Chọn NGẮN NHẤT nhưng > 60 giây (anh Hùng cần video trên 1 phút)."""
    ung = []
    for p in sorted(VIDEO_DIR.glob("*.mp4")):
        n = p.name
        if not HAN.search(n) or KANA.search(n) or HANGUL.search(n):
            continue
        g = _dai(p)
        ung.append((g, p))
    ung.sort()
    # anh Hùng chỉ đích danh 2 file này -> ưu tiên tuyệt đối, không tự đoán.
    # `BQ_TRUNG_KHOA` đổi thứ tự để đo file thứ hai.
    uu = os.environ.get("BQ_TRUNG_KHOA", "")
    for khoa in ([uu] if uu else []) + ["一只手表", "第12集"]:
        for g, p in ung:
            if khoa in p.name and g > 60.0:
                print(f"  (ưu tiên file anh Hùng chỉ: {khoa})")
                return (g, p)
    tren60 = [(g, p) for g, p in ung if g > 60.0]
    print(f"  ứng viên tiếng Trung: {len(ung)} file · trên 60s: {len(tren60)}")
    for g, p in ung:
        print(f"    {g:8.1f}s  {p.name[:64]}")
    return tren60[0] if tren60 else (ung[0] if ung else (0.0, None))


def tach_wav(src: Path, dst: Path, giay: float = 0.0) -> bool:
    c = [FF, "-y", "-v", "error", "-i", str(src)]
    if giay > 0:
        c += ["-t", f"{giay:g}"]
    c += ["-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(dst)]
    r = subprocess.run(c, capture_output=True, timeout=900,
                       creationflags=_NOWIN)
    return r.returncode == 0 and dst.exists() and dst.stat().st_size > 1000


def dem_px(png: Path, nguong: int = 200):
    import cv2
    im = cv2.imread(str(png), cv2.IMREAD_GRAYSCALE)
    if im is None:
        return 0, []
    m = (im >= nguong)
    return int(m.sum()), [int(x) for x in m.sum(axis=1)]


def _esc(p) -> str:
    return str(p).replace("\\", "/").replace(":", "\\:")


def main() -> int:
    n_key = len([x for x in os.environ.get("GROQ_API_KEYS", "")
                 .replace(",", "\n").splitlines() if x.strip()])
    print(f"[work] {WORK}")
    print(f"[key Groq] {n_key} key · BQ_FFMPEG_SLOTS="
          f"{os.environ['BQ_FFMPEG_SLOTS']}")
    if n_key == 0:
        print("DỪNG: 0 key Groq -> số đo vô nghĩa.")
        return 2

    import app.queue.jobs  # noqa: F401 (cv2 trước Qt — thứ tự main.py)
    from app.ai import chon_doan as CD
    from app.ai import recap as RC
    from app.core import captions
    from app.core import ffmpeg_utils as fu
    from app.core import transcribe as TR
    from app.core.analysis import _set as set_analysis
    from app.database.db import db
    from app.modules import m1_highlight as M1
    from app.queue.worker import JobContext

    print(f"[encoder] {fu.detect_encoder()} · cửa chờ ffmpeg "
          f"{fu.so_ffmpeg_song_song()}")

    print("\n══ NGUỒN ══")
    giay, src = tim_video_trung()
    if not src:
        print("DỪNG: không thấy video tiếng Trung.")
        return 2
    print(f"  CHỌN: {src.name}\n  dài {giay:.2f}s")

    # ═════════════ PHÉP 1: CHÉP LỜI ═════════════
    print("\n══ PHÉP 1 — CHÉP LỜI (Groq thật) ══")
    wav = WORK / "trung.wav"
    tj = WORK / "trung_transcript.json"
    if tj.exists():
        tr = json.loads(tj.read_text(encoding="utf-8"))
        print("  (dùng lại bản chép lời đã đo)")
    else:
        assert tach_wav(src, wav, min(giay, 240.0)), "tách wav hỏng"
        t0 = time.time()
        tr = TR.transcribe(str(wav), language=None)
        print(f"  thời gian chép lời: {time.time() - t0:.1f}s")
        tj.write_text(json.dumps(tr, ensure_ascii=False), encoding="utf-8")
    lg = str(tr.get("language") or "")
    segs_tr = tr.get("segments") or []
    words_tr = tr.get("words") or []
    eng = str(tr.get("engine") or "")
    text_all = str(tr.get("text") or "")
    n_han = len(HAN.findall(text_all))
    n_latin = sum(1 for ch in text_all if "a" <= ch.lower() <= "z")
    print(f"  language      = '{lg}'  -> _ma_iso = {TR._ma_iso(lg)!r}")
    print(f"  engine THỰC   = {eng}")
    print(f"  segments      = {len(segs_tr)}")
    print(f"  words (mốc)   = {len(words_tr)}")
    print(f"  ký tự HÁN     = {n_han} · ký tự latin a-z = {n_latin}")
    print(f"  mật độ        = {len(words_tr) / max(1.0, min(giay, 240.0)):.2f}"
          " mốc-từ/giây")
    print("  --- 3 ĐOẠN ĐẦU (phải là CHỮ HÁN, không phải phiên âm latin) ---")
    for s in segs_tr[:3]:
        t = str(s.get("text", ""))
        print(f"    [{float(s.get('start', 0)):7.2f}-"
              f"{float(s.get('end', 0)):7.2f}] {t}")
        print(f"        codepoint 8 ký tự đầu: "
              + " ".join(f"U+{ord(c):04X}" for c in t.strip()[:8]))
    co_loi, vi_sao, mds = CD.co_loi_noi_that(tr, min(giay, 240.0))
    print(f"  co_loi_noi_that = {co_loi} · {vi_sao} · mật độ {mds:.2f}")

    # ═════════════ PHÉP 2: TÁCH TỪ CJK ═════════════
    print("\n══ PHÉP 2 — TÁCH TỪ CJK ══")
    cau_dai = max((str(s.get("text", "")) for s in segs_tr),
                  key=lambda x: len(x), default="")
    print(f"  câu Trung DÀI NHẤT trong bản chép lời ({len(cau_dai)} ký tự):")
    print(f"    {cau_dai}")
    print(f"  _has_cjk            = {RC._has_cjk(cau_dai)}")
    n_split = len(cau_dai.split())
    n_tok = len(RC._word_tokens(cau_dai))
    print(f"  .split()            = {n_split} token")
    print(f"  _word_tokens        = {n_tok} token")
    print(f"  -> đường CJK CHẠY   = {n_tok > n_split}")
    print(f"  _caption_tokens     = {len(M1._caption_tokens(cau_dai))} cụm")
    print(f"    5 cụm đầu: {M1._caption_tokens(cau_dai)[:5]}")
    print("  BẤT BIẾN non-CJK: _word_tokens('a b c') == .split() -> "
          f"{RC._word_tokens('a b c') == 'a b c'.split()}")
    # mật độ nếu DÙNG .split() (đường SAI) so với CJK-aware
    tong_split = sum(len(str(s.get("text", "")).split()) for s in segs_tr)
    tong_tok = sum(len(RC._word_tokens(str(s.get("text", ""))))
                   for s in segs_tr)
    d = min(giay, 240.0)
    print(f"  mật độ toàn bài: .split() {tong_split / d:.2f} từ/giây · "
          f"_word_tokens {tong_tok / d:.2f} từ/giây")

    # ═════════════ PHÉP 3: CHỌN ĐOẠN ═════════════
    print("\n══ PHÉP 3 — CHỌN ĐOẠN (AI thật hay heuristic?) ══")
    adir = WORK / "assets"
    (adir / "clips").mkdir(parents=True, exist_ok=True)
    pid = db.execute("INSERT INTO projects(name, assets_dir, grp) VALUES(?,?,?)",
                     ("Kênh Trung", str(adir), "trung")).lastrowid
    vid = db.execute("INSERT INTO videos(project_id, src_path, duration) "
                     "VALUES(?,?,?)", (pid, str(src), giay)).lastrowid
    set_analysis(vid, "transcript", "done", tr, engine=eng)

    class Ctx(JobContext):
        def __init__(self) -> None:
            self.job_id = 0
            self.profile = {"encoder": fu.detect_encoder()}
            self.dong: list = []

        def progress(self, p: float, m: str = "") -> None:
            if m:
                self.dong.append(m)

        def check_canceled(self) -> None:
            return None

    ctx = Ctx()
    t0 = time.time()
    res = M1.generate_highlights(
        {"video_id": vid,
         "preset": {"count": 3, "min_len": 30.0, "max_len": 60.0}}, ctx)
    dt = time.time() - t0
    print(f"  generate_highlights: {dt:.1f}s")
    print(f"  result = {json.dumps({k: v for k, v in res.items()}, ensure_ascii=False)[:400]}")
    print(f"  llm_used = {res.get('llm_used')}   <-- True = AI THẬT, "
          "False/thiếu = CẮT CƠ BẢN")
    rows = db.query("SELECT id, title, start_sec, end_sec, signals FROM clips "
                    "WHERE video_id=? AND status='suggested' ORDER BY id", (vid,))
    print(f"  {len(rows)} Part:")
    for i, r in enumerate(rows, 1):
        sg = (db.loads(r["signals"], {}) or {})
        print(f"    Part {i}: {r['start_sec']:.2f}-{r['end_sec']:.2f}s "
              f"({r['end_sec'] - r['start_sec']:.1f}s) · "
              f"llm={sg.get('llm_used')} · đoạn={sg.get('segments')}")
        print(f"      tiêu đề: {r['title']}")
    print("  --- nhật ký ctx (30 dòng cuối) ---")
    for m in ctx.dong[-30:]:
        print("    ·", m[:160])

    # ═════════════ PHÉP 4: PHỤ ĐỀ CHỮ HÁN ═════════════
    print("\n══ PHÉP 4 — PHỤ ĐỀ HIỆN ĐƯỢC CHỮ HÁN ══")
    if not rows:
        print("  BỎ QUA: 0 Part -> không có gì xuất.")
        return 1
    cid = rows[0]["id"]
    cs = {"preset": "Trắng đơn giản", "font": "Montserrat", "ny": 0.78,
          "size": 0.055, "delay": 0.0, "hook_on": False}
    pay = {"clip_id": cid, "out_w": 1080, "out_h": 1920, "mode": "canvas",
           "video_rect": (0.5, 0.5, 1.0),
           "bg": "blur", "captions": True, "cap_style": cs,
           "part_no": 1, "out_name": "Part 1 kiem trung",
           "out_dir": str(WORK / "xuat"), "flat": True,
           "chuyen_canh": "nhe", "hieu_ung": "nhe",
           "fx_fade": True, "fx_whoosh": True}
    t0 = time.time()
    out = M1.export_clip(pay, ctx)
    print(f"  export_clip: {time.time() - t0:.1f}s · {json.dumps(out, ensure_ascii=False)[:300]}")
    op = Path(str(out.get("export_path") or ""))
    print(f"  file: {op} · tồn tại={op.exists()} · "
          f"{op.stat().st_size / 1048576 if op.exists() else 0:.2f} MB")
    if out.get("canh_bao"):
        print(f"  !!! CẢNH BÁO từ job: {out['canh_bao']}")

    # tìm .ass mà job vừa dựng (job tự dọn) -> dựng lại y hệt để soi
    print("\n  --- (a) font libass THẬT SỰ chọn (ffmpeg -loglevel debug) ---")
    words = words_tr or M1._fake_words_from_segments(segs_tr)
    c0 = float(rows[0]["start_sec"])
    sg0 = (db.loads(rows[0]["signals"], {}) or {}).get("segments") \
        or [[rows[0]["start_sec"], rows[0]["end_sec"]]]
    ass = WORK / "trung.ass"
    ok_ass = captions.build_ass(
        words, [[float(a), float(b)] for a, b in sg0], str(ass), 1080, 1920,
        font="Montserrat", size=int(0.055 * 1920), ny=0.78,
        preset="Trắng đơn giản", delay=0.0)
    print(f"  build_ass = {ok_ass} · {ass.stat().st_size if ass.exists() else 0} byte")
    fonts_dir = str(REPO / "app" / "assets" / "fonts")
    khung_sub = WORK / "khung_co_sub.png"
    # mốc có chữ: lấy giữa cue đầu tiên trong .ass
    txt_ass = ass.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"Dialogue: \d+,(\d+):(\d+):([\d.]+),", txt_ass)
    moc = 1.0
    if m:
        moc = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
        moc += 0.25
    print(f"  mốc lấy khung = {moc:.2f}s (cue đầu của .ass)")
    r = subprocess.run(
        [FF, "-y", "-loglevel", "debug", "-f", "lavfi",
         "-i", "color=c=black:s=1080x1920:d=%.1f" % (moc + 3),
         "-vf", f"subtitles='{_esc(ass)}':fontsdir='{_esc(fonts_dir)}'",
         "-ss", f"{moc:g}", "-frames:v", "1", str(khung_sub)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=600, creationflags=_NOWIN)
    for ln in (r.stderr or "").splitlines():
        if any(k in ln for k in ("fontselect", "Glyph ", "Using font",
                                 "font provider", "fontconfig", "Init:",
                                 "Added font", "Failed to open",
                                 "not found", "Fontconfig")):
            print("    libass:", ln.strip()[:170])
    tong, dong = dem_px(khung_sub)
    print(f"  khung CÓ phụ đề : {tong} px sáng · "
          f"{len([x for x in dong if x])} hàng có chữ")
    khung_ko = WORK / "khung_khong_sub.png"
    subprocess.run(
        [FF, "-y", "-v", "error", "-f", "lavfi",
         "-i", "color=c=black:s=1080x1920:d=2",
         "-frames:v", "1", str(khung_ko)],
        capture_output=True, timeout=300, creationflags=_NOWIN)
    tong0, _ = dem_px(khung_ko)
    print(f"  khung KHÔNG phụ đề: {tong0} px sáng")

    # khung từ FILE MP4 THẬT vừa xuất (đường xuất đầy đủ, không chỉ lavfi).
    # ĐO BẮT BUỘC: so vùng chữ của khung CÓ phụ đề với khung KHÔNG có phụ đề —
    # mã thoát 0 của ffmpeg KHÔNG chứng minh được chữ hiện ra.
    if op.exists():
        import cv2
        best = (0, 0.0, None)
        for mm in (1.0, 2.0, 3.0, 5.0, 8.0, 12.0, 20.0):
            k = WORK / f"khung_that_{mm:g}.png"
            subprocess.run(
                [FF, "-y", "-v", "error", "-ss", f"{mm:g}", "-i", str(op),
                 "-frames:v", "1", str(k)], capture_output=True, timeout=300,
                creationflags=_NOWIN)
            if not k.exists():
                continue
            im = cv2.imread(str(k), cv2.IMREAD_GRAYSCALE)
            if im is None:
                continue
            # VÙNG CHỮ = dải quanh ny=0.78 (hàng 1420..1620) — đếm px RẤT SÁNG
            vung = im[1420:1650, :]
            n = int((vung >= 240).sum())
            print(f"  MP4 THẬT @{mm:5.1f}s: vùng chữ {n:6d} px >=240 · "
                  f"cả khung {int((im >= 240).sum()):7d} px")
            if n > best[0]:
                best = (n, mm, k)
        if best[2] is not None:
            crop2 = WORK / "that_vung_chu.png"
            subprocess.run(
                [FF, "-y", "-v", "error", "-i", str(best[2]),
                 "-vf", "crop=1080:230:0:1420", str(crop2)],
                capture_output=True, timeout=300, creationflags=_NOWIN)
            print(f"  -> khung nhiều chữ nhất: {best[1]:g}s ({best[0]} px) "
                  f"-> {crop2}")
            print(f"  -> khung ĐẦY ĐỦ để xem mắt: {best[2]}")

    # ẢNH ĐỂ MẮT NGƯỜI XEM: crop vùng chữ, phóng to
    crop = WORK / "vung_chu.png"
    co_chu = [i for i, v in enumerate(dong) if v > 0]
    if co_chu:
        y0 = max(0, min(co_chu) - 20)
        h = min(1920 - y0, max(co_chu) - y0 + 40)
        subprocess.run(
            [FF, "-y", "-v", "error", "-i", str(khung_sub),
             "-vf", f"crop=1080:{h}:0:{y0},scale=1080:-1", str(crop)],
            capture_output=True, timeout=300, creationflags=_NOWIN)
        print(f"  vùng chữ: hàng {min(co_chu)}..{max(co_chu)} -> {crop}")

    # ═════════════ PHÉP 5: RÀ FALLBACK ═════════════
    print("\n══ PHÉP 5 — RÀ ĐƯỜNG DỰ PHÒNG IM LẶNG ══")
    print(f"  hiệu ứng đã áp : {out.get('hieu_ung_log') or out.get('da_ap')}")
    print(f"  tiếng động     : {out.get('tieng_dong_log')}")
    sig_ap = db.query_one("SELECT signals FROM clips WHERE id=?", (cid,))
    print(f"  clips.signals['da_ap'] = "
          f"{json.dumps((db.loads(sig_ap['signals'], {}) or {}).get('da_ap'), ensure_ascii=False)}")
    lg_dir = Path(os.environ["BQ_DATA_DIR"]) / "logs"
    if lg_dir.is_dir():
        for f in sorted(lg_dir.rglob("*")):
            if f.is_file():
                print(f"  log {f.name} ({f.stat().st_size} byte)")
                t = f.read_text(encoding="utf-8", errors="replace")
                for ln in t.splitlines():
                    if any(k in ln.lower() for k in (
                            "fallback", "cơ bản", "heuristic", "không chọn",
                            "bỏ hiệu ứng", "mặc định", "lỗi", "error",
                            "warn", "thiếu")):
                        print("     |", ln.strip()[:170])
    print("\n  --- nhật ký ctx lượt XUẤT ---")
    for m in ctx.dong[-25:]:
        print("    ·", m[:160])
    return 0


if __name__ == "__main__":
    sys.exit(main())
