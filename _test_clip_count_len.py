# -*- coding: utf-8 -*-
# LỖI anh Hùng 30/07: đặt 60-80s / 3 part mà ra 5-6 part + clip dưới 60s.
# Hai gốc trong m1_highlight, đường AI lẫn heuristic:
#   A. SỐ PART: không có chốt cứng = count trước vòng lưu -> fail-safe của
#      _refine_clip_selection (JSON hỏng giữ nguyên list) làm lọt dư clip.
#   B. ĐỘ DÀI: _trim_junk_edges (cắt mép CTA) chạy SAU _enforce_len ->
#      enforce nới lên 60s xong trim cắt tụt xuống <60. Nay đảo thứ tự:
#      trim TRƯỚC, enforce là NGƯỜI NÓI CUỐI -> clip luôn >= min_len.
import os
import sys
from pathlib import Path
import tempfile

# IN ĐƯỢC TIẾNG VIỆT KỂ CẢ KHI stdout BỊ CHUYỂN HƯỚNG RA FILE — xem ghi chú
# cùng nội dung ở `_test_lane_starve.py`. Thiếu nó thì cổng HỎNG OAN (mã thoát
# 1) ngay dòng `print` đầu tiên khi chạy hồi quy hàng loạt.
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        pass

# PHẢI CÓ TIỀN TỐ: `mkdtemp()` trần đẻ ra `tmpXXXXXXXX` — trùng khuôn tên mà
# MỌI chương trình khác trên máy cũng dùng, nên `_test_guard.don_rac_cu`
# KHÔNG thể dọn hộ (quét `tmp*` là dám xoá file của app khác). Không tiền tố
# = rác nằm lại VĨNH VIỄN, đúng bệnh đã làm ổ C đầy 100% hôm 15/08/2026.
os.environ["BQ_DB_PATH"] = os.path.join(
    tempfile.mkdtemp(prefix="clipcount_"), "t.db")
# CHẠY ĐÚNG BẢN MÃ CHỨA FILE TEST NÀY (worktree hay repo chính đều được).
# Trước đây ghi CỨNG đường repo chính, nên chạy cổng từ một git worktree là
# đang kiểm BẢN MÃ KHÁC — nhánh đang sửa không hề được kiểm mà cổng vẫn
# xanh (đúng loại PASS OAN đã cắn repo này nhiều lần).
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.modules import m1_highlight as M1  # noqa: E402

FAIL = []


def kiem(ok, nhan, ct=""):
    print(("  ✓ " if ok else "  ✗ ") + nhan + ("" if ok else f"  << {ct}"))
    if not ok:
        FAIL.append(nhan)


def tong(segs):
    return sum(e - s for s, e in segs)


# ── B. THỨ TỰ trim→enforce: clip có câu CTA ở cuối vẫn ĐẠT min_len ──
# Dựng transcript: 0-62s nội dung, 62-66s là "like and subscribe" (CTA).
# Clip ứng viên đúng 62s (chạm sàn 60). Trim bỏ 4s CTA -> 58s -> DƯỚI min.
print("== B. đặt min 60s, clip dính CTA cuối -> vẫn >= 60s ==")
tsegs = ([{"start": i * 2.0, "end": i * 2.0 + 2.0,
           "text": f"noi dung cau {i}"} for i in range(31)]     # 0..62s
         + [{"start": 62.0, "end": 66.0,
             "text": "like and subscribe to the channel"}])     # CTA 62-66
duration = 300.0
MIN, MAX = 60.0, 80.0
bnd = [s["end"] for s in tsegs]

clip = [[0.0, 66.0]]                     # gồm cả câu CTA cuối
# THỨ TỰ MỚI (đúng): trim trước, enforce sau
seg = M1._trim_junk_edges(clip, tsegs, MIN)
seg, note = M1._enforce_len(seg, MIN, MAX, duration, bnd)
kiem(tong(seg) >= MIN - 0.5,
     f"clip cuối cùng >= {MIN:.0f}s (đo {tong(seg):.1f}s)", f"note={note}")
kiem(tong(seg) <= MAX + 2.0,
     f"clip không vượt quá {MAX:.0f}s (đo {tong(seg):.1f}s)")

# đối chứng: thứ tự CŨ (enforce trước, trim sau) LÀM LỌT SÀN
seg_cu, _ = M1._enforce_len(clip, MIN, MAX, duration, bnd)
seg_cu = M1._trim_junk_edges(seg_cu, tsegs, MIN)
print(f"   (thứ tự CŨ ra {tong(seg_cu):.1f}s — {'lọt sàn' if tong(seg_cu) < MIN - 0.5 else 'ok'})")

# ── B2. clip quá dài -> ép về <= max ──
print("== B2. clip quá dài -> cắt về <= max ==")
seg = M1._trim_junk_edges([[0.0, 200.0]], tsegs, MIN)
seg, _ = M1._enforce_len(seg, MIN, MAX, duration, bnd)
kiem(tong(seg) <= MAX + 2.0, f"clip dài bị cắt về <= {MAX:.0f}s "
     f"(đo {tong(seg):.1f}s)")

# ── B3. min=60 max=80: đủ mọi ứng viên rơi vào [58,82] ──
print("== B3. quét nhiều ứng viên -> tất cả lọt [min-2, max+2] ==")
loi = 0
for st in (0.0, 30.0, 100.0, 150.0, 250.0):
    seg = M1._trim_junk_edges([[st, st + 40.0]], tsegs, MIN)  # 40s < min -> nới
    seg, _ = M1._enforce_len(seg, MIN, MAX, duration, bnd)
    d = tong(seg)
    if not (MIN - 2.0 <= d <= MAX + 2.0):
        loi += 1
        print(f"     ✗ start={st}: ra {d:.1f}s")
kiem(loi == 0, "mọi ứng viên đều lọt khoảng độ dài yêu cầu")

# ── A. CHỐT CỨNG số part = count (mô phỏng đúng logic trong generate) ──
print("== A. đặt count=3 mà có 6 clip -> cắt còn ĐÚNG 3 ==")


def cap_count(ai_clips, cfg):
    want = int(cfg.get("count", 0) or 0)
    if want > 0 and len(ai_clips) > want:
        ai_clips = ai_clips[:want]
    return ai_clips

sau = cap_count([{"i": i} for i in range(6)], {"count": 3})
kiem(len(sau) == 3, "6 clip -> chốt còn đúng 3", str(len(sau)))
kiem([c["i"] for c in sau] == [0, 1, 2], "giữ 3 clip ĐẦU (tốt nhất, đã xếp hạng)")

sau0 = cap_count([{"i": i} for i in range(6)], {"count": 0})
kiem(len(sau0) == 6, "count=0 (AI tự quyết) -> KHÔNG cắt", str(len(sau0)))

sau2 = cap_count([{"i": i} for i in range(2)], {"count": 5})
kiem(len(sau2) == 2, "có ít hơn count -> giữ nguyên (không bịa thêm)",
     str(len(sau2)))

# ── A2. kiểm code THẬT có 2 rào (chốt count + đảo thứ tự trim/enforce) ──
print("== A2. code thật có đủ 2 rào ==")
import io  # noqa: E402
src = io.open(str(Path(__file__).resolve().parent / 'app' / 'modules' / 'm1_highlight.py'),
              encoding="utf-8").read()
kiem("if _want > 0 and len(ai_clips) > _want:" in src,
     "đường AI: có chốt cứng số part = count")
# trim phải đứng TRƯỚC enforce trong vòng lưu (cả 2 đường)
ai_block = src[src.index("_want = int(cfg.get"):]
i_trim = ai_block.find("_trim_junk_edges(c[")
i_enf = ai_block.find("_enforce_len(segs,")
kiem(0 <= i_trim < i_enf, "đường AI: trim đứng TRƯỚC enforce", f"{i_trim},{i_enf}")

print()
if FAIL:
    print(f"KẾT QUẢ: {len(FAIL)} FAIL -> {FAIL}")
    sys.exit(1)
print("KẾT QUẢ: TẤT CẢ ĐẠT — đúng số part + đúng độ dài min/max")
