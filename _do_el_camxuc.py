"""ĐO: đường THAY GIỌNG với `el:` có mang theo **eleven_v3 + THẺ CẢM XÚC**
không — bằng **GỌI THẬT + ĐẾM**, không đọc mã rồi suy.

VÌ SAO PHẢI ĐO CHỨ KHÔNG ĐỌC MÃ: bài học `lang="vi"` (đọc mã kết luận đã nối,
gọi thật ra chưa). Và bài học cổng 67 ngược lại: bịa một bản vá rồi ca ĐẠT vì
lý do NGƯỢC HẲN (không ai gọi tới nên đếm ra 0) — nên file này bắt buộc phải
có **CHỐT "BẢN VÁ ĂN ĐƯỢC"** + **ĐỐI CHỨNG DƯƠNG**.

CÁCH ĐO
-------
Thay `dubbing._eleven_tts_once` (cửa HTTP DUY NHẤT tới ElevenLabs) bằng một
hàm GIẢ: nó **sinh mp3 thật bằng ffmpeg** rồi **GHI LẠI** `(model, text,
voice_id)` mà lớp trên đưa xuống. Không một ký tự nào bị tiêu.

**KHÔNG ĐỐT HẠN MỨC THẬT.** `_eleven_tts_once` là chỗ duy nhất `requests.post`
tới endpoint text-to-speech (grep `_ELEVEN_API` -> `/text-to-speech/` chỉ ở
trong hàm này). Chặn ở đây là chặn hết. Quota (`/user/subscription`) KHÔNG
tính ký tự nên vẫn gọi thật một lần để lấy số cho báo cáo.

BA CHỐT (thiếu chốt nào cũng có thể ĐẠT/HỎNG vì lý do ngược hẳn)
----------------------------------------------------------------
CHỐT 1 — **BẢN VÁ ĂN ĐƯỢC**: sau khi chạy, số lần cửa giả bị gọi phải > 0.
  Bằng 0 = mã không đi qua đó, mọi kết luận "không thấy v3" là VÔ NGHĨA.
CHỐT 2 — **ĐỐI CHỨNG DƯƠNG**: đường RECAP bật cảm xúc phải ĐẾM RA `eleven_v3`
  VÀ text còn nguyên thẻ `[...]`. Không ra = bộ dò hỏng, không phải app hỏng.
CHỐT 3 — **ĐỐI CHỨNG ÂM**: đường RECAP TẮT cảm xúc phải ra v2 + text đã sạch
  thẻ. Ra v3 = bộ dò không phân biệt được gì, bảng vô nghĩa.

Chạy:  .venv\\Scripts\\python -u _do_el_camxuc.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

FF = str(REPO / "bin" / "ffmpeg.exe")
SAN = REPO / "bq_do_el_camxuc"
KQ = REPO / "_kq_el_camxuc.json"
NOWIN = 0x08000000

#: Giọng premade Adam — đúng giọng `_test_eleven_tg.py` dùng, có ở MỌI account.
ADAM = "el:pNInz6obpgDQGcFmaJgB"

#: Lời narrate CÓ THẺ CẢM XÚC — đúng dạng `recap._emotion_rule` dạy AI viết.
CAU_CO_THE = [
    "[excited]Không thể TIN nổi chuyện vừa xảy ra ở đây!",
    "[whispers]Nhưng ba phút sau, cả toà nhà đã biến mất.",
]

#: Sổ ghi mọi lần cửa HTTP bị gọi. Mỗi mục: {arm, model, text, vid}.
SO: list[dict] = []


def _mp3_gia(out_path: str, giay: float = 1.4) -> None:
    """Sinh mp3 THẬT bằng ffmpeg (đủ để lớp trên ffprobe/đo được).

    `-t` LÀ TUỲ CHỌN ĐẦU VÀO — đặt sau `-i` thì `anullsrc` ghi vô hạn
    (đã có lần đầy ổ C 420 GB). Nên nó đứng TRƯỚC `-i`.
    """
    cmd = [FF, "-y", "-hide_banner", "-loglevel", "error",
           "-f", "lavfi", "-t", f"{giay:.3f}", "-i",
           "sine=frequency=180:sample_rate=44100",
           "-c:a", "libmp3lame", "-b:a", "128k", out_path]
    subprocess.run(cmd, check=True, creationflags=NOWIN,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _cua_gia(arm: str):
    """Trả hàm thay cho `dubbing._eleven_tts_once` — ĐÚNG chữ ký của nó."""
    def _gia(text: str, voice_id: str, model: str, key: str,
             out_path: str, want_timestamps: bool = True) -> list:
        SO.append({"arm": arm, "model": model, "text": text,
                   "vid": voice_id, "ts": bool(want_timestamps)})
        _mp3_gia(out_path)
        if not want_timestamps:
            return []
        # Mốc từng từ giả, tăng dần — đủ hợp lệ để lớp trên không nghẹn.
        tu = [t for t in str(text).split() if t]
        b = 1.4 / max(1, len(tu))
        return [[round(i * b, 3), round((i + 1) * b, 3), w]
                for i, w in enumerate(tu)]
    return _gia


def _co_the(s: str) -> bool:
    """Chuỗi này còn thẻ cảm xúc `[...]` không."""
    import re
    return bool(re.search(r"\[[a-zA-Z ]{2,30}\]", str(s or "")))


def _don_san() -> None:
    """Dọn hộp cát qua CỬA CHUNG — `xoa_an_toan` chặn `Path("")`/gốc ổ."""
    try:
        from app.core import xoa_an_toan
        xoa_an_toan.don_thu_muc(SAN, trong=REPO)
    except Exception as e:                                # noqa: BLE001
        print(f"  (dọn hộp cát lỗi: {e})")


def main() -> int:
    from app.core import dubbing

    SAN.mkdir(parents=True, exist_ok=True)
    kq: dict = {"arms": {}, "chot": {}}

    # ---- Số HẠN MỨC THẬT (endpoint quota KHÔNG tính ký tự) ----
    print("=" * 72)
    print("HẠN MỨC ElevenLabs THẬT (endpoint /user/subscription, 0 ký tự)")
    print("=" * 72)
    keys = dubbing._eleven_keys()
    print(f"  số key trong .env: {len(keys)}")
    tong_con = tong_han = 0
    for k in keys:
        try:
            q = dubbing.eleven_quota(k, use_cache=False)
        except Exception as e:                            # noqa: BLE001
            print(f"  key …{k[-6:]}: LỖI {type(e).__name__}")
            continue
        if not q:
            print(f"  key …{k[-6:]}: không đọc được")
            continue
        tong_con += int(q.get("remain") or 0)
        tong_han += int(q.get("limit") or 0)
        print(f"  key …{k[-6:]}: còn {q.get('remain')}/{q.get('limit')} "
              f"({q.get('tier')})")
    print(f"  TỔNG: còn {tong_con}/{tong_han} ký tự")
    kq["han_muc"] = {"so_key": len(keys), "con": tong_con, "han": tong_han}

    # Pre-flight của `_synth_all_eleven` gọi `eleven_credit_remain`; ép nó
    # trả số LỚN để lượt đo không bị đá sang edge vì lý do hạn mức (ta đang
    # hỏi "gửi model nào", không hỏi "còn tiền không").
    dubbing.eleven_credit_remain = lambda *a, **k: 10 ** 9   # type: ignore
    # Cache TTS trỏ vào hộp cát: cache trúng là KHÔNG gọi cửa HTTP -> đếm ra
    # 0 rồi kết luận sai (đúng bẫy CHỐT 1).
    dubbing._TTS_CACHE_DIR = SAN / "_cache_tts"             # type: ignore
    dubbing._TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    goc_once = dubbing._eleven_tts_once

    # =================================================================
    # ARM 1 — ĐỐI CHỨNG DƯƠNG: đường RECAP, BẬT cảm xúc
    # =================================================================
    print()
    print("=" * 72)
    print("ARM 1 (ĐỐI CHỨNG DƯƠNG) — build_recap_track(emotion=True)")
    print("=" * 72)
    SO.clear()
    dubbing._eleven_tts_once = _cua_gia("recap_bat")        # type: ignore
    try:
        parts = [{"start": 1.0, "end": 7.0, "mode": "narrate",
                  "text": CAU_CO_THE[0]},
                 {"start": 8.0, "end": 14.0, "mode": "narrate",
                  "text": CAU_CO_THE[1]}]
        dubbing.build_recap_track(
            parts, [(0.0, 30.0)], ADAM, "vi",
            SAN / "recap_bat.wav", emotion=True)
    except Exception as e:                                  # noqa: BLE001
        print(f"  build_recap_track ném: {type(e).__name__}: {e}")
    finally:
        dubbing._eleven_tts_once = goc_once                 # type: ignore
    a1 = list(SO)
    kq["arms"]["recap_bat"] = a1
    print(f"  số lần gọi cửa ElevenLabs: {len(a1)}")
    for r in a1:
        print(f"    model={r['model']!r}  thẻ={_co_the(r['text'])}  "
              f"text={r['text'][:56]!r}")

    # =================================================================
    # ARM 2 — ĐỐI CHỨNG ÂM: đường RECAP, TẮT cảm xúc
    # =================================================================
    print()
    print("=" * 72)
    print("ARM 2 (ĐỐI CHỨNG ÂM) — build_recap_track(emotion=False)")
    print("=" * 72)
    SO.clear()
    dubbing._eleven_tts_once = _cua_gia("recap_tat")        # type: ignore
    try:
        parts = [{"start": 1.0, "end": 7.0, "mode": "narrate",
                  "text": CAU_CO_THE[0]},
                 {"start": 8.0, "end": 14.0, "mode": "narrate",
                  "text": CAU_CO_THE[1]}]
        dubbing.build_recap_track(
            parts, [(0.0, 30.0)], ADAM, "vi",
            SAN / "recap_tat.wav", emotion=False)
    except Exception as e:                                  # noqa: BLE001
        print(f"  build_recap_track ném: {type(e).__name__}: {e}")
    finally:
        dubbing._eleven_tts_once = goc_once                 # type: ignore
    a2 = list(SO)
    kq["arms"]["recap_tat"] = a2
    print(f"  số lần gọi cửa ElevenLabs: {len(a2)}")
    for r in a2:
        print(f"    model={r['model']!r}  thẻ={_co_the(r['text'])}  "
              f"text={r['text'][:56]!r}")

    # =================================================================
    # ARM 3 — CÂU HỎI THẬT: đường THAY GIỌNG (`doc_ban_dich`)
    # =================================================================
    print()
    print("=" * 72)
    print("ARM 3 (CÂU HỎI) — thay_giong.doc_ban_dich(voice='el:...')")
    print("=" * 72)
    from app.core import thay_giong
    SO.clear()
    dubbing._eleven_tts_once = _cua_gia("thay_giong")       # type: ignore
    try:
        rg = thay_giong.doc_ban_dich(
            list(CAU_CO_THE), SAN / "tg", voice=ADAM, dich_sang="vi")
        print(f"  doc_ban_dich -> voice={rg.get('voice')!r} "
              f"ok={rg.get('ok')} so_hong={rg.get('so_hong')}")
    except Exception as e:                                  # noqa: BLE001
        print(f"  doc_ban_dich ném: {type(e).__name__}: {e}")
    finally:
        dubbing._eleven_tts_once = goc_once                 # type: ignore
    a3 = list(SO)
    kq["arms"]["thay_giong"] = a3
    print(f"  số lần gọi cửa ElevenLabs: {len(a3)}")
    for r in a3:
        print(f"    model={r['model']!r}  thẻ={_co_the(r['text'])}  "
              f"text={r['text'][:56]!r}")

    # =================================================================
    # BA CHỐT
    # =================================================================
    def _models(a: list) -> set:
        return {r["model"] for r in a}

    chot1 = len(a1) > 0 and len(a3) > 0
    chot2 = bool(a1) and _models(a1) == {"eleven_v3"} and \
        all(_co_the(r["text"]) for r in a1)
    chot3 = bool(a2) and "eleven_v3" not in _models(a2) and \
        not any(_co_the(r["text"]) for r in a2)
    kq["chot"] = {"an_duoc": chot1, "doi_chung_duong": chot2,
                  "doi_chung_am": chot3}

    print()
    print("=" * 72)
    print("BA CHỐT")
    print("=" * 72)
    print(f"  CHỐT 1 bản vá ĂN ĐƯỢC (arm1>0 và arm3>0): "
          f"{'ĐẠT' if chot1 else 'HỎNG'}  (arm1={len(a1)} arm3={len(a3)})")
    print(f"  CHỐT 2 đối chứng DƯƠNG (recap bật = v3 + còn thẻ): "
          f"{'ĐẠT' if chot2 else 'HỎNG'}  models={sorted(_models(a1))}")
    print(f"  CHỐT 3 đối chứng ÂM (recap tắt = KHÔNG v3 + sạch thẻ): "
          f"{'ĐẠT' if chot3 else 'HỎNG'}  models={sorted(_models(a2))}")

    print()
    print("=" * 72)
    print("KẾT LUẬN")
    print("=" * 72)
    if not (chot1 and chot2 and chot3):
        print("  BỘ DÒ KHÔNG TIN ĐƯỢC — có chốt HỎNG, KHÔNG kết luận gì.")
        kq["ket_luan"] = "bo_do_hong"
    else:
        m3 = sorted(_models(a3))
        the3 = any(_co_the(r["text"]) for r in a3)
        kq["ket_luan"] = {"model_thay_giong": m3, "con_the": the3}
        print(f"  Đường THAY GIỌNG gửi model: {m3}")
        print(f"  Đường THAY GIỌNG có gửi thẻ cảm xúc: {the3}")
        if "eleven_v3" in m3:
            print("  -> ĐÃ NỐI v3 trên đường thay giọng.")
        else:
            print("  -> **CHƯA NỐI**: đường thay giọng dùng "
                  f"{m3} chứ KHÔNG phải eleven_v3.")
            print("     Tức hộp Thay giọng KHÔNG có đường nào chỉ đạo cảm xúc.")

    KQ.write_text(json.dumps(kq, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    print(f"\n  kết quả -> {KQ}")
    return 0 if (chot1 and chot2 and chot3) else 1


if __name__ == "__main__":
    rc = 1
    try:
        rc = main()
    finally:
        _don_san()
    sys.exit(rc)
