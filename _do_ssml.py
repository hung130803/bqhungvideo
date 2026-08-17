# -*- coding: utf-8 -*-
"""edge-tts CÓ CHO SSML QUA KHÔNG — trả lời bằng THÍ NGHIỆM, không bằng suy đoán.

Nếu qua được thì `<lang xml:lang="en-US">Netflix</lang>` là cách sạch nhất:
gặp chữ tiếng Anh thì bảo Azure đọc bằng giọng Anh, giữ nguyên một lượt gọi,
giữ nguyên mốc từng chữ.

3 PHÉP THỬ, mỗi phép một tầng:
  A. QUÉT MÃ NGUỒN `edge_tts` xem nó có escape chữ của mình không.
  B. Đẩy SSML qua **CỬA CHUNG của app** (`dubbing._synth_all`) rồi chép ngược
     — thẻ bị đọc thành tiếng thì bản chép sẽ có chữ "lang" / "xml".
  C. Đẩy SSML qua **API TRẦN của edge_tts** (`Communicate` trực tiếp), phòng
     khi app có lớp làm sạch riêng.

Chạy:  .venv\\Scripts\\python -u _do_ssml.py
"""
from __future__ import annotations

import asyncio
import inspect
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

HOP = REPO / "_do_ssml"
GIONG_VI = "vi-VN-HoaiMyNeural"
THU = [
    ("tron", "Bộ phim này đứng đầu bảng xếp hạng Netflix."),
    ("ssml_lang",
     'Bộ phim này đứng đầu bảng xếp hạng <lang xml:lang="en-US">Netflix</lang>.'),
    ("ssml_phoneme",
     'Chữ viết tắt <say-as interpret-as="characters">GDP</say-as> hôm nay.'),
]


async def _tho(text: str, ra: Path) -> None:
    """Gọi THẲNG edge_tts.Communicate — không qua lớp nào của app."""
    import edge_tts
    c = edge_tts.Communicate(text, GIONG_VI)
    with open(ra, "wb") as f:
        async for ch in c.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])


def main() -> int:
    HOP.mkdir(exist_ok=True)
    import edge_tts
    from edge_tts import communicate as _cm
    print(f"edge-tts {edge_tts.__version__}\n")

    # ---- A. QUÉT MÃ NGUỒN ----
    print("[A] edge_tts có ESCAPE chữ của mình không?")
    src = inspect.getsource(_cm)
    for dau in ("escape(", "remove_incompatible_characters",
                "ssml_headers_plus_data", "mkssml"):
        print(f"   {dau:<36} {'CÓ' if dau in src else 'không'}")
    try:
        print("\n   mkssml() dựng ra gì:")
        tcs = _cm.TTSConfig(voice=GIONG_VI, rate="+0%", volume="+0%",
                            pitch="+0Hz")
        print("   " + _cm.mkssml(tcs, "A <lang xml:lang=\"en-US\">B</lang> C")
              .replace("\n", " ")[:300])
    except Exception as e:                                  # noqa: BLE001
        print(f"   (không dựng được: {type(e).__name__}: {e})")

    # ---- B + C. ĐỌC THẬT rồi CHÉP NGƯỢC ----
    from _do_doc_sai import chep_nguoc
    from app.core import dubbing

    print("\n[B] qua CỬA CHUNG của app (dubbing._synth_all)")
    paths = [str(HOP / f"b_{t}.mp3") for t, _ in THU]
    ok = asyncio.run(dubbing._synth_all([s for _, s in THU], GIONG_VI, paths))
    for (ten, s), p, o in zip(THU, paths, ok):
        chep = chep_nguoc(Path(p)) if o else "[không đọc được]"
        print(f"   {ten:<14} ok={o} -> «{chep.strip()[:110]}»")

    print("\n[C] qua API TRẦN của edge_tts (Communicate)")
    for ten, s in THU:
        p = HOP / f"c_{ten}.mp3"
        try:
            asyncio.run(_tho(s, p))
            chep = chep_nguoc(p)
        except Exception as e:                              # noqa: BLE001
            chep = f"[NÉM {type(e).__name__}: {str(e)[:80]}]"
        print(f"   {ten:<14} -> «{str(chep).strip()[:110]}»")

    print("\nĐỌC BẢNG: bản chép có chữ 'lang'/'xml'/'say as' = thẻ bị ĐỌC "
          "THÀNH TIẾNG (SSML KHÔNG qua). Bản chép sạch mà giống hệt arm 'tron' "
          "= thẻ bị BỎ nhưng cũng không có tác dụng.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
