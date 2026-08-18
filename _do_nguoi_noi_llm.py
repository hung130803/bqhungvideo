"""ĐO TÍN HIỆU (a): LLM đọc BẢN CHÉP LỜI để phân biệt NGƯỜI KỂ / NGƯỜI TRONG KHUNG.

Chấm cả 577 đoạn của 4 video, gửi theo MẺ có kèm câu TRƯỚC/SAU làm ngữ cảnh
(văn phong kể chuyện chỉ đọc ra được trong mạch, một câu trơ thì mù).

Thang phải nói rõ CHIỀU (bài học cổng 49). Ở đây trả NHÃN chứ không trả điểm
thang 0-10 để khỏi lặp lại lỗi "model chấm ngược chiều".

Chạy: .venv\\Scripts\\python -u _do_nguoi_noi_llm.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

GOC = Path(__file__).resolve().parent
sys.path.insert(0, str(GOC))
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

SAN = GOC / "_kq_nn"
TEN = ("v1_dutu", "v2_nieu", "v3_8daodien", "v4_khuyendung")
ME = 25           # số câu mỗi lượt gọi (prompt ~1.2k token, còn chỗ trả lời)

HE_THONG = (
    "Bạn phân loại từng câu trong bản chép lời của một video 'giải thích phim' "
    "trên mạng xã hội. Chỉ trả JSON, không giải thích."
)

MAU = """Video này là kiểu "giải thích phim": một NGƯỜI KỂ (thuyết minh ngoài
hình) tóm tắt cốt truyện, xen giữa là các đoạn TRÍCH TỪ CHÍNH BỘ PHIM còn
nguyên tiếng gốc (diễn viên nói trong khung, tiếng hò, tiếng hát, tiếng động).

Với MỖI câu được đánh số dưới đây, quyết định câu đó do ai phát ra:
- "ke"  = NGƯỜI KỂ đang thuyết minh. Dấu hiệu: kể ở NGÔI THỨ BA, gọi nhân vật
  bằng tên hoặc "nam chính/cô gái/người cha", tả diễn biến, tả bối cảnh, giới
  thiệu phim, đưa số liệu doanh thu/điểm đánh giá.
- "goc" = TIẾNG GỐC CỦA PHIM, KHÔNG phải người kể. Dấu hiệu: lời đối thoại
  ngôi thứ nhất/thứ hai nói trực tiếp với nhau, câu cảm thán, tiếng hò/hát/
  đếm/lặp âm vô nghĩa, câu ở NGÔN NGỮ KHÁC hẳn phần còn lại của video.

QUAN TRỌNG: người kể VẪN có thể thuật lại lời nhân vật ("anh ta nói rằng...",
"cô ấy bảo đừng đi") — đó vẫn là "ke". Chỉ đánh "goc" khi câu đó KHÔNG THỂ là
lời thuyết minh.

Nếu không chắc, hãy chọn "ke" (đánh nhầm thành "goc" làm mất nội dung video).

Trả JSON đúng dạng: [{{"i": <số>, "ai": "ke"|"goc", "tin": 0..1}}]
`tin` = mức tự tin, 1 = rất chắc.

CÁC CÂU:
{cau}"""


def me_prompt(cau: list[dict], lo: list[int]) -> str:
    dong = []
    for i in lo:
        dong.append(f"{i}. [{cau[i]['start']:.1f}s] {cau[i]['text']}")
    return MAU.format(cau="\n".join(dong))


def main() -> None:
    from app.ai import llm

    ket = {}
    for ten in TEN:
        d = json.loads((SAN / f"chep_{ten}.json").read_text(encoding="utf-8"))
        cau = d["cau"]
        nhan: dict[int, dict] = {}
        t0 = time.time()
        luot = 0
        for k in range(0, len(cau), ME):
            lo = list(range(k, min(k + ME, len(cau))))
            p = me_prompt(cau, lo)
            try:
                data = llm.complete_json(p, HE_THONG)
                luot += 1
            except Exception as e:
                print(f"   LOI me {k}: {type(e).__name__}: {str(e)[:120]}")
                continue
            if isinstance(data, dict):
                data = data.get("ket") or data.get("data") or []
            for it in (data or []):
                if not isinstance(it, dict):
                    continue
                try:
                    i = int(it.get("i"))
                except (TypeError, ValueError):
                    continue
                ai = str(it.get("ai") or "").strip().lower()
                if i in lo and ai in ("ke", "goc"):
                    try:
                        tin = float(it.get("tin", 0.5))
                    except (TypeError, ValueError):
                        tin = 0.5
                    nhan[i] = {"ai": ai, "tin": round(tin, 3)}
        thieu = [i for i in range(len(cau)) if i not in nhan]
        goc = [i for i, v in nhan.items() if v["ai"] == "goc"]
        print(f"== {ten}: {len(cau)} cau, {luot} luot LLM, "
              f"{time.time() - t0:.1f}s | cham duoc {len(nhan)}, "
              f"thieu {len(thieu)} | doan 'goc': {len(goc)} -> {sorted(goc)}")
        for i in sorted(goc):
            print(f"     #{i:3d} [{cau[i]['start']:7.2f}] tin="
                  f"{nhan[i]['tin']:.2f}  {cau[i]['text'][:52]}")
        ket[ten] = {"nhan": {str(i): v for i, v in nhan.items()},
                    "thieu": thieu, "luot": luot}
    (SAN / "llm.json").write_text(json.dumps(ket, ensure_ascii=False),
                                  encoding="utf-8")
    print("GHI: _kq_nn/llm.json")


if __name__ == "__main__":
    main()
