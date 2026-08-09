# -*- coding: utf-8 -*-
r"""ĐO NÚT THẮT 219 GIÂY CỦA "AI XEM HÌNH" — tách ra rồi mới dám sửa.

    .venv\Scripts\python _do_vision_219.py [--khung 12] [--luot 6]

`VISION_CUT` mặc định TẮT vì đo **219 giây/video** (12 khung · qwen3.6-27b ·
tối đa 3 ảnh/lượt). Anh Hùng nói key Groq gần như vô hạn -> NẾU 219 giây chủ
yếu là ĐỢI MẠNG TUẦN TỰ thì gọi song song nhiều key sẽ hạ mạnh.

**ĐO TRƯỚC, SỬA SAU.** Script này tách 219 giây thành:
  (A) TRÍCH KHUNG   — ffmpeg, `extract_frame`, đo từng khung
  (B) ĐỢI API       — `complete_vision_json`, đo từng lượt
  (C) phần còn lại  — mã hoá base64, dựng prompt, ghi DB…
rồi chạy LẠI đúng những lượt đó **SONG SONG mỗi lượt một key** và đo lại.

KHÔNG ÉP KẾT LUẬN: Groq bóp tốc độ theo tài khoản, nên nếu song song KHÔNG
nhanh hơn thì script in thẳng ra như vậy.

LUẬT 1 (máy anh Hùng đang làm việc): chỉ 1 ffmpeg mỗi lúc — phần trích khung
chạy TUẦN TỰ. Chỉ phần GỌI MẠNG mới song song (không tốn CPU máy).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

_SB = Path(tempfile.mkdtemp(prefix="dov219_"))
os.environ["BQ_DATA_DIR"] = str(_SB)
os.environ["BQ_DB_PATH"] = str(_SB / "studio.db")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["USE_VISION"] = "1"
os.environ["VISION_CUT"] = "1"
os.environ["LIGHT_MODE"] = "0"

_env = (Path(os.environ.get("LOCALAPPDATA") or Path.home())
        / "BQHungVideo" / ".env")
if _env.exists():
    for _ln in _env.read_text(encoding="utf-8", errors="replace").splitlines():
        _k, _, _v = _ln.partition("=")
        _k, _v = _k.strip(), _v.strip().strip('"').strip("'")
        if _k in ("GROQ_API_KEYS", "GROQ_KEYS_FILE") and _v:
            os.environ.setdefault(_k, _v)

import _test_guard  # noqa: E402,F401

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
    except (AttributeError, ValueError):
        pass

_NOWIN = 0x08000000 if os.name == "nt" else 0


def _so(x: float, n: int = 2) -> str:
    return f"{x:.{n}f}".replace(".", ",")


def chon_video() -> Path:
    """1 video THẬT trên máy, chọn TIỀN ĐỊNH theo băm tên (chạy lại ra cùng
    video dù prodown vẫn đang tải vào cùng thư mục)."""
    ep = os.environ.get("BQ_VD_SRC", "")
    if ep and Path(ep).exists():
        return Path(ep)
    from config import settings
    ung = []
    for d in (r"D:\video ssmatool\video mỹ", r"D:\video ssmatool\video viêt",
              r"D:\video ssmatool\video nhật dài"):
        p = Path(d)
        if not p.is_dir():
            continue
        for f in p.rglob("*.mp4"):
            try:
                mb = f.stat().st_size / 1048576
            except OSError:
                continue
            if 5.0 <= mb <= 300.0:
                ung.append((hashlib.sha1(
                    f.name.encode("utf-8", "replace")).hexdigest(), f))
    ung.sort()
    for _h, f in ung:
        r = subprocess.run(
            [settings.FFPROBE_PATH, "-v", "quiet", "-print_format", "json",
             "-show_format", str(f)], capture_output=True, text=True,
            encoding="utf-8", timeout=30, creationflags=_NOWIN)
        try:
            g = float(json.loads(r.stdout or "{}")
                      .get("format", {}).get("duration") or 0)
        except Exception:  # noqa: BLE001
            continue
        if 120.0 <= g <= 1800.0:
            print(f"[nguồn] {f.name[:60]} · {_so(g, 1)} giây")
            return f
    raise SystemExit("không tìm được video thật để đo")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--khung", type=int, default=12)
    ap.add_argument("--luot", type=int, default=0,
                    help="số lượt API (0 = khung/_BATCH)")
    a = ap.parse_args()
    print(f"[sandbox] {_SB}")
    import app.queue.jobs  # noqa: F401
    from app.ai import llm
    from app.core import vision_digest as VD
    from app.core.ffmpeg_utils import extract_frame
    from config import settings

    keys = settings.groq_keys()
    print(f"[key Groq] {len(keys)} key · model="
          f"{getattr(settings, 'GROQ_VISION_MODEL', '?')} · "
          f"_CAP={VD._CAP} _BATCH={VD._BATCH} _FRAME_W={VD._FRAME_W}")
    if not keys:
        print("0 key -> không đo được"); return 2
    src = chon_video()
    r = subprocess.run(
        [settings.FFPROBE_PATH, "-v", "quiet", "-print_format", "json",
         "-show_format", str(src)], capture_output=True, text=True,
        encoding="utf-8", timeout=30, creationflags=_NOWIN)
    dur = float(json.loads(r.stdout or "{}").get("format", {})
                .get("duration") or 0)
    times = VD.pick_frame_times(dur, None, cap=a.khung)

    # ───────────────────────────────────── (A) TRÍCH KHUNG (ffmpeg, TUẦN TỰ)
    print(f"\n══ (A) TRÍCH KHUNG — {len(times)} khung, ffmpeg, TUẦN TỰ "
          f"(LUẬT 1) ══")
    frames, t_kh = [], []
    for k, t in enumerate(times):
        fp = str(_SB / f"f{k:03d}.jpg")
        t0 = time.perf_counter()
        ok = extract_frame(str(src), t, fp, width=VD._FRAME_W)
        d = time.perf_counter() - t0
        t_kh.append(d)
        if ok:
            frames.append((t, fp))
    kb = [os.path.getsize(p) / 1024 for _t, p in frames]
    A = sum(t_kh)
    print(f"  {len(frames)}/{len(times)} khung · TỔNG {_so(A)} giây · "
          f"mỗi khung trung vị {_so(statistics.median(t_kh), 3)}s "
          f"(min {_so(min(t_kh), 3)} · max {_so(max(t_kh), 3)}) · "
          f"ảnh {_so(statistics.median(kb), 1)} KB")

    # ───────────────────────────────────── (B) ĐỢI API — TUẦN TỰ (như app)
    lo = [frames[i:i + VD._BATCH] for i in range(0, len(frames), VD._BATCH)]
    if a.luot:
        lo = lo[:a.luot]
    print(f"\n══ (B) ĐỢI API — {len(lo)} lượt x {VD._BATCH} ảnh, "
          f"TUẦN TỰ (đúng như app đang chạy) ══")
    t_api, n_moc = [], 0
    B0 = time.perf_counter()
    for i, b in enumerate(lo, 1):
        t0 = time.perf_counter()
        try:
            rows = VD._describe_batch([p for _t, p in b])
            n_moc += len([x for x in rows or [] if isinstance(x, dict)])
            err = ""
        except Exception as e:  # noqa: BLE001
            rows, err = [], f"{type(e).__name__}: {str(e)[:70]}"
        d = time.perf_counter() - t0
        t_api.append(d)
        print(f"  lượt {i:2d}/{len(lo)}: {_so(d)}s · {len(rows or [])} mô tả"
              + (f" · LỖI {err}" if err else ""))
    B = time.perf_counter() - B0
    print(f"  TỔNG ĐỢI API (tuần tự) {_so(B)} giây · mỗi lượt trung vị "
          f"{_so(statistics.median(t_api))}s · {n_moc} mô tả")

    # ───────────────────────── (C) SONG SONG — mỗi lượt MỘT KEY khác nhau
    print(f"\n══ (C) SONG SONG — {len(lo)} lượt cùng lúc, MỖI LƯỢT MỘT KEY ══")
    print(f"  (dùng {min(len(lo), len(keys))} key khác nhau trong {len(keys)} "
          f"key có sẵn)")
    ket: dict = {}
    loi_ss: list = []

    def _mot(i: int, batch: list, key: str) -> None:
        t0 = time.perf_counter()
        try:
            from openai import OpenAI
            content = [{"type": "text", "text": VD._VISION_PROMPT}]
            for _t, p in batch:
                content.append({"type": "image_url", "image_url": {
                    "url": f"data:image/jpeg;base64,{llm._b64(p)}"}})
            cl = OpenAI(api_key=key,
                        base_url="https://api.groq.com/openai/v1",
                        timeout=120, max_retries=1)
            resp = cl.chat.completions.create(
                model=settings.GROQ_VISION_MODEL,
                messages=[{"role": "user", "content": content}],
                temperature=0.3, max_tokens=900, reasoning_effort="none")
            data = llm._extract_json(resp.choices[0].message.content or "")
            ket[i] = (time.perf_counter() - t0, len(data or []), "")
        except Exception as e:  # noqa: BLE001
            ket[i] = (time.perf_counter() - t0, 0,
                      f"{type(e).__name__}: {str(e)[:90]}")
            loi_ss.append(str(e)[:90])

    ths = []
    C0 = time.perf_counter()
    for i, b in enumerate(lo):
        th = threading.Thread(target=_mot, args=(i, b, keys[i % len(keys)]),
                              daemon=True)
        ths.append(th)
        th.start()
    for th in ths:
        th.join(timeout=300)
    C = time.perf_counter() - C0
    for i in sorted(ket):
        d, n, err = ket[i]
        print(f"  lượt {i + 1:2d}/{len(lo)}: {_so(d)}s · {n} mô tả"
              + (f" · LỖI {err}" if err else ""))
    ok_ss = sum(1 for i in ket if not ket[i][2])
    print(f"  TỔNG SONG SONG (wall) {_so(C)} giây · {ok_ss}/{len(lo)} lượt "
          f"thành công")

    # ───────────────────────────────────────────────────── KẾT LUẬN
    print("\n" + "═" * 72)
    tong = A + B
    print(f"  TÁCH {_so(tong)} giây cho {len(frames)} khung / {len(lo)} lượt:")
    print(f"    (A) TRÍCH KHUNG (ffmpeg) : {_so(A):>8} giây  "
          f"= {_so(100 * A / max(tong, 1e-9), 1)}%")
    print(f"    (B) ĐỢI API (tuần tự)    : {_so(B):>8} giây  "
          f"= {_so(100 * B / max(tong, 1e-9), 1)}%")
    print(f"    (C) ĐỢI API (song song)  : {_so(C):>8} giây")
    if C > 0 and ok_ss == len(lo):
        print(f"\n  SONG SONG NHANH HƠN {_so(B / C)}x ở phần đợi API")
        print(f"  Tổng nếu áp dụng: {_so(A + C)} giây "
              f"(trước {_so(tong)} giây) = {_so((A + B) / max(A + C, 1e-9))}x")
    else:
        print(f"\n  SONG SONG KHÔNG DÙNG ĐƯỢC: {len(lo) - ok_ss} lượt lỗi")
        for x in loi_ss[:3]:
            print("    ·", x)
    print(f"\n  Suy ra cho 1 video ĐẦY ĐỦ ({VD._CAP} khung / "
          f"{(VD._CAP + VD._BATCH - 1) // VD._BATCH} lượt):")
    n_l = (VD._CAP + VD._BATCH - 1) // VD._BATCH
    a_full = statistics.median(t_kh) * VD._CAP
    b_full = statistics.median(t_api) * n_l
    c_full = max(ket[i][0] for i in ket) if ket else 0.0
    print(f"    tuần tự  : {_so(a_full + b_full)} giây "
          f"(khung {_so(a_full)} + API {_so(b_full)})")
    print(f"    song song: {_so(a_full + c_full)} giây "
          f"(khung {_so(a_full)} + API {_so(c_full)})")
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    finally:
        import shutil
        shutil.rmtree(_SB, ignore_errors=True)
    sys.exit(rc)
