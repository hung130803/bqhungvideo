"""ĐO NHẤN NHÁ TỪNG GIỌNG — BẢNG ĐẦY ĐỦ cho danh sách gọn của combo.

**VÌ SAO PHẢI CÓ FILE NÀY:** `_do_nhan_nha.py` (lượt 10) chỉ đo 6 giọng
Việt/OmniVoice. Tài liệu `docs/GIONG_THU_TAY.md` mục 5b có nhắc *"đo cả 47
giọng tiếng Anh"* nhưng **chỉ chép ra 5 con số lẻ** (Andrew 5,35 ·
AndrewMultilingual 5,25 · Emma 4,96 · Ryan 4,85 · Rosa 1,82) — muốn HIỆN số
cạnh MỖI giọng trong combo thì phải có số CỦA TỪNG GIỌNG, không có đường nào
khác ngoài đo lại.

**THƯỚC — dùng lại NGUYÊN XI `_do_nhan_nha.f0_nua_cung`** (độ lệch chuẩn cao
độ F0 tính bằng NỬA CUNG, khung 40 ms, tự tương quan). Import chứ không chép
lại: hai bản thước là hai bảng số không so được với nhau.

**CÂU ĐỌC PHẢI ĐÚNG TIẾNG CỦA GIỌNG.** Bắt giọng Nhật đọc câu tiếng Việt là
đo một thứ khác hẳn (máy đọc dò vần sai, F0 loạn). Mỗi ngôn ngữ một bộ câu,
mọi bộ đều có câu HỎI và câu CẢM THÁN — giọng nào biết lên xuống thì mới lộ
ra ở đúng chỗ đó.

**ĐI QUA CỬA CHUNG `dubbing._synth_all`** = đúng cửa lượt xuất thật đi, nên số
đo được là số của thứ anh Hùng sẽ nghe, không phải của một đường riêng dựng
cho phép đo.

Chạy:  .venv\\Scripts\\python -u _do_nhan_nha_bang.py            (danh sách gọn)
       .venv\\Scripts\\python -u _do_nhan_nha_bang.py en-GB-RyanNeural ...
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import statistics as st
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

FF = str(REPO / "bin" / "ffmpeg.exe")
SAN = REPO / "bq_do_nhan_nha_bang"
NOWIN = 0x08000000

#: Câu đọc theo NGÔN NGỮ. Mỗi bộ 4 câu: kể · hỏi · cảm thán · kể dài.
#: Bộ `en` và `vi` là hai bộ dùng để kết luận (tôi đọc được cả hai); các bộ
#: còn lại đủ để máy đọc phát ra tiếng đúng vần — xem phần GIỚI HẠN ở cuối.
CAU: dict[str, list[str]] = {
    "en": [
        "A storm unlike anything in recorded history is closing in on the city.",
        "But can you believe what happened only three minutes later?",
        "The whole building was gone! Nobody had time to get ready.",
        "He turned around and realised he had taken the wrong road from the start.",
    ],
    "vi": [
        "Một cơn bão chưa từng có trong lịch sử đang ập tới thành phố này.",
        "Bạn có tin được không? Chỉ trong ba phút, cả toà nhà đã biến mất!",
        "Thật không thể tin được! Cô ấy đã sống sót sau tất cả chuyện đó.",
        "Anh ta quay lại, và nhận ra mình đã đi sai đường ngay từ đầu.",
    ],
    "id": [
        "Badai yang belum pernah terjadi dalam sejarah sedang mendekati kota ini.",
        "Apakah kamu percaya apa yang terjadi tiga menit kemudian?",
        "Seluruh gedung itu hilang! Tidak ada yang sempat bersiap.",
        "Dia berbalik dan sadar bahwa dia salah jalan sejak awal.",
    ],
    "th": [
        "พายุที่ไม่เคยเกิดขึ้นมาก่อนในประวัติศาสตร์กำลังเข้าใกล้เมืองนี้",
        "คุณจะเชื่อไหมว่าเกิดอะไรขึ้นในสามนาทีต่อมา",
        "ตึกทั้งหลังหายไป ไม่มีใครทันเตรียมตัวเลย",
        "เขาหันกลับมาและรู้ว่าเขาเดินผิดทางตั้งแต่แรก",
    ],
    "ko": [
        "역사상 한 번도 없었던 폭풍이 이 도시로 다가오고 있습니다.",
        "삼 분 뒤에 무슨 일이 일어났는지 믿을 수 있나요?",
        "건물 전체가 사라졌어요! 아무도 준비할 시간이 없었습니다.",
        "그는 돌아서서 처음부터 길을 잘못 들었다는 것을 깨달았습니다.",
    ],
    "ja": [
        "歴史上かつてない嵐がこの街に近づいています。",
        "その三分後に何が起きたか、信じられますか。",
        "建物が丸ごと消えました！誰も準備する時間がありませんでした。",
        "彼は振り返り、最初から道を間違えていたことに気づきました。",
    ],
    "zh": [
        "一场史无前例的风暴正在逼近这座城市。",
        "你能相信三分钟之后发生了什么吗？",
        "整栋楼都消失了！没有人来得及做准备。",
        "他转过身，才发现自己从一开始就走错了路。",
    ],
    "es": [
        "Una tormenta como ninguna otra en la historia se acerca a esta ciudad.",
        "¿Puedes creer lo que pasó solo tres minutos después?",
        "¡El edificio entero desapareció! Nadie tuvo tiempo de prepararse.",
        "Se dio la vuelta y entendió que había tomado el camino equivocado.",
    ],
    "pt": [
        "Uma tempestade como nunca houve na história está chegando a esta cidade.",
        "Você acredita no que aconteceu apenas três minutos depois?",
        "O prédio inteiro desapareceu! Ninguém teve tempo de se preparar.",
        "Ele se virou e percebeu que tinha pegado o caminho errado desde o começo.",
    ],
    "fr": [
        "Une tempête comme il n'y en a jamais eu approche de cette ville.",
        "Pouvez-vous croire ce qui s'est passé trois minutes plus tard ?",
        "Tout le bâtiment a disparu ! Personne n'a eu le temps de se préparer.",
        "Il s'est retourné et a compris qu'il avait pris le mauvais chemin.",
    ],
    "de": [
        "Ein Sturm, wie es ihn noch nie gab, zieht auf diese Stadt zu.",
        "Können Sie glauben, was nur drei Minuten später passiert ist?",
        "Das ganze Gebäude war weg! Niemand hatte Zeit, sich vorzubereiten.",
        "Er drehte sich um und merkte, dass er von Anfang an falsch war.",
    ],
    "ru": [
        "Буря, какой не было за всю историю, приближается к этому городу.",
        "Вы можете поверить в то, что случилось всего через три минуты?",
        "Всё здание исчезло! Никто не успел подготовиться.",
        "Он обернулся и понял, что с самого начала пошёл не той дорогой.",
    ],
    "it": [
        "Una tempesta mai vista nella storia si sta avvicinando a questa città.",
        "Riesci a credere a quello che è successo solo tre minuti dopo?",
        "L'intero edificio è sparito! Nessuno ha avuto il tempo di prepararsi.",
        "Si voltò e capì di aver sbagliato strada fin dall'inizio.",
    ],
    "ar": [
        "عاصفة لم يشهد التاريخ مثلها تقترب من هذه المدينة.",
        "هل تصدق ما حدث بعد ثلاث دقائق فقط؟",
        "اختفى المبنى بالكامل! لم يجد أحد وقتا للاستعداد.",
        "استدار وأدرك أنه سلك الطريق الخطأ منذ البداية.",
    ],
    "hi": [
        "इतिहास में कभी न आया ऐसा तूफ़ान इस शहर की ओर बढ़ रहा है।",
        "क्या आप यकीन कर सकते हैं कि तीन मिनट बाद क्या हुआ?",
        "पूरी इमारत गायब हो गई! किसी को तैयारी का समय नहीं मिला।",
        "उसने पीछे मुड़कर देखा और समझा कि वह शुरू से ही गलत रास्ते पर था।",
    ],
}


#: Máy đọc KHÔNG phải edge-tts -> id không mang mã ngôn ngữ (`ov:nam_tre`,
#: `piper:vais1000`). Chúng đọc tiếng VIỆT trên máy anh Hùng, và cho chúng đọc
#: **cùng bộ câu Việt với `vi-VN-*`** chính là phép so DUY NHẤT có nghĩa: cùng
#: tiếng, cùng câu, cùng thước.
#:
#: **BẪY ĐÃ SẬP 1 LẦN, GIỮ LẠI ĐỂ ĐỪNG LẶP:** bản đầu tách tiền tố bằng
#: `voice.split("-")[0]` nên `piper:vais1000` không khớp mã nào rồi rơi vào
#: nhánh lùi **tiếng Anh** — bắt một model CHỈ BIẾT TIẾNG VIỆT đọc câu tiếng
#: Anh rồi ghi số vào bảng. Nó ra 1,88 (thấp nhất toàn bảng) và trông rất
#: giống một kết luận thật.
#:
#: **BẪY ĐÓ SẬP LẠI LẦN THỨ HAI VỚI `vn:` (VieNeu) — 19/08/2026.** Danh sách
#: này ra đời trước `giong_vieneu.py`, nên `vn:Minh Đức` không khớp tiền tố
#: nào -> `"vn:minh đức".split("-")[0]` không có trong `CAU` -> **rơi đúng
#: nhánh lùi tiếng Anh**. Tức lượt đo 20 giọng VieNeu (bộ đọc CHỈ BIẾT TIẾNG
#: VIỆT) sẽ bắt chúng đọc *"A storm unlike anything in recorded history…"*
#: rồi ghi số vào cùng cột với `vi-VN-*`.
#:
#: **NÓI THẲNG SỐ ĐO, KHÔNG KHOE:** `_do_nhan_nha_vn.py` phần 1 đo bẫy này
#: trên `vn:Ngọc Huyền` — bộ câu Việt **3,10** so với bộ câu Anh **2,82**,
#: lệch **0,28**. Nhưng cùng lượt đó phát hiện chuyện lớn hơn: **VieNeu KHÔNG
#: TIỀN ĐỊNH** — cùng giọng, cùng bộ câu Việt, hai lượt ra **3,28 và 2,92**
#: (trải 0,36, tức LỚN HƠN chênh lệch giữa hai bộ câu). Vậy phép đo 2 lượt
#: **không tách được** hai nguyên nhân, và con số 0,28 KHÔNG được kể là "bằng
#: chứng bẫy". Cái vá này đứng vững vì lý do CẤU TẠO (VieNeu là bộ đọc tiếng
#: Việt, bắt nó đọc tiếng Anh là đo thứ khác), không vì con số.
#: **`kk:` (Kokoro) CỐ Ý KHÔNG CÓ TRONG DANH SÁCH NÀY — ĐỪNG THÊM VÀO.**
#: Danh sách này nghĩa là *"máy đọc này đọc TIẾNG VIỆT"*. Kokoro **KHÔNG có
#: tiếng Việt**: 28/28 giọng là `af_/am_/bf_/bm_` = Mỹ/Anh (xem
#: `giong_kokoro.GIONG_KK`). Thêm `kk:` vào đây là bắt một bộ đọc CHỈ BIẾT
#: TIẾNG ANH đọc 4 câu tiếng Việt rồi ghi số vào cùng cột với `vi-VN-*` — đúng
#: cái bẫy đã làm `piper:vais1000` ra 1,88 (thấp nhất toàn bảng), chỉ là quay
#: ngược chiều. Gặp `ValueError` khi chạy `_do_nhan_nha_bang.py kk:...` thì
#: **đó là chốt đang làm việc**, không phải lỗi cần vá: giọng Kokoro đo bằng
#: `_do_nhan_nha_kk.py` (bộ câu `CAU["en"]` + đối chứng edge-tts tiếng Anh).
NGOAI_EDGE = ("ov:", "ix:", "piper:", "vn:", "vnb:")


def cau_cho(voice: str) -> list[str]:
    """Bộ câu đúng tiếng của giọng.

    **KHÔNG ĐOÁN ĐƯỢC THÌ NÉM, ĐỪNG LÙI TIẾNG ANH.** Nhánh lùi im lặng chính
    là chỗ `piper:vais1000` (1,88) và `vn:` chui vào. Giọng edge-tts luôn mang
    mã `<nn>-<VÙNG>-<Tên>Neural` nên tra bảng là ra; mã có dấu `:` mà chưa
    khai trong `NGOAI_EDGE` nghĩa là có nguồn giọng MỚI — người thêm nguồn
    phải tự khai nó đọc tiếng gì, chứ không để phép đo tự bịa hộ.
    """
    v = str(voice)
    if v.startswith(NGOAI_EDGE):
        return CAU["vi"]
    if ":" in v:
        raise ValueError(
            f"giọng {v!r} mang tiền tố lạ — khai vào `NGOAI_EDGE` (nếu nó đọc "
            f"tiếng Việt) trước khi đo, đừng để nó lùi về câu tiếng Anh")
    return CAU.get(v.split("-")[0].lower()) or CAU["en"]


def ra_wav(src: Path, dst: Path) -> bool:
    r = subprocess.run([FF, "-y", "-v", "error", "-i", str(src), "-ac", "1",
                        "-ar", "16000", "-f", "wav", str(dst)],
                       capture_output=True, creationflags=NOWIN, timeout=300)
    return r.returncode == 0 and dst.exists() and dst.stat().st_size > 1000


def do_mot(voice: str) -> dict:
    """Đọc 4 câu bằng CỬA CHUNG rồi đo F0 -> nhấn nhá (nửa cung)."""
    from _do_nhan_nha import f0_nua_cung
    from app.core import dubbing

    texts = cau_cho(voice)
    tm = SAN / voice.replace(":", "_").replace("-", "_")
    shutil.rmtree(tm, ignore_errors=True)
    tm.mkdir(parents=True, exist_ok=True)
    paths = [str(tm / f"c{i}.mp3") for i in range(len(texts))]
    t0 = time.monotonic()
    try:
        ok = asyncio.run(dubbing._synth_all(texts, voice, paths))
    except Exception as e:                                    # noqa: BLE001
        return {"loi": f"{type(e).__name__}: {e}"}
    files = [p for p, o in zip(paths, ok) if o and Path(p).exists()]
    if not files:
        return {"loi": "không đọc được câu nào"}
    tat: list[float] = []
    for i, p in enumerate(files):
        w = tm / f"w{i}.wav"
        if not ra_wav(Path(p), w):
            continue
        d = f0_nua_cung(w)
        if len(d) >= 20:
            tat.extend(d)
    if len(tat) < 50:
        return {"loi": f"quá ít khung có tiếng ({len(tat)})"}
    return {"nhan_nha": round(st.pstdev(tat), 2),
            "so_khung": len(tat), "so_cau": len(files),
            "f0_giua_hz": round(100.0 * 2 ** (st.median(tat) / 12.0), 1),
            "giay": round(time.monotonic() - t0, 1)}


def danh_sach_gon() -> list[str]:
    """Đúng tập giọng combo hiện ra ở danh sách gọn (không cần 'tất cả')."""
    from app.core import dubbing
    allv = dubbing._fetch_all_voices()
    ra = [v["ShortName"] for v in allv
          if v.get("ShortName") in dubbing._HOT_VOICES
          or dubbing._la_giong_mo_them(v)]
    return sorted(set(ra))


if __name__ == "__main__":
    SAN.mkdir(exist_ok=True)
    ds = sys.argv[1:] or danh_sach_gon()
    print(f"ĐO NHẤN NHÁ {len(ds)} GIỌNG (F0 std, nửa cung) — cửa chung "
          f"dubbing._synth_all")
    print("-" * 72)
    print(f"{'giọng':34s} {'nhấn nhá':>9s} {'F0 giữa':>9s} {'khung':>7s} "
          f"{'giây':>6s}")
    ra: dict = {}
    kq = SAN / "ket_qua.json"
    if kq.exists():                       # chạy lại thì không đo lại từ đầu
        try:
            ra = json.loads(kq.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            ra = {}
    for v in ds:
        if v in ra and not ra[v].get("loi"):
            d = ra[v]
        else:
            d = do_mot(v)
            ra[v] = d
            kq.write_text(json.dumps(ra, ensure_ascii=False, indent=1),
                          encoding="utf-8")
        if d.get("loi"):
            print(f"{v:34s} LỖI: {d['loi']}")
        else:
            print(f"{v:34s} {d['nhan_nha']:9.2f} {d['f0_giua_hz']:8.1f}Hz "
                  f"{d['so_khung']:7d} {d.get('giay', 0):6.1f}")
    tot = {k: v["nhan_nha"] for k, v in ra.items()
           if k in set(ds) and not v.get("loi")}
    if tot:
        xs = sorted(tot.values())
        print("-" * 72)
        print(f"ĐO ĐƯỢC {len(tot)}/{len(ds)} giọng · thấp nhất {xs[0]:.2f} · "
              f"cao nhất {xs[-1]:.2f} · TRẢI {xs[-1] - xs[0]:.2f}")
        top = sorted(tot.items(), key=lambda kv: -kv[1])[:8]
        print("CAO NHẤT: " + " · ".join(f"{k} {v:.2f}" for k, v in top))
    print(f"\n-> {kq}")
