# -*- coding: utf-8 -*-
"""ĐO CHỐT 1 — CHATTERBOX **ĐỌC LOẠN NHỊP**, và cắt lặng GIỮA CÂU chữa được bao
nhiêu.

═══════════════════════════════════════════════════════════════════════════
PHÉP SO PHẢI **GHÉP CẶP**, KHÔNG ĐƯỢC CHẠY HAI LƯỢT
═══════════════════════════════════════════════════════════════════════════
Chatterbox có đóng seed (`torch.manual_seed`) nhưng vẫn phụ thuộc thứ tự gọi
và trạng thái model; chạy hai lượt rồi so là dựng lại đúng bẫy đã sập ba lần
trên máy này (*"đo A/B phải đan xen"*). Ở đây tránh hẳn: sinh **MỘT** bộ WAV
thô, rồi hai arm chỉ khác nhau ở phép XỬ LÝ trên chính bộ WAV đó.

    arm THÔ  = file Chatterbox vừa trả
    arm CẮT  = `giong_chatter.cat_lang_giua` trên CHÍNH file đó

Mọi nhiễu của model bị triệt tiêu **theo cấu tạo**.

═══════════════════════════════════════════════════════════════════════════
"TRẦN" LÀ GÌ — VÀ VÌ SAO KHÔNG ĐƯỢC LẤY ĐỘ DÀI CÂU GỐC
═══════════════════════════════════════════════════════════════════════════
Trần = **edge-tts đọc ĐÚNG NHỮNG CHỮ ẤY**, đã cắt lề im hai đầu. Đó là "một
máy đọc bình thường mất bao lâu cho từng ấy chữ". Lấy độ dài câu gốc trong
video làm trần thì đang đo *"bản dịch dài hơn bản gốc bao nhiêu"* — một
chuyện khác hẳn, và nó lẫn cả lỗi của bước dịch vào.

Lề im hai đầu bị cắt ở **CẢ HAI BÊN** trước khi so (edge-tts chèn ~200 ms đầu
và tới 860 ms đuôi; Chatterbox đo được TB 337 ms, cá biệt 2.680 ms). Không cắt
thì bảng số đang so hai kiểu chèn lề chứ không so nhịp đọc.

═══════════════════════════════════════════════════════════════════════════
RANH GIỚI CỨNG — MẪU THAM CHIẾU LÀ **GIỌNG MÁY**
═══════════════════════════════════════════════════════════════════════════
Mẫu để nhân bản trong lượt đo này sinh bằng **edge-tts** (giọng máy), KHÔNG
lấy giọng người thật nào. Cụ thể là **KHÔNG dùng `_mau_giong/adam_clone.wav`**
— nguồn của file đó là bản sao một giọng ElevenLabs thương mại.

Chạy:  .venv\\Scripts\\python.exe _do_chatter_nhip.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
GOC = Path(__file__).resolve().parent
sys.path.insert(0, str(GOC))

HOP = GOC / "_do_chatter_nhip"
KQ = GOC / "_kq_chatter_nhip.json"

#: Giọng máy dùng làm MẪU nhân bản (edge-tts). Giọng máy, không phải người.
GIONG_MAU = "en-US-AndrewMultilingualNeural"

#: BA BỘ CÂU, và ba bộ này **KHÔNG thay nhau được** — xem `_kq_chatter_nhip`.
#: Lượt đo đầu chỉ có bộ `en_ngan` và nó ra **0,99x**, tức KHÔNG tái hiện được
#: con số 1,81x. Kết luận đúng lúc đó không phải *"1,81x là bịa"* mà là *"tật
#: loạn nhịp phụ thuộc HÌNH DẠNG CÂU"*, nên phải đo thêm đúng hai hình dạng
#: mà đường thay tiếng thật sinh ra:
#:   · `en_dai`  — câu dịch THẬT dài, nhiều mệnh đề, có dấu phẩy: đó là thứ
#:     `_dich_loat` trả ra, không phải câu 60 ký tự một mệnh đề.
#:   · `ja`      — bộ này bán ở chỗ nó ĐA NGÔN NGỮ; đo mỗi tiếng Anh rồi kết
#:     luận cho cả 23 thứ tiếng là chứng nhận sai thứ.
BO: dict[str, dict] = {
    "en_ngan": {
        "tran": "en-US-AriaNeural", "lang": "en",
        "cau": [
            "The storm knocked out power to the entire village that night.",
            "She opened the letter and read it twice before saying anything.",
            "Nobody expected the small team to win the championship.",
            "He kept the receipt in his wallet for almost three years.",
            "The doctor looked at the scan and went completely quiet.",
            "They found the missing camera buried under the old floorboards.",
            "Everything changed the moment the second envelope arrived.",
            "The recipe had been copied from her grandmother's notebook.",
            "It took four hours to drive back through the flooded road.",
            "The company denied it, but the emails told a different story.",
            "She sold the house and moved to a town nobody had heard of.",
            "By the time the police arrived, the room had already been cleaned.",
        ],
    },
    "en_dai": {
        "tran": "en-US-AriaNeural", "lang": "en",
        "cau": [
            "When the power finally came back on, sometime after three in the "
            "morning, the first thing anyone noticed was that the front door "
            "of the old house was standing wide open.",
            "He said he had never met her before, but the photograph on the "
            "desk, the one taken outside the courthouse in the summer of "
            "nineteen ninety four, told a completely different story.",
            "The report ran to four hundred pages, and yet somehow, in all "
            "that paper, nobody had bothered to write down the one detail "
            "that would have explained everything.",
            "She counted the money twice, put it back into the envelope, "
            "sealed it, and then sat there for almost twenty minutes without "
            "moving or saying a single word to anyone.",
            "Okay.",
            "Wait.",
            "And that was it.",
            "Nobody knew why.",
        ],
    },
    "ja": {
        "tran": "ja-JP-NanamiNeural", "lang": "ja",
        "cau": [
            "その夜、村じゅうの電気が止まってしまいました。",
            "彼女は手紙を開いて、二度読み返してから、ようやく口を開きました。",
            "小さなチームが優勝するとは、誰も思っていませんでした。",
            "医者はレントゲンを見つめたまま、完全に黙り込んでしまった。",
            "警察が到着したときには、部屋はすでにきれいに片づけられていた。",
            "そして、何も起こらなかった。",
        ],
    },
}

MAU_CAU = ("This is a sample of my speaking voice, recorded for testing. "
           "I am reading a few sentences at a normal pace so the system has "
           "enough material to work with. The weather today is clear and "
           "cold, and the streets are unusually quiet this morning.")


def ffmpeg() -> str:
    from config import settings
    return str(getattr(settings, "FFMPEG_PATH", "") or "ffmpeg")


def edge(text: str, voice: str, ra: Path) -> bool:
    """edge-tts -> wav 24k mono. Trả True nếu ra file dùng được."""
    import asyncio
    import edge_tts
    mp3 = ra.with_suffix(".mp3")

    async def _go() -> None:
        c = edge_tts.Communicate(text, voice)
        await c.save(str(mp3))

    try:
        asyncio.run(_go())
    except Exception as e:                                     # noqa: BLE001
        print(f"  edge-tts hỏng: {type(e).__name__}: {e}")
        return False
    r = subprocess.run(
        [ffmpeg(), "-y", "-v", "error", "-i", str(mp3), "-ac", "1",
         "-ar", "24000", str(ra)], capture_output=True)
    return r.returncode == 0 and ra.exists() and ra.stat().st_size > 4000


def cat_le(src: Path, dst: Path) -> float:
    """Cắt lề im HAI ĐẦU rồi trả độ dài. Dùng lại đúng hàm của app."""
    from app.core import thay_giong as TG
    d, _cat_dau = TG.cat_le_im_moc(str(src), str(dst))
    return float(d)


def mot_bo(gc, ten_bo: str, cfg: dict, ref: Path, py: str) -> dict:
    """Đo MỘT bộ câu. Trả dict số đo (đã in bảng ra màn hình)."""
    cau = list(cfg["cau"])
    lang = cfg["lang"]
    thu = HOP / ten_bo
    thu.mkdir(parents=True, exist_ok=True)

    print(f"\n### BỘ «{ten_bo}» ({len(cau)} câu, tiếng {lang}) "
          f"— trần = {cfg['tran']}")
    tran: list[float] = []
    for i, t in enumerate(cau):
        p = thu / f"tran_{i:02d}.wav"
        tran.append(cat_le(p, thu / f"tran_sach_{i:02d}.wav")
                    if edge(t, cfg["tran"], p) else 0.0)
    print(f"  trần: {sum(tran):.2f}s")

    items = [{"i": i, "text": t, "raw": str(thu / f"cb_{i:02d}.wav")}
             for i, t in enumerate(cau)]
    t0 = time.time()
    ket = gc._chay(items, str(ref), lang, py, 3600, None)
    giay_chay = time.time() - t0
    try:
        from app.core import xoa_an_toan
        xoa_an_toan.don_thu_muc(ket.get("_sandbox"), trong=gc.thu_muc_chatter())
    except Exception:                                          # noqa: BLE001
        pass
    if not ket.get("ok"):
        print(f"  Chatterbox đọc hỏng: {ket.get('loi')}")
        return {"bo": ten_bo, "loi": str(ket.get("loi"))}
    print(f"  Chatterbox xong {giay_chay:.1f}s · dev={ket.get('dev')} "
          f"· nạp {ket.get('nap')}s · gen {ket.get('gen')}s "
          f"· VRAM {ket.get('vram')} GiB")

    dong: list[dict] = []
    for i, t in enumerate(cau):
        raw = Path(items[i]["raw"])
        if not raw.exists():
            continue
        d_tho = cat_le(raw, thu / f"tho_sach_{i:02d}.wav")
        _dai, lang_giua = gc.khoang_lang_giua(raw)
        cat = thu / f"cat_{i:02d}.wav"
        kq = gc.cat_lang_giua(raw, cat)
        d_cat = (cat_le(cat, thu / f"cat_sach_{i:02d}.wav")
                 if kq.get("ok") else d_tho)
        tr = tran[i] if i < len(tran) else 0.0
        dong.append({
            "i": i, "chu": len(t), "tran": round(tr, 3),
            "tho": round(d_tho, 3), "cat": round(d_cat, 3),
            "ty_tho": round(d_tho / tr, 3) if tr > 0 else 0.0,
            "ty_cat": round(d_cat / tr, 3) if tr > 0 else 0.0,
            "so_lang": len(lang_giua),
            "lang_dai": round(max([b - a for a, b in lang_giua] or [0.0]), 3),
            "lang_tong": round(sum(b - a for a, b in lang_giua), 3),
            "cat_ok": bool(kq.get("ok")), "cat_ly_do": kq.get("ly_do", ""),
        })

    tong_tran = sum(d["tran"] for d in dong)
    tong_tho = sum(d["tho"] for d in dong)
    tong_cat = sum(d["cat"] for d in dong)
    ty = [d for d in dong if d["tran"] > 0]
    TEMPO_TRAN = 1.50

    print("=" * 74)
    print(" i | chữ |  trần |   THÔ | tỉ lệ |   CẮT | tỉ lệ | lặng giữa")
    print("-" * 74)
    for d in dong:
        print(f"{d['i']:2d} | {d['chu']:3d} | {d['tran']:5.2f} | "
              f"{d['tho']:5.2f} | {d['ty_tho']:5.2f} | {d['cat']:5.2f} | "
              f"{d['ty_cat']:5.2f} | {d['so_lang']} khoảng, "
              f"dài nhất {d['lang_dai']:.2f}s")
    print("=" * 74)
    r = {
        "bo": ten_bo, "lang": lang, "so_cau": len(dong),
        "tran": round(tong_tran, 2), "tho": round(tong_tho, 2),
        "cat": round(tong_cat, 2),
        "ty_tho": round(tong_tho / max(1e-9, tong_tran), 3),
        "ty_cat": round(tong_cat / max(1e-9, tong_tran), 3),
        "te_nhat_tho": round(max([d["ty_tho"] for d in ty] or [0]), 3),
        "te_nhat_cat": round(max([d["ty_cat"] for d in ty] or [0]), 3),
        "cham_tran_tho": sum(1 for d in ty if d["ty_tho"] > TEMPO_TRAN),
        "cham_tran_cat": sum(1 for d in ty if d["ty_cat"] > TEMPO_TRAN),
        "so_lang": sum(d["so_lang"] for d in dong),
        "lang_tong": round(sum(d["lang_tong"] for d in dong), 2),
        "lang_dai": round(max([d["lang_dai"] for d in dong] or [0]), 2),
        "cat_duoc": sum(1 for d in dong if d["cat_ok"]),
        "may": {"dev": ket.get("dev"), "vram_gib": ket.get("vram"),
                "nap_giay": ket.get("nap"), "gen_giay": ket.get("gen"),
                "wall_giay": round(giay_chay, 2), "torch": ket.get("torch")},
        "dong": dong,
    }
    print(f"TỔNG   trần {r['tran']:6.2f}s · THÔ {r['tho']:6.2f}s "
          f"({r['ty_tho']:.2f}x) · CẮT {r['cat']:6.2f}s ({r['ty_cat']:.2f}x)")
    print(f"CÂU TỆ NHẤT  THÔ {r['te_nhat_tho']:.2f}x · "
          f"CẮT {r['te_nhat_cat']:.2f}x   |   CHẠM TRẦN atempo 1,5: "
          f"THÔ {r['cham_tran_tho']}/{len(ty)} · CẮT {r['cham_tran_cat']}/{len(ty)}")
    print(f"LẶNG GIỮA CÂU {r['so_lang']} khoảng · tổng {r['lang_tong']:.2f}s · "
          f"dài nhất {r['lang_dai']:.2f}s   |   CẮT ĐƯỢC "
          f"{r['cat_duoc']}/{len(dong)} câu · bỏ {r['tho'] - r['cat']:.2f}s chết")
    return r


def main() -> int:
    from app.core import giong_chatter as gc

    if HOP.exists():
        shutil.rmtree(HOP, ignore_errors=True)
    HOP.mkdir(parents=True, exist_ok=True)

    tt = gc.tinh_trang()
    print(f"Chatterbox: co={tt['co']} gpu={tt['gpu']} thieu={tt['thieu']}")
    if not tt["co"]:
        print("KHÔNG có môi trường Chatterbox -> dừng, không bịa số.")
        return 2

    ref = HOP / "mau_may.wav"
    print("Sinh mẫu tham chiếu bằng edge-tts (GIỌNG MÁY, không phải người)...")
    if not edge(MAU_CAU, GIONG_MAU, ref):
        print("Không sinh được mẫu -> dừng.")
        return 2

    chon = sys.argv[1:] or list(BO)
    ra = [mot_bo(gc, b, BO[b], ref, tt["python"]) for b in chon if b in BO]
    KQ.write_text(json.dumps(ra, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    print(f"\nGhi {KQ.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
