# -*- coding: utf-8 -*-
"""CỔNG 21 — Ô NỀN SÁNG CHẠY THEO TỪ ĐANG NÓI (mode 'hlbox', kiểu Submagic).

CÁCH DỰNG: mỗi từ sinh 2 dòng cùng mốc — LỚP 0 = miếng ô (chữ tô ĐẶC cùng màu
viền dày -> viên thuốc bo góc; các từ khác `\\alpha&HFF&` ẩn đi), LỚP 1 = CHỮ vẽ
đè lên. Bản đầu nhúng ô GIỮA DÒNG chung với chữ và đã sai: viền đen của từ BÊN
CẠNH đè lên ô (libass gộp mọi viền của 1 dòng vào 1 lớp) -> ô bị chặt phẳng 1
cạnh, cỡ chữ lớn thì 2 từ dính liền nhau.

CÁC LỖI THẬT ĐÃ BẮT ĐƯỢC (rà đối kháng 05/08/2026) — mỗi lỗi 1 mục canh:
  B1 `cap_ow` >= 0,17 làm VIỀN CHỮ dày hơn Ô -> ô bị nuốt, chữ thành cục đen.
  B2 màu chữ user chọn (`color`) bị bỏ hẳn, mà XEM TRƯỚC lại hiện đúng màu ->
     đúng loại lỗi "chọn X ra Y".
  B3 cỡ chữ lớn + chữ HOA -> 4 dòng, BỊ CẮT ĐÁY KHUNG (kiểu cũ chỉ 2 dòng).
  C4 "bỏ dòng < 60ms" làm mất 4-6% chữ với lời nói nhanh, và mất GẦN HẾT chữ
     khi bản chép lời không có mốc từng-từ (bước 0,05s -> 1/20 dòng).
  C5 `delay` âm làm mất dòng đầu.  C8 ô sáng bọc dấu phẩy.  C9 CJK bị chèn
     dấu cách.  C10 phồng NGANG làm cả khối chữ xuống dòng lại trong 160ms.
  C3' chọn hlbox cho "Chữ AI đọc" -> chữ Narrate ra TRẮNG, lẫn với lời gốc.

BẤT BIẾN SỐNG CÒN: 18 preset CŨ phải ra file .ass GIỐNG TỪNG BYTE bản trước
(anh Hùng đang chạy sản xuất 200-300 kênh bằng preset cũ) — mục 12 so với
`git show HEAD:app/core/captions.py`.
"""
import importlib.util
import os
import re
import subprocess
import sys
import tempfile

T = tempfile.mkdtemp(prefix="hlbox_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "s.ini")
REPO = r"D:\claude\ai-content-studio"
sys.path.insert(0, REPO)
import _test_guard  # noqa: E402,F401 - CẤM test mở Explorer/trình phát máy user

from app.core import captions as C  # noqa: E402

FAIL: list[str] = []
FF = os.path.join(REPO, "bin", "ffmpeg.exe")
KIEU = ["Ô sáng chạy từ (đa màu)", "Ô sáng chạy từ (vàng)",
        "Ô sáng chạy từ (xanh neon)", "Ô sáng chạy từ (xanh lá)",
        "Ô sáng chạy từ (hồng)", "Ô sáng chạy từ (đỏ)"]
W, H = 1080, 1920
SIZE = int(H * 0.052)
T0, DT = 0.2, 0.36
TU = ["chuyện", "này", "không", "ai", "dám", "kể", "cho", "bạn", "nghe",
      "nhưng", "nó", "đổi", "hết", "mọi", "thứ"]
RE_TAG = re.compile(r"\{[^}]*\}")


def kiem(ok, nhan, ct=""):
    print(("  ✓ " if ok else "  ✗ ") + nhan + ("" if ok else f"  << {ct}"))
    if not ok:
        FAIL.append(nhan)


def words(n=9, buoc=DT, tu=None):
    t, ws = T0, []
    for i in range(n):
        w = (tu or TU)[i % len(tu or TU)]
        ws.append({"start": t, "end": t + buoc - 0.03, "word": w})
        t += buoc
    return ws, t + 0.5


def dung(preset, n=9, buoc=DT, tu=None, mod=None, **kw):
    ws, dur = words(n, buoc, tu)
    p = os.path.join(T, re.sub(r"\W+", "_", preset)[:40] + f"_{n}_{int(buoc*1000)}"
                     + f"_{abs(hash(str(sorted(kw.items()))))%9999}.ass")
    ok = (mod or C).build_ass(ws, [(0.0, dur)], p, out_w=W, out_h=H,
                             font="Montserrat", size=SIZE, ny=0.70,
                             preset=preset, **kw)
    txt = open(p, encoding="utf-8").read() if ok else ""
    dong = [ln for ln in txt.splitlines() if ln.startswith("Dialogue:")]
    return ok, txt, dong, dur, p


def tach(ln):
    """(layer, start, end, body) của 1 dòng Dialogue."""
    c = ln.split(",", 9)
    return int(c[0].split(":")[1]), c[1].strip(), c[2].strip(), c[9]


def giay(hms):
    h, m, s = hms.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def cap(dong):
    """Gom thành cặp (dòng ô lớp 0, dòng chữ lớp 1) theo mốc."""
    ra, i = [], 0
    while i + 1 < len(dong):
        a, b = tach(dong[i]), tach(dong[i + 1])
        if a[0] == 0 and b[0] == 1 and a[1] == b[1] and a[2] == b[2]:
            ra.append((a, b))
            i += 2
        else:
            i += 1
    return ra


def tu_sang(body_o):
    """(màu ô, thứ tự từ được chiếu sáng) trong dòng LỚP 0."""
    m = re.search(r"\{\\alpha&H00&\\1c(&H[0-9A-Fa-f]{8})\\3c(&H[0-9A-Fa-f]{8})"
                  r"\\bord(\d+)", body_o)
    if not m:
        return None
    vt = len(RE_TAG.sub("", body_o[:m.start()]).split())
    return (m.group(1).upper(), m.group(2).upper(), int(m.group(3)), vt)


print("\n══ 1. Preset khai đúng ══")
for k in KIEU:
    p = C.CAPTION_PRESETS.get(k) or {}
    kiem(p.get("mode") == "hlbox" and bool(p.get("hl_palette")),
         f"{k}: mode=hlbox + có hl_palette", str(p))
kiem(len(C.CAPTION_PRESETS[KIEU[0]]["hl_palette"]) >= 5, "'đa màu' >= 5 màu")

print("\n══ 2. Cấu trúc 2 LỚP: ô ở dưới, chữ ở trên, cùng mốc ══")
ok, txt, dong, dur, ass_da = dung(KIEU[0])
cs = cap(dong)
kiem(len(cs) == 9 and len(dong) == 18,
     f"9 từ -> 9 cặp / 18 dòng (ra {len(cs)} cặp / {len(dong)} dòng)")
loi = []
for i, (o, chu) in enumerate(cs):
    s = tu_sang(o[3])
    if not s:
        loi.append((i, "không thấy ô"))
        continue
    mau_chu, mau_o, day, vt = s
    if mau_chu != mau_o:
        loi.append((i, "chữ lớp ô phải TÔ ĐẶC cùng màu viền -> mới thành miếng"))
    if vt != i % 3:                       # cụm 3 từ -> ô chạy 0,1,2 rồi cụm mới
        loi.append((i, f"ô ở từ thứ {vt}, mong {i % 3}"))
    if o[3].count("\\alpha&HFF&") != len(RE_TAG.sub("", o[3]).split()) - 1:
        loi.append((i, "lớp ô phải ẩn HẾT các từ khác"))
    if RE_TAG.sub("", o[3]).split() != RE_TAG.sub("", chu[3]).split():
        loi.append((i, "2 lớp phải CÙNG chữ (không thì ô lệch khỏi từ)"))
kiem(not loi, "mọi cặp: ô đặc + đúng vị trí + ẩn từ khác + 2 lớp cùng chữ",
     str(loi[:4]))
kiem(all("\\bord0" in chu[3] for o, chu in cs),
     "chữ trong ô KHÔNG viền dày (không thì chữ bệt trên ô)")

print("\n══ 3. Màu: đa màu · 1 màu · cùng từ cùng màu ══")
ms = [tu_sang(o[3])[1] for o, _ in cs]
kiem(len(set(ms)) >= 5, f"'đa màu': {len(set(ms))} màu/9 từ")
for k in KIEU[1:]:
    _, _, d1, _, _ = dung(k)
    s1 = {tu_sang(o[3])[1] for o, _ in cap(d1)}
    kiem(len(s1) == 1, f"{k}: đúng 1 màu ô", str(s1))
_, _, d3, _, _ = dung(KIEU[0], n=3)
theo_tu = {}
for o, _ in cap(d3):
    m, mo, _d, vt = tu_sang(o[3])
    theo_tu.setdefault(vt, set()).add(mo)
kiem(all(len(v) == 1 for v in theo_tu.values()) and len(theo_tu) == 3,
     "trong 1 cụm mỗi từ giữ NGUYÊN 1 màu (không nhấp nháy)", str(theo_tu))

print("\n══ 4. B1: user kéo 'độ dày viền' to -> ô KHÔNG bị viền nuốt ══")
for cap_ow in (0.0, 0.10, 0.17, 0.20, 0.30):
    _, t2, d2, _, _ = dung(KIEU[0], n=4, cap_ow=cap_ow)
    day_o = tu_sang(cap(d2)[0][0][3])[2]
    m = re.search(r"\\bord(\d+)\\shad", cap(d2)[0][1][3])
    day_chu = int(m.group(1)) if m else -1
    kiem(day_o >= day_chu + 4,
         f"cap_ow={cap_ow}: ô dày {day_o} > viền chữ {day_chu}")

print("\n══ 5. B2: 'Màu chữ' user chọn phải ĂN vào phụ đề ══")
# dùng màu KHÔNG có trong bảng màu ô, không thì không phân biệt được nguồn màu
_, t3, d3b, _, _ = dung(KIEU[0], n=4, color="#00FF88")
kiem("&H0088FF00" in t3, "color=#00FF88 -> mã màu có trong file .ass",
     t3[-300:][:160])
_, t3b, _, _, _ = dung(KIEU[0], n=4)
kiem("&H0088FF00" not in t3b, "không đặt color -> KHÔNG bị nhuộm oan")

print("\n══ 6. C4: lời nói NHANH / không có mốc từng-từ -> không mất chữ ══")
for buoc, ten in ((0.05, "bước 0,05s (chép lời không có mốc từ)"),
                  (0.03, "bước 0,03s (dày bất thường)"),
                  (0.36, "bước 0,36s (bình thường)")):
    _, _, d4, dur4, _ = dung(KIEU[0], n=20, buoc=buoc)
    c4 = cap(d4)
    phu = sum(giay(o[2]) - giay(o[1]) for o, _ in c4)
    tam = 20 * buoc      # thời lượng CÓ TIẾNG NÓI (không tính 0,2s im đầu)
    kiem(c4 and phu >= tam * 0.75,
         f"{ten}: {len(c4)} cặp, chữ hiện {phu:.2f}s / {tam:.2f}s tiếng nói")

print("\n══ 7. C5: delay ÂM không làm mất dòng ══")
for dl in (0.0, -0.15, -0.30, 0.20):
    _, _, d5, _, _ = dung(KIEU[0], n=5, delay=dl)
    kiem(len(cap(d5)) == 5, f"delay={dl}: đủ 5 cặp (ra {len(cap(d5))})")

print("\n══ 8. C8: KHÔNG chiếu ô lên dấu câu lẻ, chữ vẫn hiện ══")
ws_p = [{"start": 0.2, "end": 0.5, "word": "này"},
        {"start": 0.6, "end": 0.62, "word": ","},
        {"start": 0.7, "end": 1.0, "word": "thật"}]
p_p = os.path.join(T, "dau_cau.ass")
C.build_ass(ws_p, [(0.0, 2.0)], p_p, out_w=W, out_h=H, size=SIZE,
            preset=KIEU[0])
t_p = open(p_p, encoding="utf-8").read()
c_p = cap([l for l in t_p.splitlines() if l.startswith("Dialogue:")])
kiem(len(c_p) == 2, f"3 token (1 là dấu phẩy) -> 2 ô (ra {len(c_p)})")
kiem(all(RE_TAG.sub("", o[3]).split()[tu_sang(o[3])[3]] != ","
         for o, _ in c_p), "không ô nào bọc dấu phẩy")
kiem("," in RE_TAG.sub("", c_p[0][1][3]), "dấu phẩy VẪN hiện trong chữ")

print("\n══ 9. C9: Nhật/Trung không bị chèn dấu cách ══")
_, t_j, d_j, _, _ = dung(KIEU[0], n=4, tu=["これは", "誰も", "語らな", "かった"])
than_j = RE_TAG.sub("", cap(d_j)[0][1][3])
kiem(" " not in than_j.strip(), f"CJK nối liền: '{than_j}'")
_, t_v, d_v, _, _ = dung(KIEU[0], n=4)
kiem(" " in RE_TAG.sub("", cap(d_v)[0][1][3]),
     "tiếng Việt/Anh VẪN có dấu cách (không phá)")

print("\n══ 10. C10: phồng chữ KHÔNG làm đổi bề ngang (đỡ xuống dòng lại) ══")
kiem("\\fscx" not in txt, "không dùng \\fscx (phồng ngang) trong kiểu ô")
kiem("\\fscy105" in txt, "vẫn có phồng dọc nhẹ khi từ được chiếu")

print("\n══ 11. Mốc: không chồng, không lỗ, end>start ══")
mo = [(giay(o[1]), giay(o[2])) for o, _ in cs]
kiem(all(b > a for a, b in mo), "mọi cặp end > start")
kiem(all(mo[i][1] <= mo[i + 1][0] + 1e-6 for i in range(len(mo) - 1)),
     "không cặp nào chồng cặp kế (không 2 ô sáng cùng lúc)")
ho = [round(mo[i + 1][0] - mo[i][1], 3) for i in range(len(mo) - 1)
      if mo[i + 1][0] - mo[i][1] > 0.001]
kiem(not ho, f"không có LỖ giữa các cặp (lỗ: {ho})")

print("\n══ 12. BẤT BIẾN: 18 preset CŨ ra file GIỐNG TỪNG BYTE bản HEAD ══")
cu_py = os.path.join(T, "captions_cu.py")
r = subprocess.run(["git", "-C", REPO, "show", "HEAD:app/core/captions.py"],
                   capture_output=True)
open(cu_py, "wb").write(r.stdout)
spec = importlib.util.spec_from_file_location("captions_cu", cu_py)
CU = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CU)
khac = []
for ten in CU.CAPTION_PRESETS:
    for kw in ({}, {"cap_case": "upper", "hook": "GIẬT TÍT", "hook_dur": 1.5},
               {"color": "#00FF88", "cap_ow": 0.2, "delay": -0.1},
               {"extra_cues": [(0.4, 1.2, "ai kể", "word"),
                               (1.5, 2.4, "cả câu", "sent")],
                "narr_preset": "Karaoke hồng"}):
        _, a, _, _, _ = dung(ten, n=9, mod=C, **kw)
        _, b, _, _, _ = dung(ten, n=9, mod=CU, **kw)
        if a != b:
            khac.append(f"{ten}/{list(kw)[:2]}")
kiem(not khac, f"{len(CU.CAPTION_PRESETS)} preset cũ × 4 bộ tham số: "
               f"KHÔNG đổi 1 byte", str(khac[:5]))

print("\n══ 13. C3': hlbox làm 'Chữ AI đọc' -> vẫn phân biệt được lời AI ══")
ws_n, dur_n = words(6)
p_n = os.path.join(T, "narr.ass")
ok_n = C.build_ass(ws_n, [(0.0, dur_n)], p_n, out_w=W, out_h=H, size=SIZE,
                   preset="Vàng nhảy (TikTok)", narr_preset=KIEU[4],
                   extra_cues=[(0.5, 1.5, "ai kể đây", "word")])
t_n = open(p_n, encoding="utf-8").read()
st_n = [l for l in t_n.splitlines() if l.startswith("Style: Narrate")][0]
kiem(ok_n and ",&H00FFFFFF," not in st_n.split(",", 4)[3] + ",",
     f"màu chữ Narrate KHÔNG bị ra trắng: {st_n.split(',')[3]}")
kiem(sum(1 for l in t_n.splitlines() if ",Narrate," in l) == 1,
     "cue AI kể vẫn ra đúng 1 dòng Narrate")

print("\n══ 14. Đường RECAP (words rỗng, chỉ extra_cues) — không nổ ══")
p_r = os.path.join(T, "recap.ass")
ok_r = C.build_ass([], [(0.0, 6.0)], p_r, out_w=W, out_h=H, size=SIZE,
                   preset=KIEU[0],
                   extra_cues=[(0.5, 1.5, "câu một", "orig_word"),
                               (2.0, 3.0, "câu hai", "sent")])
n_r = sum(1 for l in open(p_r, encoding="utf-8") if l.startswith("Dialogue:"))
kiem(ok_r and n_r == 2, f"recap: {n_r} dòng, không nổ (LƯU Ý: đường recap "
                        f"KHÔNG có ô nền — đã báo anh Hùng)")

print("\n══ 15. Ca biên ══")
for n in (1, 2, 15, 40):
    ok_b, _, d_b, _, _ = dung(KIEU[0], n=n)
    kiem(ok_b and len(cap(d_b)) == n, f"{n} từ -> {len(cap(d_b))} cặp")
kiem(C.build_ass([], [(0, 5)], os.path.join(T, "rong.ass"),
                 preset=KIEU[0]) is False, "không từ nào -> False")
ws_x = [{"start": 1.0, "end": 0.5, "word": "LÙI"},
        {"start": 1.0, "end": 1.3, "word": "TRÙNG"},
        {"start": 2.0, "end": 2.4, "word": "x" * 40},
        {"start": 3.0, "end": 3.2, "word": "😀"},
        {"start": 4.0, "end": 4.2, "word": "  "}]
try:
    okx = C.build_ass(ws_x, [(0.0, 6.0)], os.path.join(T, "ban.ass"),
                      out_w=W, out_h=H, size=SIZE, preset=KIEU[0])
    kiem(bool(okx), "dữ liệu bẩn (mốc lùi/trùng/40 ký tự/emoji/rỗng) -> không nổ")
except Exception as e:  # noqa: BLE001
    kiem(False, "dữ liệu bẩn không nổ", repr(e))
_, _, d_h, _, _ = dung(KIEU[0], n=6, hook="CÂU GIẬT TÍT", hook_dur=1.5)
kiem(any(",Hook," in l for l in d_h) and len(cap(d_h)) >= 4,
     f"có HOOK: {len(cap(d_h))} cặp + 1 dòng Hook")
_, _, d_s2, _, _ = dung(KIEU[0], n=6)
kiem(len(cap(d_s2)) == 6, "1 đoạn liền: đủ cặp")
ws_2, _ = words(6)
p_2 = os.path.join(T, "hookfirst.ass")                # GHÉP NGƯỢC THỜI GIAN
ok2 = C.build_ass(ws_2, [(1.4, 2.2), (0.2, 1.0)], p_2, out_w=W, out_h=H,
                  size=SIZE, preset=KIEU[0])
c2 = cap([l for l in open(p_2, encoding="utf-8") if l.startswith("Dialogue:")])
m2 = [(giay(o[1]), giay(o[2])) for o, _ in c2]
kiem(ok2 and c2 and all(m2[i][1] <= m2[i + 1][0] + 1e-6
                        for i in range(len(m2) - 1)),
     f"hook-first (đoạn ngược thời gian): {len(c2)} cặp, không chồng mốc")

print("\n══ 16. B3: RENDER THẬT — chữ KHÔNG tràn đáy khung, ô đúng màu ══")
SW, SH = 540, 960
PAL = C.CAPTION_PRESETS[KIEU[0]]["hl_palette"]


def khung(ass, gio, nen="0x606060"):
    ra = os.path.join(T, "f.rgb")
    r = subprocess.run(
        [FF, "-y", "-v", "error", "-f", "lavfi", "-i",
         f"color=c={nen}:s={W}x{H}:d=20,fps=25", "-vf",
         f"ass={os.path.basename(ass)},scale={SW}:{SH}", "-ss", f"{gio:.2f}",
         "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", ra],
        capture_output=True, text=True, errors="replace",
        cwd=os.path.dirname(ass))
    return (open(ra, "rb").read() if r.returncode == 0 else None), r.stderr[:200]


def dem(buf, hexv, tol=38):
    h = hexv.lstrip("#")
    tr, tg, tb = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    n = sx = sy = 0
    mv = memoryview(buf)
    for i in range(0, len(buf), 3):
        if (abs(mv[i] - tr) <= tol and abs(mv[i + 1] - tg) <= tol
                and abs(mv[i + 2] - tb) <= tol):
            n += 1
            sx += (i // 3) % SW
            sy += (i // 3) // SW
    return n, (sx / n if n else 0, sy / n if n else 0)


def y_cuoi(buf, nen=(0x60, 0x60, 0x60), tol=26):
    """Hàng có pixel KHÁC nền thấp nhất -> chữ có bị cắt đáy khung không."""
    mv = memoryview(buf)
    for y in range(SH - 1, -1, -1):
        b = y * SW * 3
        for x in range(0, SW * 3, 3):
            if (abs(mv[b + x] - nen[0]) > tol or abs(mv[b + x + 1] - nen[1]) > tol
                    or abs(mv[b + x + 2] - nen[2]) > tol):
                return y
    return -1


tam = []
for k in (1, 2, 4):
    buf, err = khung(ass_da, T0 + DT * k + DT * 0.5)
    if buf is None:
        kiem(False, f"render khung từ #{k}", err)
        continue
    mau = PAL[k % len(PAL)]
    n, c = dem(buf, mau)
    nguong = max(700, 380 * len(TU[k]))
    kiem(n >= nguong, f"từ #{k} '{TU[k]}': mảng màu {mau} = {n} px "
                      f"(cần >= {nguong})")
    n2, _ = dem(buf, PAL[(k + 2) % len(PAL)])
    kiem(n2 < n * 0.35, f"từ #{k}: không lẫn màu từ khác ({n2} px)")
    tam.append(c)
if len(tam) >= 2:
    di = [abs(tam[i + 1][0] - tam[i][0]) + abs(tam[i + 1][1] - tam[i][1])
          for i in range(len(tam) - 1)]
    kiem(all(d > 25 for d in di), f"ô DI CHUYỂN theo từ ({[round(d) for d in di]} px)")
# cắt đáy khung: cỡ chữ tới 8% + ny tới 0,88 (thanh trong Chỉnh mẫu cho phép)
# So Ô SÁNG với KIỂU CŨ ở cùng cỡ/vị trí: kiểu mới KHÔNG được xuống thấp hơn
# kiểu cũ. (Ca 6,5% + ny 0,88 thì CẢ HAI đều bị cắt đáy — lỗi CŨ có sẵn của app
# khi kéo chữ quá thấp, đo 05/08/2026: cả 2 kiểu đều hết ở hàng 959/960. Đã báo
# anh Hùng: dùng ny <= 0,80 là an toàn. Cổng này canh PARITY, không canh lỗi cũ.)
CAU_DAI = ["những", "chuyện", "quan", "trọng", "nhất", "không", "ai", "kể"]
for tls, ny in ((0.040, 0.78), (0.052, 0.78), (0.065, 0.78), (0.065, 0.88)):
    yy = {}
    for pre in (KIEU[0], "Cả câu, từ đang nói vàng"):
        ws_d, dur_d = words(8, 0.36, CAU_DAI)
        pp = os.path.join(T, f"tran_{int(tls*1000)}_{int(ny*100)}_"
                             f"{'hl' if pre == KIEU[0] else 'cu'}.ass")
        C.build_ass(ws_d, [(0.0, dur_d)], pp, out_w=W, out_h=H,
                    font="Montserrat", size=int(H * tls), ny=ny, preset=pre)
        buf, err = khung(pp, T0 + DT * 4.5)
        yy[pre] = y_cuoi(buf) if buf else -2
    hl, cu = yy[KIEU[0]], yy["Cả câu, từ đang nói vàng"]
    kiem(hl >= 0 and hl <= max(cu, SH - 4),
         f"cỡ {tls*100:.1f}% ny {ny}: Ô SÁNG hết ở hàng {hl} / kiểu cũ {cu} "
         f"(khung {SH}) — không tệ hơn kiểu cũ")

print("\n══ 17. ĐI QUA HÀM XUẤT CLIP THẬT của app ══")
try:
    from app.core.ffmpeg_utils import export_canvas_clip  # noqa: E402
    src = os.path.join(T, "nguon.mp4")
    subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i",
                    "color=c=0x505050:s=1280x720:d=6,fps=30", "-f", "lavfi",
                    "-i", "sine=f=300:d=6", "-shortest", "-c:v", "libx264",
                    "-preset", "ultrafast", "-c:a", "aac", src],
                   capture_output=True)
    dst = os.path.join(T, "ra.mp4")
    _, _, _, dur4, ass4 = dung(KIEU[0], n=6)
    ok_x = export_canvas_clip(src, dst, [(0.0, min(5.5, dur4))],
                              (0.5, 0.42, 1.0), bg="blur", out_w=W, out_h=H,
                              ass_path=ass4)
    kiem(bool(ok_x) and os.path.exists(dst) and os.path.getsize(dst) > 20_000,
         f"xuất clip thật: {os.path.getsize(dst)/1024:.0f} KB"
         if os.path.exists(dst) else "xuất clip thật", str(ok_x))
    ra = os.path.join(T, "g.rgb")
    r = subprocess.run([FF, "-y", "-v", "error", "-ss",
                        f"{T0 + DT * 2 + DT * 0.5:.2f}", "-i", dst, "-vf",
                        f"scale={SW}:{SH}", "-frames:v", "1", "-f", "rawvideo",
                        "-pix_fmt", "rgb24", ra], capture_output=True,
                       text=True, errors="replace")
    n_x, _c = dem(open(ra, "rb").read(), PAL[2]) if r.returncode == 0 else (0, 0)
    kiem(n_x >= 1500, f"clip XUẤT RA có ô đúng màu {PAL[2]} ({n_x} px)")
except Exception as e:  # noqa: BLE001
    kiem(False, "xuất clip thật với kiểu ô nền", repr(e))

print()
if FAIL:
    print(f"KẾT QUẢ: {len(FAIL)} FAIL -> {FAIL}")
    sys.stdout.flush()
    os._exit(1)
print("KẾT QUẢ: TẤT CẢ ĐẠT — ô nền 2 lớp chạy đúng theo từ, đa màu, "
      "không mất chữ, không tràn khung, preset cũ y nguyên")
sys.stdout.flush()
os._exit(0)
