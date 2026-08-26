# -*- coding: utf-8 -*-
"""GIỌNG NHÂN BẢN ĐỌC TIẾNG ANH **DÀI HƠN KHUNG BAO NHIÊU** — nghi phạm thứ hai.

Anh Hùng nói *"đọc như thằng mới học ấy, **nói không lưu loát**"*. Hai chuyện
KHÁC NHAU trốn chung trong một câu, và bảng `_kq_vnb_en.txt` chỉ trả lời được
một:

  (1) **ĐỌC SAI CHỮ** — `_do_vnb_en.py` đã đo (WER · token · nhãn tiếng).
  (2) **ĐỌC KHÔNG LƯU LOÁT** — máy đọc ĐÚNG chữ nhưng tiếng ra **DÀI HƠN
      KHUNG THỜI GIAN** của câu gốc, nên `thay_giong.khop_thoi_gian` ép
      `rubberband`/`atempo` cho lọt. Ép mạnh là tiếng méo, nhịp gấp gáp —
      nghe **đúng như "người mới học"** dù không sai một chữ nào.

Bộ này đã có tiền lệ đo được: Chatterbox đọc tiếng Trung ra **1,85x** trần
(câu tệ nhất **3,56x**) trong khi **WER chỉ 1,5%** — tức *"đọc ĐÚNG CHỮ, SAI
NHỊP"*. Nên hỏi câu (1) rồi kết luận là bỏ sót đúng nửa câu hỏi của anh Hùng.

═══════════════════════════════════════════════════════════════════════════
KHÔNG ĐỌC LẠI GÌ CẢ — ĐO TRÊN CHÍNH FILE `_do_vnb_en.py` VỪA SINH
═══════════════════════════════════════════════════════════════════════════
Đọc lại một lượt nữa là (a) tốn 5 phút GPU, (b) **đo một arm KHÁC** vì VieNeu
không tiền định. File đã nằm ở `_do_vn_en/<arm>_v<vòng>/c0NN.mp3`; thước là
`thay_giong.cat_le_im_moc` + `giong_chatter._do_lang` — ĐÚNG hai hàm đường
xuất thật dùng, không dựng thước riêng.

TRẦN = `edge_en_v1` (en-US-Aria), tức **cùng bộ file** đã làm trần cho bảng
sai-chữ. Một phép đo, hai câu hỏi, một cái trần.

Chạy:  .venv\\Scripts\\python -u _do_vnb_nhip.py
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

HOP = REPO / "_do_vn_en"
TAM = REPO / "_do_vnb_en" / "_nhip"
KQ = REPO / "_kq_vnb_nhip.json"

#: Trần `atempo`/`rubberband` của đường xuất thật. Đọc THẲNG từ `thay_giong`
#: chứ không gõ lại 1.50 — gõ lại là đẻ ra bản sao thứ hai của một con số.
from app.core.thay_giong import TEMPO_TOI_DA                    # noqa: E402

ARM = [("VNB_en", 1), ("VNB_en", 2), ("CB_en", 1), ("CB_en", 2),
       ("edge_en", 1), ("AD_en", 1)]
TRAN = ("edge_en", 1)

NHAN = {
    "VNB_en": "vnb: NHÂN BẢN qua VieNeu",
    "CB_en":  "cb: NHÂN BẢN qua Chatterbox",
    "edge_en": "edge Aria (TRẦN)",
    "AD_en":  "vn:Adam DỰNG SẴN",
}


def do_arm(ten: str, vong: int) -> list[float]:
    """Độ dài TỪNG CÂU sau khi cắt lề im hai đầu, giây. [] nếu thiếu file.

    Cắt lề trước khi đo là bắt buộc: edge-tts chèn tới **860 ms** im ở đuôi
    (đo được ở bảng Adam), mà `cat_le_loat` của đường xuất thật CẮT nó đi
    trước khi ai đo độ dài câu. Đo thô là so một cái có lề với một cái không.
    """
    from app.core import giong_chatter as GC
    from app.core import thay_giong as TG
    thu = HOP / f"{ten}_v{vong}"
    if not thu.is_dir():
        return []
    TAM.mkdir(parents=True, exist_ok=True)
    ra: list[float] = []
    for i in range(34):
        p = thu / f"c{i:03d}.mp3"
        if not p.exists():
            ra.append(0.0)
            continue
        sach = TAM / f"{ten}_v{vong}_{i:03d}.wav"
        try:
            TG.cat_le_im_moc(str(p), str(sach))
            ra.append(float(GC._do_lang(sach)[0]))
        except Exception:                                      # noqa: BLE001
            ra.append(0.0)
    return ra


def main() -> int:
    print("=" * 78)
    print("NHỊP ĐỌC — GIỌNG NHÂN BẢN ĐỌC TIẾNG ANH DÀI HƠN TRẦN BAO NHIÊU")
    print("=" * 78)
    print(f"trần `atempo` của đường xuất thật: {TEMPO_TOI_DA}")
    do: dict[str, list[float]] = {}
    for ten, v in ARM:
        d = do_arm(ten, v)
        if d:
            do[f"{ten}_v{v}"] = d
            print(f"  đo xong {ten}_v{v}: {len(d)} câu")
    key_tran = f"{TRAN[0]}_v{TRAN[1]}"
    if key_tran not in do:
        print("KHÔNG có trần -> mọi tỉ lệ vô nghĩa, DỪNG")
        return 2
    tran = do[key_tran]

    print("\n" + "=" * 78)
    print("BẢNG — TỔNG GIÂY · TỈ LỆ SO TRẦN · CÂU TỆ NHẤT · SỐ CÂU CHẠM TRẦN "
          f"atempo {TEMPO_TOI_DA}")
    print("=" * 78)
    print(f"{'arm':<34}{'tổng s':>10}{'tỉ lệ':>9}{'câu tệ nhất':>14}"
          f"{'chạm trần':>12}{'trung vị':>10}")
    ket: dict = {}
    for k, d in do.items():
        cap = [(a, b) for a, b in zip(d, tran) if a > 0 and b > 0]
        if not cap:
            continue
        tong_a = sum(a for a, _b in cap)
        tong_b = sum(b for _a, b in cap)
        ti = [a / b for a, b in cap]
        cham = sum(1 for x in ti if x > TEMPO_TOI_DA)
        ket[k] = {"tong": tong_a, "tran": tong_b, "ti_le": tong_a / tong_b,
                  "te_nhat": max(ti), "cham_tran": cham, "n": len(cap),
                  "trung_vi": st.median(ti)}
        ten = k.rsplit("_v", 1)[0]
        print(f"{NHAN.get(ten, ten) + ' v' + k[-1]:<34}{tong_a:>10.1f}"
              f"{tong_a / tong_b:>8.2f}x{max(ti):>13.2f}x"
              f"{f'{cham}/{len(cap)}':>12}{st.median(ti):>9.2f}x")

    print("\n" + "=" * 78)
    print("ĐỌC BẢNG NÀY THẾ NÀO")
    print("=" * 78)
    print("  · tỉ lệ 1,00x = đọc đúng bằng trần -> `khop_thoi_gian` không phải")
    print("    ép gì, tiếng ra KHÔNG méo.")
    print(f"  · câu có tỉ lệ > {TEMPO_TOI_DA} là câu đường xuất **ép không nổi**")
    print("    -> phải cắt bớt chữ hoặc để tràn khung. Đó là chỗ nghe ra")
    print("    'gấp gáp / không lưu loát' rõ nhất.")
    KQ.write_text(json.dumps(ket, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    print(f"\nSố thô: {KQ}")

    # DỌN file tạm của chính mình — kể cả khi lỗi (luật repo).
    try:
        from app.core import xoa_an_toan
        xoa_an_toan.don_thu_muc(str(TAM))
    except Exception:                                          # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
