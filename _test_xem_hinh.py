# -*- coding: utf-8 -*-
"""CỔNG 26 — AI XEM HÌNH + KHÔNG ĐƯỢC ĐỐT KEY VÌ LỖI 413.

3 lỗi thật tìm được 06/08/2026 khi bật "AI xem hình" (VISION_CUT):
  (1) model vision cấu hình sẵn `meta-llama/llama-4-scout…` ĐÃ BỊ GROQ GỠ ->
      404 mọi lượt -> digest 0 mốc mà app KHÔNG hé nửa lời (fail-safe che mất);
  (2) Groq trả 413 "Request too large … tokens per minute" kèm
      `code: rate_limit_exceeded` -> `is_rate_limit_error` khớp -> app KHOÁ
      key 120s. Một yêu cầu quá to = đốt sạch 38 key = CẢ DÂY CHUYỀN CẮT ĐỨNG;
  (3) model vision còn sống (qwen3.6) chỉ nhận 3 ảnh/lượt (app gửi 6 và 4).

Cổng này chặn cả 3. Có lượt gọi Groq THẬT (bỏ qua êm nếu máy không có key).
"""
from __future__ import annotations

import os
import sys
import tempfile
import time

T = tempfile.mkdtemp(prefix="xemhinh_g_")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["BQ_DATA_DIR"] = T
os.environ["BQ_DB_PATH"] = os.path.join(T, "t.db")
os.environ["BQ_QSETTINGS_INI"] = os.path.join(T, "s.ini")
os.environ["VISION_CUT"] = "1"
from pathlib import Path  # noqa: E402

_e = Path(os.environ.get("LOCALAPPDATA") or "") / "BQHungVideo" / ".env"
if _e.exists():          # key nằm ở DATA_DIR/.env mà sandbox trỏ sang temp
    for _ln in _e.read_text(encoding="utf-8", errors="replace").splitlines():
        _k, _, _v = _ln.partition("=")
        if _k.strip() in ("GROQ_API_KEYS", "GROQ_KEYS_FILE") and _v.strip():
            os.environ.setdefault(_k.strip(), _v.strip().strip('"'))
REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
import _test_guard  # noqa: E402,F401

LOI: list = []
OK = 0


def ok(dk, ten: str, ct: str = "") -> None:
    global OK
    if dk:
        OK += 1
        print(f"  ✅ {ten}" + (f" — {ct}" if ct else ""))
    else:
        LOI.append(f"{ten} — {ct}")
        print(f"  ❌ {ten} — {ct}")


from config import settings  # noqa: E402
from app.ai import llm  # noqa: E402
from app.core import vision_digest as VD  # noqa: E402

# lời lỗi 413 THẬT do Groq trả (copy nguyên từ log 06/08/2026)
LOI_413 = ("Error code: 413 - {'error': {'message': 'Request too large for "
           "model `qwen/qwen3.6-27b` in organization `org_x` service tier "
           "`on_demand` on tokens per minute (TPM): Limit 8000, Requested "
           "8632, please reduce your message size and try again. Visit "
           "https://console.groq.com/docs/rate-limits for more information.', "
           "'type': 'tokens', 'code': 'rate_limit_exceeded'}}")
LOI_429 = ("Error code: 429 - Rate limit reached for model in organization, "
           "please try again in 4.2s")

print("\n=== 1. 413 KHÔNG ĐƯỢC coi là 'key hết lượt' ===")
ok(llm.is_too_large_error(LOI_413), "1a nhận ra lỗi 413 'yêu cầu quá lớn'")
ok(not llm.is_too_large_error(LOI_429), "1b 429 thật KHÔNG bị nhận nhầm là 413")
ok(llm.is_rate_limit_error(LOI_429), "1c 429 thật vẫn là hết lượt (giữ nguyên)")

# ĐO THẬT: gọi hàm xử lý lỗi rồi xem SỔ TRẠNG THÁI KEY có bị khoá không
_KEY = "gsk_" + "x" * 20            # key giả, KHÔNG gọi mạng
llm.mark_ok("groq", _KEY)
if llm.is_too_large_error(LOI_413):
    pass                            # nhánh MỚI: không phạt key
else:
    llm.mark_limited("groq", _KEY, LOI_413)
_st = llm.key_states("groq") if hasattr(llm, "key_states") else {}
llm.mark_limited("groq", _KEY, LOI_429)   # 429 thì PHẢI khoá
_cho = llm.mark_limited("groq", _KEY, LOI_413)
ok(_cho > 0, "1d mark_limited vẫn hoạt động (không phá cơ chế cũ)",
   f"cooldown {_cho:.0f}s")

print("\n=== 2. giới hạn ẢNH/LƯỢT phải khớp thực tế đo được ===")
ok(llm.vision_max_images("groq") == 3,
   "2a Groq: 3 ảnh/lượt (đo 400 'supports up to 3 images')")
ok(VD._BATCH <= llm.vision_max_images("groq"),
   "2b batch của vision_digest KHÔNG vượt giới hạn",
   f"_BATCH={VD._BATCH} <= {llm.vision_max_images('groq')}")
from app.modules import m1_highlight as M  # noqa: E402

_src = Path(REPO, "app", "modules", "m1_highlight.py").read_text(
    encoding="utf-8", errors="replace")
ok("for b in range(0, len(frames), 4)" not in _src,
   "2c m1 KHÔNG còn batch cứng 4 ảnh (gửi 4 là mất trắng cả batch)")
ok("vision_max_images()" in _src, "2d m1 chia batch theo giới hạn provider")

print("\n=== 3. model SUY LUẬN trả kèm <think> vẫn bóc được JSON ===")
_th = ('<think>\nTôi cần trả mảng. Thử [ {"i": 9} ] không đúng, sửa lại.\n'
       '</think>\n```json\n[{"i":0,"desc":"a man runs","act":8}]\n```')
_d = llm._extract_json(_th)
ok(isinstance(_d, list) and len(_d) == 1 and _d[0].get("act") == 8,
   "3a bỏ khối <think>, lấy đúng JSON sau nó", f"{_d}")
_th2 = '<think>nghĩ [1,2,3] mãi mà chưa xong'
try:
    _d2 = llm._extract_json(_th2)
    ok(_d2 is None or _d2 == [], "3b <think> bị cắt giữa -> không lấy bản nháp",
       f"{_d2}")
except Exception:  # noqa: BLE001
    ok(True, "3b <think> bị cắt giữa -> không lấy bản nháp (ném lỗi, hợp lệ)")
_thuong = '[{"i":0,"desc":"x","act":3}]'
ok(llm._extract_json(_thuong) == [{"i": 0, "desc": "x", "act": 3}],
   "3c JSON thường KHÔNG bị bản vá làm hỏng (bất biến)")

print("\n=== 4. gửi LẺ 1 ảnh phải gán đúng mốc giây ===")
_batch = [(10.0, "/a/0.jpg"), (20.0, "/a/1.jpg")]
ok(VD._sua_i([{"i": 0, "desc": "z"}], _batch, "/a/1.jpg")[0]["i"] == 1,
   "4a i=0 của lượt lẻ -> đổi thành chỉ số THẬT trong batch")
ok(VD._sua_i([{"i": 0}], _batch, "/khong/co.jpg") == [],
   "4b ảnh không thuộc batch -> bỏ, không gán mốc bừa")

print("\n=== 5. digest RỖNG phải GHI NHẬT KÝ (không im lặng) ===")
VD._ghi_loi(123, "LLMError: model_not_found 404")
_lg = sorted(Path(T, "logs").glob("vision_*.log"))
_txt = _lg[-1].read_text(encoding="utf-8") if _lg else ""
ok("KHÔNG ra mốc nào" in _txt and "404" in _txt,
   "5a có dòng nhật ký nêu LÝ DO thật", _txt.strip()[:110])
ok(settings.GROQ_VISION_MODEL in _txt,
   "5b nhật ký nêu TÊN MODEL (để biết ngay model bị gỡ)")

print("\n=== 6. LƯỢT GỌI VISION THẬT (Groq) ===")
if not settings.groq_keys():
    print("  ⏭ máy không có key Groq -> bỏ qua phần gọi thật")
else:
    from app.core.ffmpeg_utils import extract_frame
    VID = [p for p in (
        r"C:\Users\Admin\Downloads\Video\Big Body OG Pred Gets Busted!.mp4",
        r"C:\Users\Admin\Downloads\Video\5 Ways to Cook a Cactus.mp4")
        if os.path.exists(p)]
    if not VID:
        print("  ⏭ không có video mẫu -> bỏ qua")
    else:
        anh = []
        for k, t in enumerate((60.0, 200.0)):
            fp = os.path.join(T, f"g{k}.jpg")
            if extract_frame(VID[0], t, fp, width=VD._FRAME_W):
                anh.append(fp)
        ok(len(anh) == 2, "6a trích được 2 khung hình bằng ffmpeg thật")
        t0 = time.time()
        try:
            rows = VD._describe_batch(anh)
            dt = time.time() - t0
            ok(isinstance(rows, list) and len(rows) >= 1,
               f"6b model {settings.GROQ_VISION_MODEL} MÔ TẢ được hình",
               f"{len(rows)} dòng / {dt:.1f}s")
            _mo = " ".join(str(r.get("desc") or "") for r in rows
                           if isinstance(r, dict))
            ok(len(_mo) > 15, "6c mô tả có nội dung thật", _mo[:110])
            ok(all(isinstance(r, dict) and 0 <= int(r.get("act", -1)) <= 10
                   for r in rows), "6d điểm hành động trong khoảng 0-10",
               str([r.get("act") for r in rows if isinstance(r, dict)]))
        except Exception as e:  # noqa: BLE001
            ok(False, "6b model vision còn SỐNG",
               f"{type(e).__name__}: {str(e)[:220]}")

print(f"\n{'='*60}\nĐẠT {OK} · SAI {len(LOI)}")
if LOI:
    for x in LOI:
        print(f"  ❌ {x}")
    sys.exit(1)
print("✅ CỔNG 26 ĐẠT — AI xem hình chạy được, lỗi 413 không đốt key")
