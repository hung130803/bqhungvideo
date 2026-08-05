# -*- coding: utf-8 -*-
"""TẢI + GỘP KHO TIẾNG ĐỘNG CC0 vào app, CÓ KHOÁ DUNG LƯỢNG.

Chạy 1 lần trên máy dev (không phải lúc chạy app):
    python tools/fetch_sfx.py            # xem trước, KHÔNG ghi gì
    python tools/fetch_sfx.py --ghi      # tải + gộp thật vào app/assets/sfx

VÌ SAO PHẢI CÓ FILE NÀY (đo thật 05/08/2026):
    kho WAV hiện tại  43 file = 1 598 KB (37,2 KB/file)
    cùng số file Opus 32k mono =    75 KB ( 1,7 KB/file)  ← nhẹ hơn 21 lần
    => mở kho lên 300 file bằng Opus vẫn chỉ ~0,5 MB, tức TO GẤP 7 mà NHẸ HƠN 3 LẦN
    bản .exe cài cho nhân viên.

NGUỒN: chỉ lấy kho **CC0 / public domain** (Kenney.nl — ghi rõ CC0, không cần
ghi nguồn, được dùng thương mại). KHÔNG lấy loại "free nhưng phải credit" vì
video đăng hàng loạt không ai ghi credit được. Mỗi lượt tải ghi lại nguồn +
giấy phép vào app/assets/sfx/NGUON.md để về sau chứng minh được.

KHÔNG XOÁ file WAV đang có: chúng do tools/gen_sfx.py sinh (whoosh/riser/drone
tổng hợp — Kenney không có loại này). File tải về chỉ THÊM vào, và app đọc cả
2 loại (xem _list_sfx_files / _pick_sfx_by_category trong ffmpeg_utils.py).
"""
from __future__ import annotations

import argparse
import io
import json
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SFX_DIR = ROOT / "app" / "assets" / "sfx"
FFMPEG = str(ROOT / "bin" / "ffmpeg.exe")
FFPROBE = str(ROOT / "bin" / "ffprobe.exe")
_NO_WIN = 0x08000000 if sys.platform == "win32" else 0

#: TRẦN DUNG LƯỢNG cho toàn bộ file TẢI VỀ (không tính WAV tự sinh). Vượt là
#: dừng, không âm thầm phình bản cài.
TRAN_KB = 900
#: TRẦN TỪNG NHÓM: lượt đầu không có trần này ra 134 impact / 74 reveal mà
#: transition chỉ 40, comedy 0 (kho Kenney nghiêng hẳn về game UI + va đập).
#: Kho lệch = 300 kênh vẫn nghe ra trùng tiếng. Ép đều để ĐA DẠNG thật.
TRAN_NHOM = 30
#: file dùng được cho video ngắn: xung/hiệu ứng, KHÔNG lấy tiếng dài/ambience
DAI_MIN, DAI_MAX = 0.05, 2.5
#: bitrate kho: Opus 32k mono — đo thật 1,7 KB/file, tai không phân biệt được
#: với WAV ở loại xung ngắn phát dưới lời nói.
OPUS_KBPS = 32

#: Kho CC0 của Kenney (slug trang -> nhóm hữu ích). Link .zip có mã băm nên
#: phải dò từ trang, không hard-code (link đổi là hỏng).
KHO = [
    "impact-sounds", "ui-audio", "interface-sounds", "digital-audio",
    "sci-fi-sounds", "casino-audio", "music-jingles",
]
#: Xếp file vào 10 nhóm app đang dùng (SFX_CATEGORIES trong ffmpeg_utils.py:813)
#: theo TỪ KHOÁ trong tên file. Thứ tự có ý nghĩa: khớp trước thắng.
LUAT = [
    ("impact", ("impact", "hit", "punch", "explosion", "boom", "thud", "slam",
                "crash", "metal_", "impactplate", "impactwood")),
    ("pop", ("click", "switch", "bong", "tick", "select", "toggle", "tap",
             "pop", "blip", "minimize", "maximize")),
    ("reveal", ("confirmation", "confirm", "question", "jingle", "chime",
                "bell", "coin", "reward", "success", "achievement", "star")),
    ("comedy", ("bounce", "boing", "spring", "cartoon", "funny", "wobble",
                "silly")),
    ("scratch", ("scratch", "static", "glitch", "error", "wrong", "denied",
                 "buzz", "noise")),
    ("transition", ("whoosh", "swoosh", "swipe", "woosh", "air", "swing",
                    "phaser", "laser", "zap", "beam")),
    ("riser", ("riser", "rise", "buildup", "charge", "powerup", "power_up")),
    ("suspense", ("drone", "ambient", "tension", "dark", "low", "sub")),
    ("drumroll", ("drum", "roll", "snare")),
    ("sad", ("sad", "fail", "lose", "gameover", "game_over", "negative")),
]
#: BỎ HẲN: vô dụng cho video ngắn (đo: kho Kenney impact có 130 file mà 60 file
#: là tiếng bước chân trên thảm/tuyết -> không dùng được, chỉ làm phình kho).
LOAI_BO = ("footstep", "foot_", "walk", "run_", "jump", "cloth", "handle",
           "drawer", "door", "engine", "loop", "music_", "song")


def _tai(url: str, giay: int = 90) -> bytes:
    r = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(r, timeout=giay) as f:
        return f.read()


def link_zip(slug: str) -> str:
    """Dò link .zip thật từ trang kho (link có mã băm, đổi theo thời gian)."""
    html = _tai(f"https://kenney.nl/assets/{slug}", 40).decode("utf-8", "replace")
    m = re.findall(r'https://kenney\.nl/media/pages/assets/[^"\']+\.zip', html)
    return m[0] if m else ""


def nhom_cua(ten: str) -> str:
    t = ten.lower()
    for nhom, tu in LUAT:
        if any(k in t for k in tu):
            return nhom
    return ""


def do_dai(p: Path) -> float:
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True, creationflags=_NO_WIN)
    try:
        return float((r.stdout or "0").strip())
    except ValueError:
        return 0.0


def sang_opus(src: Path, dst: Path) -> bool:
    """Chuẩn hoá âm lượng + mono 48k + Opus. Trả True nếu ra file dùng được."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src),
         "-ac", "1", "-ar", "48000",
         # san đều rồi ép đỉnh -0,5 dB: tiếng động không được to hơn lời nói
         "-af", "dynaudnorm=f=100:g=5,alimiter=limit=0.9,volume=0.9",
         "-c:a", "libopus", "-b:a", f"{OPUS_KBPS}k", "-vbr", "on",
         "-application", "audio", str(dst)],
        capture_output=True, text=True, creationflags=_NO_WIN)
    return r.returncode == 0 and dst.exists() and dst.stat().st_size > 200


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ghi", action="store_true",
                    help="gộp thật vào app/assets/sfx (mặc định chỉ xem trước)")
    ap.add_argument("--tran-kb", type=int, default=TRAN_KB)
    ap.add_argument("--nen-kho-cu", action="store_true",
                    help="nén luôn 43 WAV tự sinh sang Opus (1598 KB -> ~75 KB)")
    a = ap.parse_args()
    tam = ROOT / "_sfx_tam"
    if tam.exists():
        shutil.rmtree(tam, ignore_errors=True)
    tam.mkdir()
    cu = sorted(SFX_DIR.rglob("*.*"))
    cu_kb = sum(f.stat().st_size for f in cu) / 1024
    print(f"kho hiện có: {len(cu)} file = {cu_kb:.0f} KB")
    print(f"trần cho phần TẢI VỀ: {a.tran_kb} KB · Opus {OPUS_KBPS}k mono\n")

    nguon_log, dem = [], Counter()
    tong_kb = 0.0
    bo_dai = bo_nhom = bo_loai = trung = du_nhom = 0
    da_co = {p.stem for p in cu}
    for slug in KHO:
        try:
            url = link_zip(slug)
            if not url:
                print(f"  ✗ {slug}: không dò được link .zip")
                continue
            raw = _tai(url)
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ {slug}: {type(e).__name__} {e}")
            continue
        z = zipfile.ZipFile(io.BytesIO(raw))
        ten_ok = [n for n in z.namelist()
                  if n.lower().endswith((".ogg", ".wav", ".mp3", ".flac"))]
        lay = 0
        for n in sorted(ten_ok):
            base = Path(n).stem
            low = base.lower()
            if any(k in low for k in LOAI_BO):
                bo_loai += 1
                continue
            nhom = nhom_cua(base)
            if not nhom:
                bo_nhom += 1
                continue
            if dem[nhom] >= TRAN_NHOM:      # nhóm đã đủ -> nhường chỗ nhóm khác
                du_nhom += 1
                continue
            moi = f"k_{slug.replace('-', '')}_{base}"[:60]
            if moi in da_co:
                trung += 1
                continue
            src = tam / Path(n).name
            src.write_bytes(z.read(n))
            d = do_dai(src)
            if not (DAI_MIN <= d <= DAI_MAX):
                bo_dai += 1
                src.unlink(missing_ok=True)
                continue
            dst = tam / "ra" / nhom / f"{moi}.opus"
            if not sang_opus(src, dst):
                src.unlink(missing_ok=True)
                continue
            kb = dst.stat().st_size / 1024
            if tong_kb + kb > a.tran_kb:
                print(f"  ⚠ ĐỦ TRẦN {a.tran_kb} KB -> dừng lấy thêm")
                break
            tong_kb += kb
            dem[nhom] += 1
            da_co.add(moi)
            lay += 1
            src.unlink(missing_ok=True)
        nguon_log.append((slug, url, len(ten_ok), lay))
        print(f"  ✓ {slug}: {len(ten_ok)} file trong kho -> lấy {lay}")
        if tong_kb >= a.tran_kb:
            break

    print(f"\nlọc bỏ: {bo_loai} không dùng được (bước chân/loop/nhạc) · "
          f"{bo_nhom} không rõ nhóm · {bo_dai} sai độ dài · {trung} trùng tên · "
          f"{du_nhom} bỏ vì nhóm đã đủ {TRAN_NHOM}")
    print(f"lấy được: {sum(dem.values())} file = {tong_kb:.0f} KB "
          f"({tong_kb/max(1,sum(dem.values())):.1f} KB/file)")
    print("theo nhóm: " + " · ".join(f"{k} {v}" for k, v in sorted(dem.items())))
    print(f"\nKHO SAU KHI GỘP: {len(cu) + sum(dem.values())} file = "
          f"{cu_kb + tong_kb:.0f} KB (hiện {cu_kb:.0f} KB)")

    if not a.ghi:
        print("\n(xem trước — CHƯA ghi gì vào app. Thêm --ghi để gộp thật)")
        shutil.rmtree(tam, ignore_errors=True)
        return 0
    n = 0
    for f in (tam / "ra").rglob("*.opus"):
        dst = SFX_DIR / f.parent.name / f.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dst)
        n += 1
    (SFX_DIR / "NGUON.md").write_text(
        "# Nguồn kho tiếng động\n\n"
        "## Tự sinh (không bản quyền)\n"
        "`tools/gen_sfx.py` — sinh bằng ffmpeg lavfi (whoosh/riser/drone/...).\n\n"
        "## Tải về — giấy phép CC0 1.0 (public domain)\n"
        "Nguồn: Kenney.nl — CC0, dùng thương mại, KHÔNG cần ghi nguồn.\n"
        "Chuẩn hoá: mono 48 kHz, dynaudnorm + alimiter đỉnh −0,9, "
        f"Opus {OPUS_KBPS} kbps.\n\n"
        + "\n".join(f"- `{s}` — {u}  (kho {t} file, lấy {l})"
                    for s, u, t, l in nguon_log)
        + f"\n\nGộp lần này: {n} file, {tong_kb:.0f} KB.\n",
        encoding="utf-8")
    print(f"\nĐÃ GỘP {n} file vào {SFX_DIR}")
    print(f"ghi nguồn/giấy phép: {SFX_DIR / 'NGUON.md'}")
    shutil.rmtree(tam, ignore_errors=True)
    print(json.dumps(dict(dem), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
