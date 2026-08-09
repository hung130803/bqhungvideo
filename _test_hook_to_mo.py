# -*- coding: utf-8 -*-
r"""CỔNG 47 — HOOK CHỌN THEO TÒ MÒ, KHÔNG THEO TIẾNG TO.

    .venv\Scripts\python _test_hook_to_mo.py [--so 8] [--giay 150]

Anh Hùng: hook giỏi là chỗ **để lại câu hỏi / thông tin dở dang** ("và rồi anh
ta phát hiện ra…"), KHÔNG phải tiếng hét. v2.20.0 `_pick_hook_seg` dò cửa sổ
2,5 s có `_audio_score` lớn nhất -> chọn theo ĐỘ ỒN.

CỔNG NÀY KIỂM **KẾT QUẢ**, KHÔNG KIỂM Ý ĐỊNH:
  CA 1  chấm câu (hàm thuần) đúng trên 4 thứ tiếng + không nhận nhầm câu chào
  CA 2  **A/B trên >= 8 VIDEO THẬT nhiều thứ tiếng, chép lời bằng Groq THẬT** —
        IN RA CÂU ĐƯỢC CHỌN của CẢ HAI cách để người đọc tự đánh giá; đo:
          · hook CŨ rơi vào chỗ **KHÔNG MỘT CHỮ NÀO** (nhạc/tiếng động) — bao
            nhiêu video (đây là hỏng thật, không phải ý kiến)
          · hook CŨ rơi trúng câu CHÀO HỎI/KÊU GỌI ĐĂNG KÝ
          · điểm tò mò câu MỚI so với câu CŨ
  CA 3  **BẤT BIẾN video KHÔNG CÓ LỜI**: `chon_hook_to_mo` trả None và
        `_pick_hook_seg` ra ĐÚNG cửa sổ cao trào tiếng như bản cũ (dựng lại
        công thức cũ ngay trong cổng rồi so từng số).
  CA 4  TIỀN ĐỊNH: chạy 2 lượt trên cùng dữ liệu ra y hệt (3 làn xuất song song
        phải ra cùng một hook, không thì tra lại không được).
  CA 5  QUÉT TĨNH: `hook_to_mo.py` KHÔNG được đếm token bằng `.split()`
        (câu Nhật/Trung không có dấu cách -> 1 token -> mọi ngưỡng sai) và
        KHÔNG được bỏ dấu tiếng Việt.

CHỌN NGUỒN: theo **băm sha1 của TÊN** (bài học cổng 41 — prodown tải liên tục
nên xếp theo KÍCH THƯỚC thì "video thứ N" đổi giữa 2 lượt). Ép nguồn bằng
`BQ_HOOK_SRC=<file>;<file>` để tái hiện.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

_SB = Path(tempfile.mkdtemp(prefix="hookto_"))
os.environ["BQ_DATA_DIR"] = str(_SB)
os.environ["BQ_DB_PATH"] = str(_SB / "studio.db")
os.environ["BQ_QSETTINGS_INI"] = str(_SB / "settings.ini")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["WHISPER_PROVIDER"] = "groq"
os.environ.setdefault("ECO_MODE", "0")

# key Groq: đọc .env THẬT rồi truyền qua ENV — KHÔNG ghi ra file (cổng 22)
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
    print(("  ĐẠT   " if ok else "  HỎNG  ") + nhan
          + (f"   << {ct}" if ct else ""))
    if not ok:
        FAIL.append(nhan)
    return ok


def bo_qua(nhan: str, ly_do: str) -> None:
    print(f"  THIẾU {nhan}   << {ly_do}")
    BOQUA.append(f"{nhan} — {ly_do}")


def _ma_that(src: str, mau: str) -> list:
    """Các dòng **MÃ CHẠY ĐƯỢC** có chứa `mau` — bỏ COMMENT và mọi CHUỖI.

    Vì sao không lọc bằng `startswith('#')`: ghi chú thụt lề, ghi chú ĐUÔI DÒNG
    và docstring đều lọt, nên chính câu *"CẤM `.split()`"* trong tài liệu bị kể
    là vi phạm. `tokenize` cho biết đúng loại từng token.
    """
    import io
    import tokenize
    dong = {}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            dong.setdefault(tok.start[0], []).append(tok.string)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return [f"KHÔNG PHÂN TÍCH ĐƯỢC {mau}"]
    return ["".join(v).strip() for _n, v in sorted(dong.items())
            if mau in "".join(v)]


#: nhóm -> ([thư mục], CHỮ VIẾT phải có trong TÊN FILE, giây tối thiểu).
#: Dấu hiệu ngôn ngữ lấy từ TÊN FILE — phải ĐỘC LẬP với `transcribe()`, nếu
#: không thì "chọn nguồn bằng chính kết quả đang đi assert" (bẫy cổng 40/41).
KHO = {
    "nhat": ([r"D:\video ssmatool\video nhật dài"], "[぀-ヿ一-鿿]", 60.0),
    "han":  ([r"D:\video ssmatool\video hàn dài",
              r"D:\video ssmatool\video hàn"], "[가-힯]", 40.0),
    "anh":  ([r"D:\video ssmatool\video mỹ"], "", 60.0),
    "viet": ([r"D:\video ssmatool\video viêt"],
             "[ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩị"
             "òóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ]", 25.0),
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


def chon_nguon(nhom: str, so: int, gmax=1800.0) -> list:
    """`so` video của nhóm, xếp theo **BĂM SHA1 CỦA TÊN** (ổn định giữa các
    lượt dù prodown vẫn đang tải vào cùng thư mục — bài học cổng 41).

    `KHO[nhom]` = (DANH SÁCH thư mục, mẫu CHỮ VIẾT trong tên file, giây tối
    thiểu). Lọc theo CHỮ VIẾT là dấu hiệu ĐỘC LẬP với `transcribe` (bài học
    cổng 40: prodown tải lẫn video tiếng Anh vào thư mục 'video nhật dài').
    """
    import re
    ds, chu, gmin = KHO[nhom]
    rx = re.compile(chu, re.I) if chu else None
    ung = []
    for d in ds:
        p = Path(d)
        if not p.is_dir():
            continue
        for f in p.rglob("*.mp4"):
            try:
                mb = f.stat().st_size / 1048576
            except OSError:
                continue
            if not (2.0 <= mb <= 300.0):
                continue
            if rx is not None and not rx.search(f.name):
                continue
            ung.append((hashlib.sha1(f.name.encode("utf-8",
                                                   "replace")).hexdigest(), f))
    ung.sort()
    ra = []
    for _h, f in ung:
        g = _dai(f)
        if gmin <= g <= gmax:
            ra.append((f, g))
        if len(ra) >= so:
            break
    return ra


def tach_wav(src: Path, dst: Path, t0: float, giay: float) -> bool:
    c = [FF, "-y", "-v", "error", "-ss", f"{t0:g}", "-i", str(src),
         "-t", f"{giay:g}", "-vn", "-ac", "1", "-ar", "16000",
         "-c:a", "pcm_s16le", str(dst)]
    r = subprocess.run(c, capture_output=True, timeout=600,
                       creationflags=_NOWIN)
    return r.returncode == 0 and dst.exists() and dst.stat().st_size > 1000


def bao_rms(wav: Path, hop: float = 0.5) -> dict:
    """Đường bao RMS -> đúng CẤU TRÚC `analysis['audio']` mà `_audio_score`
    đọc: {"rms_envelope":{"hop_sec":h,"values":[...]}, "peaks":[...]}."""
    import numpy as np
    import wave as W
    with W.open(str(wav), "rb") as w:
        sr, n = w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    v = np.frombuffer(raw[: (len(raw) // 2) * 2],
                      dtype="<i2").astype("float32") / 32768.0
    k = max(1, int(hop * sr))
    m = (v.size // k) * k
    if m < k:
        return {}
    o = v[:m].reshape(-1, k)
    vals = np.sqrt((o * o).mean(axis=1))
    mx = float(vals.max()) or 1.0
    vals = (vals / mx).tolist()
    return {"rms_envelope": {"hop_sec": hop, "values": vals}, "peaks": []}


def hook_cu(audio: dict, segs: list, M1) -> list:
    """CÔNG THỨC CŨ NGUYÊN VĂN (v2.20.0 `_pick_hook_seg` nhánh cao trào
    tiếng) — dựng lại NGAY TRONG CỔNG để CA 3 so được từng số, không phải tin
    lời ghi chú."""
    best, best_sc = None, -1.0
    for s0, e0 in segs:
        t = float(s0)
        while t + 2.5 <= float(e0):
            sc = M1._audio_score(audio, t, t + 2.5)
            if sc > best_sc:
                best_sc, best = sc, [round(t, 2), round(t + 2.5, 2)]
            t += 1.0
    if best and abs(best[0] - float(segs[0][0])) > 3.0:
        return best
    return None


def loi_trong_cua(tr: dict, a: float, b: float) -> str:
    ra = []
    for c in (tr or {}).get("segments") or []:
        try:
            s, e = float(c.get("start")), float(c.get("end"))
        except (TypeError, ValueError):
            continue
        if e > a and s < b:
            t = str(c.get("text") or "").strip()
            if t:
                ra.append(t)
    return " ".join(ra).strip()


# ══════════════════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--so", type=int, default=8, help="tổng số video A/B")
    ap.add_argument("--giay", type=float, default=150.0,
                    help="số giây audio lấy mỗi video")
    a = ap.parse_args()

    print(f"[sandbox] {_SB}")
    import app.queue.jobs  # noqa: F401  (cv2 nạp trước Qt — thứ tự main.py)
    from app.ai import hook_to_mo as HK
    from app.modules import m1_highlight as M1

    # ───────────────────────────────────────────── CA 1: hàm thuần, 4 tiếng
    print("\n══ CA 1. CHẤM CÂU — hàm thuần, 4 thứ tiếng ══")
    TO_MO = [
        ("anh", "And then he discovered something nobody had ever seen"),
        ("nhat", "そしたら彼は信じられないものを発見した"),
        ("han", "그런데 그 순간 아무도 모르는 비밀이 밝혀졌어요"),
        ("viet", "Và rồi anh ta phát hiện ra một điều không ai biết"),
    ]
    NHAT_NHEO = [
        ("anh", "Hello guys welcome back to my channel"),
        ("nhat", "こんにちは、みなさん"),
        ("han", "안녕하세요 여러분 오늘은"),
        ("viet", "Xin chào các bạn, hôm nay mình sẽ"),
        ("đệm", "um yeah ok"),
    ]
    for ten, cau in TO_MO:
        d, ly = HK.cham_cau(cau, 3.0)
        kiem(d >= HK.NGUONG, f"CA1 {ten}: câu tò mò qua ngưỡng ({d:.3f} >= "
                             f"{HK.NGUONG})", ly[:70])
    for ten, cau in NHAT_NHEO:
        d, ly = HK.cham_cau(cau, 3.0)
        kiem(d < HK.NGUONG, f"CA1 {ten}: câu chào/đệm KHÔNG qua ngưỡng "
                            f"({d:.3f} < {HK.NGUONG})", ly[:70])
    # bẫy ranh giới từ: "and" không được khớp trong "island"
    d_dao, _ = HK.cham_cau("We sailed to the island and saw the sand", 3.0)
    kiem(d_dao < HK.NGUONG,
         f"CA1 ranh giới từ: 'island/sand' KHÔNG khớp 'and then' ({d_dao:.3f})")
    # bẫy CJK: câu Nhật dài KHÔNG được coi là 1 token
    from app.ai.recap import _word_tokens
    cau_ja = "そしたら彼は信じられないものを発見した"
    kiem(len(_word_tokens(cau_ja.lower())) >= 8,
         "CA1 CJK: câu Nhật đếm nhiều token, không phải 1",
         f"{len(_word_tokens(cau_ja.lower()))} token vs "
         f"{len(cau_ja.split())} nếu .split()")

    # ───────────────────────────────────────────── CA 2: A/B video THẬT
    print("\n══ CA 2. A/B TRÊN VIDEO THẬT — chép lời Groq THẬT ══")
    n_key = len([x for x in os.environ.get("GROQ_API_KEYS", "")
                 .replace(",", "\n").splitlines() if x.strip()])
    print(f"[key Groq] {n_key} key · lấy {a.giay:g}s audio/video")
    if n_key == 0:
        bo_qua("CA 2 A/B video thật", "0 key Groq (chép lời sẽ tụt whisper máy)")
        return _ket()

    from app.core import transcribe as TR
    ep = os.environ.get("BQ_HOOK_SRC", "")
    nguon = []
    if ep:
        for x in ep.split(";"):
            if x.strip() and Path(x.strip()).exists():
                nguon.append(("ép", Path(x.strip()), _dai(Path(x.strip()))))
    else:
        # LẤY DƯ: video thật hay bị loại giữa chừng (tách audio hỏng, chép lời
        # ra < 4 câu — vlog nhạc nền). Lấy đúng `so // nhóm` thì chỉ cần MỘT
        # video bị loại là cổng ĐỎ oan vì thiếu mẫu, không phải vì app sai.
        moi = max(2, a.so // len(KHO)) + 2
        theo_nhom = {n: chon_nguon(n, moi) for n in KHO}
        # ĐAN XEN theo vòng, KHÔNG nối đuôi từng nhóm: vòng lấy mẫu bên dưới
        # dừng ngay khi đủ `--so`, nên nối đuôi thì 2 nhóm đầu chiếm hết suất và
        # ca "phủ >= 4 nhóm ngôn ngữ" HỎNG OAN dù trên đĩa có đủ cả 4 thứ tiếng.
        for i in range(moi):
            for nhom in KHO:
                if i < len(theo_nhom[nhom]):
                    f, g = theo_nhom[nhom][i]
                    nguon.append((nhom, f, g))
    if len(nguon) < a.so:
        bo_qua(f"CA 2 đủ {a.so} video", f"chỉ tìm được {len(nguon)}")

    hang = []
    for nhom, f, g in nguon:
        wav = _SB / f"a_{len(hang)}.wav"
        # lấy từ GIỮA video: đầu video hay là intro/nhạc hiệu, không đại diện
        t0 = max(0.0, min(g * 0.25, max(0.0, g - a.giay - 1)))
        if not tach_wav(f, wav, t0, a.giay):
            print(f"  (bỏ {f.name[:40]} — tách audio hỏng)")
            continue
        try:
            tr = TR.transcribe(str(wav), language=None)
        except Exception as e:  # noqa: BLE001
            print(f"  (bỏ {f.name[:40]} — chép lời lỗi: {str(e)[:60]})")
            continue
        finally:
            try:
                wav.unlink()
            except OSError:
                pass
        segs_tr = (tr or {}).get("segments") or []
        if len(segs_tr) < 4:
            print(f"  (bỏ {f.name[:40]} — chỉ {len(segs_tr)} câu)")
            continue
        # đoạn cắt giả lập: cả cửa sổ đã chép (đúng cảnh m1 chọn 2-3 đoạn dài)
        segs = [[0.0, float(a.giay)]]
        audio = bao_rms(_SB / "x.wav") if False else None
        hang.append({"nhom": nhom, "file": f, "tr": tr, "segs": segs,
                     "lang": str((tr or {}).get("language") or "?")})
        if len(hang) >= a.so:
            break

    kiem(len(hang) >= a.so, f"CA2 có >= {a.so} video thật chép lời được",
         f"đo {len(hang)}")
    kiem(len({h['nhom'] for h in hang}) >= 4,
         "CA2 phủ >= 4 nhóm ngôn ngữ",
         ", ".join(sorted({h['nhom'] for h in hang})))

    # đường CŨ cần `audio` -> dựng đường bao RMS THẬT của chính cửa sổ đó
    cu_khong_chu = cu_chao = 0
    tot_hon = bang_nhau = te_hon = 0
    print()
    for i, h in enumerate(hang, 1):
        wav = _SB / f"r_{i}.wav"
        g = _dai(h["file"])
        t0 = max(0.0, min(g * 0.25, max(0.0, g - a.giay - 1)))
        tach_wav(h["file"], wav, t0, a.giay)
        audio = bao_rms(wav)
        try:
            wav.unlink()
        except OSError:
            pass
        hc = hook_cu(audio, h["segs"], M1) if audio else None
        moi = HK.chon_hook_to_mo(h["tr"], h["segs"])
        cau_cu = loi_trong_cua(h["tr"], hc[0], hc[1]) if hc else ""
        d_cu = HK.cham_cau(cau_cu, (hc[1] - hc[0]) if hc else 0)[0] \
            if cau_cu else 0.0
        d_moi = moi["diem"] if moi else 0.0
        if hc and not cau_cu:
            cu_khong_chu += 1
        if cau_cu and any(HK._khop(HK._chuan(cau_cu), k) for k in HK._XAU):
            cu_chao += 1
        if moi:
            if d_moi > d_cu + 1e-9:
                tot_hon += 1
            elif abs(d_moi - d_cu) <= 1e-9:
                bang_nhau += 1
            else:
                te_hon += 1
        print(f"─ {i}. [{h['nhom']}/{h['lang']}] {h['file'].name[:56]}")
        print(f"   CŨ  (cao trào tiếng) giây "
              f"{hc[0] if hc else '-'}-{hc[1] if hc else '-'} · tò mò "
              f"{d_cu:.2f} : "
              + (f"«{cau_cu[:100]}»" if cau_cu
                 else "«KHÔNG MỘT CHỮ NÀO — nhạc/tiếng động»"))
        if moi:
            print(f"   MỚI (tò mò)          giây {moi['seg'][0]}-"
                  f"{moi['seg'][1]} · tò mò {d_moi:.2f} : «{moi['cau'][:100]}»")
            print(f"        lý do: {moi['vi_sao'][:130]}")
        else:
            print("   MỚI (tò mò)          KHÔNG câu nào đủ tò mò -> "
                  "GIỮ ĐƯỜNG CŨ")

    n = len(hang) or 1
    co_moi = tot_hon + bang_nhau + te_hon
    print(f"\n  [số đo] {n} video · hook CŨ rơi vào chỗ KHÔNG CHỮ: "
          f"{cu_khong_chu}/{n} · rơi trúng câu CHÀO/ĐĂNG KÝ: {cu_chao}/{n}")
    print(f"  [số đo] hook MỚI chọn được: {co_moi}/{n} · tò mò cao hơn CŨ: "
          f"{tot_hon} · bằng: {bang_nhau} · thấp hơn: {te_hon}")
    kiem(co_moi >= max(1, int(n * 0.6)),
         f"CA2 hook tò mò chọn được trên >= 60% video ({co_moi}/{n})")
    kiem(te_hon == 0,
         "CA2 KHÔNG video nào hook mới tò mò THẤP HƠN hook cũ",
         f"{te_hon} video")
    # hook MỚI không bao giờ được là câu chào hỏi/kêu gọi đăng ký
    xau_moi = 0
    for h in hang:
        m = HK.chon_hook_to_mo(h["tr"], h["segs"])
        if m and any(HK._khop(HK._chuan(m["cau"]), k) for k in HK._XAU):
            xau_moi += 1
    kiem(xau_moi == 0, "CA2 hook MỚI không bao giờ là câu chào/kêu gọi đăng ký",
         f"{xau_moi} video")

    # ───────────────────────────────── CA 3: BẤT BIẾN video KHÔNG CÓ LỜI
    print("\n══ CA 3. BẤT BIẾN — video KHÔNG CÓ LỜI phải đi ĐÚNG đường cũ ══")
    h0 = hang[0] if hang else None
    if not h0:
        bo_qua("CA 3", "không có video nào ở CA 2")
    else:
        wav = _SB / "kl.wav"
        g = _dai(h0["file"])
        t0 = max(0.0, min(g * 0.25, max(0.0, g - a.giay - 1)))
        tach_wav(h0["file"], wav, t0, a.giay)
        audio = bao_rms(wav)
        try:
            wav.unlink()
        except OSError:
            pass
        for ten, tr_rong in (("transcript rỗng", {}),
                             ("transcript None", None),
                             ("segments rỗng", {"segments": []}),
                             ("câu không mốc",
                              {"segments": [{"text": "và rồi anh ta phát hiện"}]})):
            kiem(HK.chon_hook_to_mo(tr_rong, h0["segs"]) is None,
                 f"CA3 {ten}: chon_hook_to_mo trả None")
        # và `_pick_hook_seg` phải ra ĐÚNG cửa sổ cao trào tiếng của bản cũ
        mong = hook_cu(audio, h0["segs"], M1)
        _cu_get = M1.get_analysis
        M1.get_analysis = lambda vid, kind: (audio if kind == "audio" else None)
        try:
            that = M1._pick_hook_seg(-1, {}, h0["segs"], transcript={})
        finally:
            M1.get_analysis = _cu_get
        kiem(that == mong,
             "CA3 _pick_hook_seg KHÔNG LỜI = ĐÚNG cửa sổ cao trào tiếng cũ",
             f"mới {that} vs cũ {mong}")
        # có lời tò mò -> phải KHÁC (nếu không thì bản vá vô tác dụng)
        M1.get_analysis = lambda vid, kind: (audio if kind == "audio" else None)
        try:
            that2 = M1._pick_hook_seg(-1, {}, h0["segs"],
                                      transcript=h0["tr"])
        finally:
            M1.get_analysis = _cu_get
        m0 = HK.chon_hook_to_mo(h0["tr"], h0["segs"])
        if m0:
            kiem(that2 == m0["seg"],
                 "CA3 CÓ lời tò mò -> _pick_hook_seg đi đường TÒ MÒ",
                 f"{that2} vs {m0['seg']}")

    # ───────────────────────────────────────────── CA 4: TIỀN ĐỊNH
    print("\n══ CA 4. TIỀN ĐỊNH — 2 lượt ra y hệt ══")
    lech = 0
    for h in hang:
        r1 = HK.chon_hook_to_mo(h["tr"], h["segs"])
        r2 = HK.chon_hook_to_mo(h["tr"], h["segs"])
        if (r1 or {}).get("seg") != (r2 or {}).get("seg"):
            lech += 1
    kiem(lech == 0, "CA4 chạy 2 lượt ra CÙNG một hook", f"{lech} lệch")

    # ───────────────────────────────────────────── CA 5: QUÉT TĨNH
    print("\n══ CA 5. QUÉT TĨNH ══")
    src = (REPO / "app" / "ai" / "hook_to_mo.py").read_text(encoding="utf-8")
    # QUÉT **MÃ THẬT**, không quét chữ trong ghi chú. Bản đầu của cổng này lọc
    # bằng `startswith("#")` nên chính dòng ghi chú *"CẤM .split()"* bị kể là vi
    # phạm -> cổng ĐỎ OAN vĩnh viễn (đúng bài học cổng 27: soi cả file thì bắt
    # nhầm thứ user không thấy). `tokenize` bỏ COMMENT + STRING (gồm docstring)
    # nên chỉ còn mã chạy được.
    xau = _ma_that(src, ".split()")
    kiem(not xau, "CA5 hook_to_mo KHÔNG đếm token bằng `.split()`",
         "; ".join(x[:60] for x in xau))
    # TỰ KIỂM BỘ DÒ: bộ dò phải KÊU khi mã thật có `.split()`, không thì cổng
    # này chỉ là con dấu (bài học cổng 43 "tự kiểm bộ dò").
    kiem(bool(_ma_that("x = 1  # .split()\ns = 'a .split() b'\nn = t.split()",
                       ".split()")),
         "CA5 bộ dò tĩnh CÓ kêu khi mã thật dùng `.split()`")
    kiem(not _ma_that("# chỉ ghi chú .split()\ns = 'chuỗi .split()'",
                      ".split()"),
         "CA5 bộ dò tĩnh KHÔNG kêu với ghi chú/chuỗi")
    kiem("_word_tokens" in src, "CA5 hook_to_mo DÙNG recap._word_tokens")
    kiem("unicodedata" not in src and "normalize('NFD'" not in src
         and 'normalize("NFD"' not in src,
         "CA5 hook_to_mo KHÔNG bỏ dấu tiếng Việt")
    return _ket()


def _ket() -> int:
    print("\n" + "═" * 74)
    if BOQUA:
        print(f"THIẾU {len(BOQUA)}:")
        for x in BOQUA:
            print("   ·", x)
    if FAIL:
        print(f"HỎNG {len(FAIL)}:")
        for x in FAIL:
            print("   ✗", x)
        return 1
    print("TẤT CẢ ĐẠT")
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    finally:
        import shutil
        shutil.rmtree(_SB, ignore_errors=True)
    sys.exit(rc)
