# -*- coding: utf-8 -*-
"""MỞ RỘNG KHO NHẠC NỀN — CHỈ NHẠC CC0 (02/11/2026).

Anh Hùng: *"thêm càng nhiều nhạc nền càng tốt ... đảm bảo không to, không lỗi"*.
Kho cũ 14 bài (OpenGameArt, CC0). FreePD (public domain) ĐÃ ĐÓNG CỬA (đo
02/11/2026: trang chủ ghi "Site Closed") nên nguồn còn lại là OpenGameArt —
lọc `field_art_licenses_tid=4` (CC0) VÀ mở từng trang kiểm lại khối giấy phép
có chữ CC0 (bộ lọc tìm kiếm không phải bằng chứng).

LOẠI (đây là nhạc NỀN dưới lời nói của kênh drama/crime người thật):
  * nhạc game 8-bit/chiptune/NES, đánh boss, metal — sai chất video người thật;
  * có LỜI HÁT / giọng (vocal, song, lyrics, choir) — đè đúng giọng nói;
  * gói .zip (nhiều bài, không kiểm được từng bài), file < 30 s hoặc > 7 phút.

    python tools/tai_nhac_cc0.py <thư_mục_tạm> dò       # ghi ung_vien.json
    python tools/tai_nhac_cc0.py <thư_mục_tạm> chọn     # gán tâm trạng theo thẻ
    python tools/tai_nhac_cc0.py <thư_mục_tạm> tải      # tải file gốc
    python tools/tai_nhac_cc0.py <thư_mục_tạm> ghi      # chuẩn hoá vào kho
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KHO = ROOT / "app" / "assets" / "music"
FF = str(ROOT / "bin" / "ffmpeg.exe")
FP = str(ROOT / "bin" / "ffprobe.exe")
NW = 0x08000000 if sys.platform == "win32" else 0
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/130 Safari/537.36"}

#: tâm trạng (khớp `catalog.json`) -> từ khoá tìm kiếm
TU_KHOA = {
    "calm": ["calm", "ambient", "relaxing", "chill", "lofi", "peaceful"],
    "emotional": ["sad", "emotional", "melancholy", "piano", "heartfelt"],
    "mystery": ["mystery", "suspense", "investigation", "dark ambient",
                "mysterious"],
    "tension": ["tension", "tense", "thriller", "suspenseful"],
    "bright": ["happy", "upbeat", "cheerful", "positive"],
    "playful": ["funny", "comedy", "quirky", "silly"],
}
#: CHỈ 6 tâm trạng `music_library.MOODS` — tâm trạng lạ làm `catalog()` NÉM
#: và hỏng luôn đường dựng phóng sự (đọc mã 02/11/2026 trước khi thêm).
#: "inspiring/uplifting" gộp vào `bright`.
TU_KHOA["bright"] += ["inspiring", "uplifting", "hopeful"]
#: chữ trong TIÊU ĐỀ / THẺ -> loại
CAM = ("chiptune", "8-bit", "8bit", "8 bit", "nes ", "gameboy", "boss",
       "battle", "metal", "vocal", "vocals", "song with", "lyrics", "singing",
       "choir", "rap", "dubstep", "chip tune", "retro game", "16-bit",
       "16bit", "jingle", "victory", "game over", "fanfare")
DAI_MIN, DAI_MAX = 30.0, 420.0
#: kho cũ là Opus ~100 kb/s stereo (~0,7-2 MB/bài). Nhạc nền nằm DƯỚI lời nói
#: ~18 dB nên 48 kb/s stereo là đủ; cắt tối đa 120 s (~0,7 MB/bài —
#: 90 bài mới ~65 MB, bộ cài/bản tự cập nhật phải tải thêm chừng ấy) (clip dài hơn thì app
#: lặp bài bằng `-stream_loop`, có mờ vào/ra ở chỗ nối vòng).
KBPS, CAT_TOI_DA = 48, 120.0
#: mức chuẩn của KHO (LUFS) — app tự hạ tiếp theo mức lời của từng clip.
DICH_LUFS = -20.0


def _tai(url: str, giay: int = 60) -> bytes:
    r = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(r, timeout=giay) as f:
        return f.read()


def _tim(tu: str) -> list:
    q = urllib.parse.urlencode({
        "keys": tu, "field_art_type_tid[]": "12",
        "field_art_licenses_tid[]": "4", "sort_by": "count",
        "sort_order": "DESC", "items_per_page": "48"})
    h = _tai("https://opengameart.org/art-search-advanced?" + q).decode(
        "utf-8", "replace")
    return sorted(set(re.findall(r'href="(/content/[^"#?]+)"', h)) -
                  {"/content/faq"})


def _doc_trang(duong: str) -> dict | None:
    h = _tai("https://opengameart.org" + duong).decode("utf-8", "replace")
    # khối giấy phép = từ nhãn License(s) tới khối Collections kế tiếp; lấy
    # TÊN từng giấy phép (một trang có thể cho chọn nhiều giấy phép).
    i = h.find("field-name-field-art-licenses")
    j = h.find("field-name-collect", i) if i >= 0 else -1
    khoi = h[i:j if j > i else i + 3000] if i >= 0 else ""
    ten_gp = re.findall(r"license-name'>([^<]+)<", khoi)
    if not any(x.strip().upper() == "CC0" for x in ten_gp):
        return None
    tit = re.search(r"<title>(.*?)\s*\|\s*OpenGameArt", h, re.S)
    tieu_de = html.unescape(tit.group(1)).strip() if tit else duong
    tg = re.search(r'field-name-author-submitter.*?<a[^>]*>(.*?)</a>', h, re.S)
    the = " ".join(re.findall(r'field_art_tags_tid=[^"]*"[^>]*>([^<]+)<',
                              h)).lower()
    files = re.findall(r'href="(https://opengameart\.org/sites/default/files/'
                       r'[^"]+\.(?:mp3|ogg|wav|flac))"', h, re.I)
    return {"trang": "https://opengameart.org" + duong, "tieu_de": tieu_de,
            "tac_gia": html.unescape(tg.group(1)).strip() if tg else "",
            "the": the, "files": files,
            "license": "CC0-1.0", "giay_phep_trang": ten_gp}


def do(tam: Path) -> None:
    ung: dict = {}
    for mood, tus in TU_KHOA.items():
        for tu in tus:
            try:
                ds = _tim(tu)
            except Exception as e:  # noqa: BLE001
                print("  !! tìm hỏng", tu, e)
                continue
            for d in ds:
                ung.setdefault(d, {"mood": mood, "tu": tu})
            print(f"  {mood:<10} {tu:<14} {len(ds)} trang")
            time.sleep(0.5)
    kq = []
    for i, (d, m) in enumerate(sorted(ung.items())):
        try:
            t = _doc_trang(d)
        except Exception as e:  # noqa: BLE001
            print("  !! trang hỏng", d, e)
            continue
        time.sleep(0.3)
        if not t or not t["files"]:
            continue
        chu = (t["tieu_de"] + " " + t["the"] + " " + d).lower()
        if any(x in chu for x in CAM):
            continue
        t.update(m)
        kq.append(t)
        print(f"  [{i}] {m['mood']:<10} {t['tieu_de'][:50]}")
    (tam / "ung_vien.json").write_text(
        json.dumps(kq, ensure_ascii=False, indent=1), "utf-8")
    print("ứng viên:", len(kq))


def _dai(p: Path) -> float:
    r = subprocess.run([FP, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True,
                       text=True, creationflags=NW)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


#: file gốc lớn hơn mức này (thường là WAV/FLAC hàng chục MB) thì bỏ — lượt
#: tải đầu đo được 6 bài / 20 phút vì toàn file WAV lớn trên máy chủ chậm.
TRAN_MB_GOC = 15.0


def _co_mb(url: str) -> float:
    try:
        r = urllib.request.Request(url, headers=UA, method="HEAD")
        with urllib.request.urlopen(r, timeout=30) as f:
            return int(f.headers.get("Content-Length") or 0) / 1e6
    except Exception:  # noqa: BLE001
        return -1.0


def _tai_mot(t: dict, goc: Path) -> str:
    # ưu tiên file NÉN (ogg/mp3) — cùng bài, nhẹ hơn WAV/FLAC hàng chục lần
    ds = sorted(t["files"], key=lambda u: (
        0 if u.lower().endswith((".ogg", ".mp3")) else 1))
    for f in ds:
        mb = _co_mb(f)
        if mb > TRAN_MB_GOC:
            continue
        dst = goc / (hashlib.sha1(f.encode()).hexdigest()[:12] +
                     Path(urllib.parse.unquote(f)).suffix.lower())
        if not dst.exists():
            try:
                b = _tai(f, 180)
            except Exception as e:  # noqa: BLE001
                return f"tải hỏng {e}"
            tmp = dst.with_suffix(dst.suffix + ".tmp")
            tmp.write_bytes(b)
            tmp.replace(dst)
        t["goc"] = str(dst)
        t["dai_goc"] = _dai(dst)
        return ""
    return "không có file nén <= %.0f MB" % TRAN_MB_GOC


def tai(tam: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor
    kq = json.loads((tam / "chon.json").read_text("utf-8"))
    goc = tam / "goc"
    goc.mkdir(exist_ok=True)
    with ThreadPoolExecutor(4) as ex:
        for t, loi in zip(kq, ex.map(lambda x: _tai_mot(x, goc), kq)):
            if loi:
                print(f"  !! {t['tieu_de'][:40]}: {loi}")
            else:
                print(f"  {t['dai_goc']:6.1f}s {t['tieu_de'][:50]}", flush=True)
    (tam / "chon.json").write_text(
        json.dumps(kq, ensure_ascii=False, indent=1), "utf-8")


def _lufs(p: str) -> float | None:
    r = subprocess.run([FF, "-hide_banner", "-i", p, "-af",
                        "loudnorm=print_format=json", "-f", "null", "-"],
                       capture_output=True, creationflags=NW)
    t = r.stderr.decode("utf-8", "replace")
    try:
        return float(json.loads(t[t.rindex("{"):t.rindex("}") + 1])["input_i"])
    except (ValueError, KeyError):
        return None


def _id(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")
    return ("o2_" + s)[:40]


def ghi(tam: Path) -> None:
    kq = json.loads((tam / "chon.json").read_text("utf-8"))
    cat = json.loads((KHO / "catalog.json").read_text("utf-8"))
    co = {t["file"] for t in cat["tracks"]}
    co_nguon = {t.get("source") for t in cat["tracks"]}
    them = 0
    dong_md: list = []
    for t in kq:
        g = t.get("goc")
        d = float(t.get("dai_goc") or 0)
        if not g or not Path(g).exists() or not (DAI_MIN <= d <= DAI_MAX):
            continue
        if t["trang"] in co_nguon:
            continue                       # bài đã có trong kho
        tid = _id(t["tieu_de"])
        ten = tid + ".opus"
        if ten in co:
            continue
        lu = _lufs(g)
        if lu is None or lu < -45:
            print("  bỏ (đo không được / gần câm):", t["tieu_de"])
            continue
        dai = min(d, CAT_TOI_DA)
        mo = max(0.0, dai - 3.0)
        dst = KHO / ten
        r = subprocess.run(
            [FF, "-y", "-hide_banner", "-loglevel", "error", "-i", g,
             "-t", f"{dai:.3f}",
             "-af", f"volume={DICH_LUFS - lu:.2f}dB,"
                    f"afade=t=in:d=1.5,afade=t=out:st={mo:.3f}:d=3,"
                    "alimiter=limit=0.7:level=0",
             "-ac", "2", "-ar", "48000", "-c:a", "libopus",
             "-b:a", f"{KBPS}k", "-vbr", "on", str(dst)],
            capture_output=True, creationflags=NW)
        if r.returncode != 0 or not dst.exists():
            print("  !! chuẩn hoá hỏng:", t["tieu_de"])
            continue
        cat["tracks"].append({
            "id": tid, "title": t["tieu_de"], "mood": t["mood"],
            "author": t["tac_gia"], "source": t["trang"],
            "download": t["files"][0], "license": "CC0-1.0", "file": ten,
            "duration": round(_dai(dst), 3),
            "sha256": hashlib.sha256(dst.read_bytes()).hexdigest()})
        co.add(ten)
        them += 1
        dong_md.append(f"- {t['tieu_de']} — {t['tac_gia']} — CC0 1.0 — "
                       f"{t['trang']}")
        print(f"  + {t['mood']:<10} {ten}")
    # MỨC THẬT (LUFS) của MỌI bài, kể cả 14 bài cũ: app tính âm lượng nhạc
    # theo con số này (`nhac_tu_dong.he_so_db`) — không đoán.
    for t in cat["tracks"]:
        if "lufs" not in t:
            lu = _lufs(str(KHO / t["file"]))
            if lu is not None:
                t["lufs"] = round(lu, 2)
    (KHO / "catalog.json").write_text(
        json.dumps(cat, ensure_ascii=False, indent=2), "utf-8")
    if dong_md:
        md = (KHO / "NGUON.md").read_text("utf-8")
        nl = chr(10)
        md += (nl + "## Lượt 2 (02/11/2026, `tools/tai_nhac_cc0.py`) — "
               "OpenGameArt, mỗi trang đã kiểm khối giấy phép có CC0"
               + nl + nl + nl.join(dong_md) + nl)
        (KHO / "NGUON.md").write_text(md, "utf-8")
    print("đã thêm:", them, "· tổng:", len(cat["tracks"]))


#: GÁN LẠI TÂM TRẠNG THEO THẺ CỦA CHÍNH BÀI (không theo từ khoá tìm kiếm — tìm
#: "piano" ra cả "Haunting piano" thẻ horror/despair). Thứ tự = ưu tiên.
THE_MOOD = [
    ("tension", ("tense", "tension", "suspense", "thriller", "horror",
                 "scary", "action", "chase", "danger")),
    ("mystery", ("mystery", "mysterious", "creepy", "spooky", "investigation",
                 "noir", "dark")),
    ("emotional", ("sad", "emotional", "melancholy", "melancholic",
                   "heartfelt", "sorrow", "grief")),
    ("playful", ("funny", "silly", "comedy", "quirky", "comic", "fun")),
    ("bright", ("happy", "upbeat", "positive", "uplifting", "hopeful",
                "cheerful", "joyful")),
    ("calm", ("calm", "peaceful", "relaxing", "relax", "chill", "lofi",
              "lo-fi", "soft", "ambient", "gentle")),
]
NANG_MOOD = {"tension", "mystery", "emotional"}
NHE_MOOD = {"playful", "bright"}
#: thẻ chất GAME rõ — sai chất video người thật
THE_BO = ("medieval", "tavern", "racing", "techno", "retro", "midi", "vgm",
          "menu", "boss", "battle", "dungeon", "platformer", "arcade")
MOI_MOOD = 15


def chon(tam: Path) -> None:
    kq = json.loads((tam / "ung_vien.json").read_text("utf-8"))
    cat = json.loads((KHO / "catalog.json").read_text("utf-8"))
    co_nguon = {t.get("source") for t in cat["tracks"]}
    nhom: dict = {}
    bo = {"mâu thuẫn": 0, "chất game": 0, "không thẻ tâm trạng": 0}
    for t in kq:
        if t["trang"] in co_nguon:
            continue
        the = set(re.findall(r"[a-z\-]+", (t["the"] + " " +
                                            t["tieu_de"]).lower()))
        if the & set(THE_BO):
            bo["chất game"] += 1
            continue
        khop = [m for m, tu in THE_MOOD if the & set(tu)]
        if not khop:
            bo["không thẻ tâm trạng"] += 1
            continue
        if set(khop) & NANG_MOOD and set(khop) & NHE_MOOD:
            bo["mâu thuẫn"] += 1
            continue
        m = khop[0]
        diem = len(the & set(dict(THE_MOOD)[m]))
        t["mood"] = m
        t["diem"] = diem
        nhom.setdefault(m, []).append(t)
    ra = []
    for m, ds in nhom.items():
        ds.sort(key=lambda x: (-x["diem"], x["trang"]))
        ra += ds[:MOI_MOOD]
        print(f"  {m:<10} {len(ds)} bài hợp -> lấy {min(len(ds), MOI_MOOD)}")
    print("  loại:", bo)
    (tam / "chon.json").write_text(
        json.dumps(ra, ensure_ascii=False, indent=1), "utf-8")
    print("đã chọn:", len(ra))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    tam = Path(sys.argv[1])
    tam.mkdir(parents=True, exist_ok=True)
    {"dò": do, "chọn": chon, "tải": tai, "ghi": ghi}[sys.argv[2]](tam)
