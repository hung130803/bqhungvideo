"""ĐO TÍN HIỆU (a) LƯỢT 2 — có MỒI ĐỐI CHỨNG trong từng mẻ + BỎ PHIẾU 3 lượt.

LƯỢT 1 ĐÃ BẮT ĐƯỢC MỘT LỖI NẶNG, PHẢI GHI LẠI: nhãn "goc" dính **ĐÚNG BIÊN
MẺ** — v1 và v2 đều là các câu 100-124 (mẻ thứ 5), v4 là 50-64 (mẻ cuối).
Cùng một mẻ thì CẢ 25 câu ra "goc" với `tin` 0,95-1,00, trong khi đó là những
câu kể chuyện rõ ràng nhất. Tức model **ĐẢO NHÃN CẢ MẺ** và vẫn rất tự tin.
Đo được 67/577 = 11,6% "goc", trong đó 66 là ĐẢO NHÃN.

Bài học: `tin` do model tự khai KHÔNG dùng được để bắt lỗi này (nó tự tin nhất
đúng lúc sai nhất). Phải có MỒI mà mình biết trước đáp án.

CHỮA (3 lớp):
  1. MỖI MẺ chèn 4 câu MỒI mình biết đáp án (2 kể · 2 gốc), đánh số LẪN vào
     dãy 1..N nên model không phân biệt được mồi với câu thật.
  2. Mẻ nào chấm sai mồi -> BỎ, gọi lại (tối đa 3 lần). Vẫn sai -> mẻ đó ghi
     "khong_tin", KHÔNG được quyền giữ gốc.
  3. Mỗi mẻ chấm 3 LƯỢT, lấy ĐA SỐ.

Chạy: .venv\\Scripts\\python -u _do_nguoi_noi_llm2.py
"""
from __future__ import annotations

import json
import os
import random
import sys
import time
from pathlib import Path

GOC = Path(__file__).resolve().parent
sys.path.insert(0, str(GOC))
sys.stdout.reconfigure(encoding="utf-8")

SAN = GOC / "_kq_nn"
TEN = ("v1_dutu", "v2_nieu", "v3_8daodien", "v4_khuyendung")
ME = 20
SO_LUOT = 3

#: MỒI — đáp án do tôi đặt, model không được biết. Cùng thứ tiếng với corpus.
MOI = [
    ("这部电影上映首周就拿下了三亿票房", "ke"),
    ("男主回到家后发现桌上的东西被人动过", "ke"),
    ("别过来！你到底想干什么", "goc"),
    ("啊啊啊 救命啊 快跑", "goc"),
]

HE_THONG = ("Bạn phân loại từng câu trong bản chép lời video 'giải thích phim'. "
            "Chỉ trả JSON.")

MAU = """Video kiểu "giải thích phim": một NGƯỜI KỂ thuyết minh ngoài hình tóm
tắt cốt truyện, xen giữa là đoạn TRÍCH TỪ CHÍNH BỘ PHIM còn nguyên tiếng gốc.

Phân loại MỖI câu:
- "ke"  = lời NGƯỜI KỂ. Kể ngôi thứ BA, gọi nhân vật bằng tên hoặc "nam
  chính / cô gái / người cha", tả diễn biến, tả bối cảnh, nêu doanh thu/điểm.
- "goc" = TIẾNG GỐC CỦA PHIM. Đối thoại ngôi thứ NHẤT/THỨ HAI nói trực tiếp
  với nhau, câu cảm thán, tiếng hò/hát/lặp âm vô nghĩa, hoặc câu ở NGÔN NGỮ
  KHÁC hẳn phần còn lại.

Người kể VẪN được thuật lại lời nhân vật ("anh ta nói rằng...", "cô bảo đừng
đi") — đó là "ke". Chỉ đánh "goc" khi câu KHÔNG THỂ là lời thuyết minh.

Phần lớn câu trong video này là "ke". Câu "goc" là NGOẠI LỆ, thường rất ít.
Mỗi câu đánh "goc" PHẢI kèm `vi_sao` dưới 12 chữ nói rõ dấu hiệu.

Trả JSON: [{{"i": <số>, "ai": "ke"|"goc", "vi_sao": "<chỉ khi goc>"}}]
Phải trả ĐỦ {n} phần tử, đúng các số đã cho.

CÁC CÂU:
{cau}"""


def mot_luot(llm, muc: list[tuple[int, str]]) -> dict[int, dict]:
    dong = "\n".join(f"{j}. {t}" for j, t in muc)
    p = MAU.format(n=len(muc), cau=dong)
    data = llm.complete_json(p, HE_THONG)
    if isinstance(data, dict):
        data = data.get("ket") or data.get("data") or data.get("cau") or []
    ra = {}
    for it in (data or []):
        if not isinstance(it, dict):
            continue
        try:
            j = int(it.get("i"))
        except (TypeError, ValueError):
            continue
        ai = str(it.get("ai") or "").strip().lower()
        if ai in ("ke", "goc"):
            ra[j] = {"ai": ai, "vi_sao": str(it.get("vi_sao") or "")[:60]}
    return ra


def cham_me(llm, cau: list[dict], lo: list[int], rnd: random.Random):
    """Trả (nhan theo chỉ số THẬT, so_luot_dung_moi, so_luot_goi)."""
    phieu: dict[int, list[str]] = {i: [] for i in lo}
    dung, goi = 0, 0
    for _ in range(SO_LUOT):
        muc = [(0, cau[i]["text"]) for i in lo]
        muc = [(i, cau[i]["text"]) for i in lo]
        kem = list(MOI)
        rnd.shuffle(kem)
        tron = [(("that", i), t) for i, t in muc] + \
               [(("moi", k), t) for k, (t, _) in enumerate(kem)]
        rnd.shuffle(tron)
        so = {}
        muc_gui = []
        for j, (khoa, t) in enumerate(tron, start=1):
            so[j] = khoa
            muc_gui.append((j, t))
        for _lan in range(3):
            goi += 1
            try:
                ra = mot_luot(llm, muc_gui)
            except Exception as e:
                print(f"      LOI: {type(e).__name__} {str(e)[:90]}")
                continue
            sai = [j for j, khoa in so.items()
                   if khoa[0] == "moi" and j in ra
                   and ra[j]["ai"] != kem[khoa[1]][1]]
            thieu_moi = [j for j, khoa in so.items()
                         if khoa[0] == "moi" and j not in ra]
            if sai or thieu_moi:
                print(f"      MOI SAI {len(sai)} / thieu {len(thieu_moi)} "
                      f"-> bo me, goi lai")
                continue
            dung += 1
            for j, khoa in so.items():
                if khoa[0] == "that" and j in ra:
                    phieu[khoa[1]].append(ra[j]["ai"])
            break
    nhan = {}
    for i, ps in phieu.items():
        if not ps:
            nhan[i] = {"ai": "khong_tin", "goc_phieu": 0, "so_phieu": 0}
            continue
        ng = sum(1 for x in ps if x == "goc")
        nhan[i] = {"ai": "goc" if ng * 2 > len(ps) else "ke",
                   "goc_phieu": ng, "so_phieu": len(ps)}
    return nhan, dung, goi


def main() -> None:
    from app.ai import llm
    rnd = random.Random(20260818)
    ket = {}
    for ten in TEN:
        d = json.loads((SAN / f"chep_{ten}.json").read_text(encoding="utf-8"))
        cau = d["cau"]
        nhan: dict[int, dict] = {}
        t0 = time.time()
        tong_dung = tong_goi = 0
        for k in range(0, len(cau), ME):
            lo = list(range(k, min(k + ME, len(cau))))
            n, dung, goi = cham_me(llm, cau, lo, rnd)
            nhan.update(n)
            tong_dung += dung
            tong_goi += goi
        goc = sorted(i for i, v in nhan.items() if v["ai"] == "goc")
        kt = sorted(i for i, v in nhan.items() if v["ai"] == "khong_tin")
        print(f"== {ten}: {len(cau)} cau | {tong_goi} lan goi, "
              f"{tong_dung} luot QUA MOI | {time.time() - t0:.0f}s")
        print(f"   'goc': {len(goc)} -> {goc}")
        print(f"   'khong_tin': {len(kt)}")
        for i in goc:
            v = nhan[i]
            print(f"     #{i:3d} [{cau[i]['start']:7.2f}] "
                  f"{v['goc_phieu']}/{v['so_phieu']} phieu  "
                  f"{cau[i]['text'][:46]}")
        ket[ten] = {str(i): v for i, v in nhan.items()}
    (SAN / "llm2.json").write_text(json.dumps(ket, ensure_ascii=False),
                                   encoding="utf-8")
    print("GHI: _kq_nn/llm2.json")


if __name__ == "__main__":
    main()
