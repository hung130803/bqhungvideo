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

**ĐO ĐƯỢC 26/08/2026 — MODEL TIỀN ĐỊNH TUYỆT ĐỐI, LO NGẠI Ở TRÊN LÀ THỪA (ở
chiều này) NHƯNG THIẾU Ở CHIỀU KHÁC.** 6 câu dùng chung giữa bộ `zh_goc` và
bộ `zh` cho ra tỉ lệ **giống nhau tới 2 chữ số thập phân** (1,00 · 1,28 ·
1,17 · 2,64 · 1,18 · 1,00) dù chạy ở **hai tiến trình khác nhau** và **hai vị
trí khác nhau trong mẻ**. Tức `(chữ, mẫu, tiếng, seed)` -> ra một kết quả duy
nhất; "thứ tự gọi và trạng thái model" KHÔNG ảnh hưởng.
**Cái THẬT SỰ đổi kết quả là BYTE của FILE MẪU** — xem khối `MAU` ở dưới.

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
MẪU THAM CHIẾU LÀ **MỘT ARM**, KHÔNG PHẢI HẰNG SỐ — VÁ 26/08/2026
═══════════════════════════════════════════════════════════════════════════
Bản đầu ghi cứng **một** mẫu (`en-US-AndrewMultilingual`) rồi kết luận cho cả
bộ. Đó là chỗ hổng chết người của lượt đo ấy: `_do_chatter_dangn.py` đã ghi
thẳng rằng *"lỗi đi theo **CẶP** (mẫu × ngôn ngữ)"* — cùng bộ câu tiếng Trung
mà `A_nu` ra **6,86 s/câu** còn `B_nam` chỉ **3,04 s/câu**. Đo bằng một mẫu
KHÁC hẳn rồi nói *"không tái hiện được"* là đang đo một arm khác và tưởng
mình đã bác bỏ arm cũ.

Nên `MAU` ở dưới là **bảng**, và mỗi lượt đo nêu rõ arm = `<bộ>@<mẫu>`.

**KẾT QUẢ 26/08/2026 — 3 VÒNG ĐAN XEN CÓ XOAY THỨ TỰ, và biên độ đọc ra là
`0,000`:** vòng 1 và vòng 2 ra **GIỐNG NHAU TỚI TỪNG CHỮ SỐ** ở cả 4 arm. Đó
không phải may — nó là hệ quả của tính tiền định vừa nói ở trên, và nó **đổi
cách đọc bảng cũ**: con số 1,81x của lượt 25/08 KHÔNG phải số rút thăm, nên
"đo lại không ra" là dấu hiệu **đo khác arm**, không phải dấu hiệu nhiễu.
Đo bằng CHÍNH file mẫu của lượt cũ (`_do_chatter_zh_mau.py`) ra **1,798x** so
với **1,806x** của bảng cũ, khớp tới TỪNG CÂU.

    arm (thước SAU cắt lề) | trần  | THÔ           | SAU CẮT LẶNG  | tệ nhất
    zh_goc@A_nu            | 25,52 | 50,14 (1,97x) | 47,16 (1,85x) | 3,79->3,56
    zh_goc@B_nam           | 25,52 | 20,88 (0,82x) | 20,70 (0,81x) | 1,00->1,00
    zh@A_nu (trộn dài)     | 62,50 | 78,85 (1,26x) | 75,07 (1,20x) | 3,33->2,80
    en_ngan@A_nu (đ.chứng) | 37,75 | 49,91 (1,32x) | 46,88 (1,24x) | 1,79->1,68

═══════════════════════════════════════════════════════════════════════════
RANH GIỚI CỨNG — MẪU THAM CHIẾU LÀ **GIỌNG MÁY**
═══════════════════════════════════════════════════════════════════════════
Mẫu để nhân bản trong lượt đo này sinh bằng **edge-tts** (giọng máy), KHÔNG
lấy giọng người thật nào. Cụ thể là **KHÔNG dùng `_mau_giong/adam_clone.wav`**
— nguồn của file đó là bản sao một giọng ElevenLabs thương mại.

Chạy:  .venv\\Scripts\\python.exe _do_chatter_nhip.py [arm...] [--vong N]
       arm = `<bộ>` (dùng mẫu mặc định) hoặc `<bộ>@<mẫu>`
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
#:
#: `A_nu`/`B_nam` là **ĐÚNG hai mẫu của `_do_chatter_dangn.py`** (cùng giọng,
#: cùng `CAU_MAU`) — không chép lại số, mà dựng lại đúng arm để so được. `nhip`
#: là mẫu bản đầu của chính file này, giữ để mọi số cũ còn tái lập được.
GIONG_MAU = "en-US-AndrewMultilingualNeural"

MAU: dict[str, str] = {
    "nhip": GIONG_MAU,
    "A_nu": "vi-VN-HoaiMyNeural",
    "B_nam": "vi-VN-NamMinhNeural",
}

#: Câu đọc để LÀM MẪU cho `A_nu`/`B_nam` — chép nguyên văn
#: `_do_chatter_dangn.CAU_MAU`. Mẫu khác chữ là mẫu khác, và cả bảng số lại
#: không so được với lượt trước nữa.
CAU_MAU_DANGN = ("Đây là đoạn ghi âm ngắn để làm mẫu giọng của tôi. Tôi đọc "
                 "thêm vài câu nữa cho đủ dài, để máy có cái mà học theo.")

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
    # ═══════════════════════════════════════════════════════════════════════
    # `zh_goc` — DỰNG LẠI ĐÚNG ARM ĐÃ SINH RA CON SỐ 1,81x
    # ═══════════════════════════════════════════════════════════════════════
    # **KHÔNG bịa câu mới, KHÔNG lấy mẫu khác.** Đây là ĐÚNG 8 câu mà
    # `_do_chatter_dangn.cau_cua("zh")` trả về (`CORPUS["zh"]` lọc
    # `cau_thuong` + `ban_dia`, cắt ở `SO_CAU`=8), đọc bằng ĐÚNG mẫu `A_nu`.
    # Chép tay 8 câu vào đây thay vì `import` là **cố ý**: `SO_CAU` đọc biến
    # môi trường `BQ_CB_CAU` nên bộ câu của lượt sau có thể khác lượt trước mà
    # không ai thấy — mà bộ này tồn tại đúng để **đóng băng** arm cũ. Mục tự
    # kiểm ở `main()` đối chiếu lại với corpus, nên chép lệch là bị kêu.
    #
    # ĐẶC ĐIỂM PHẢI GHI RA: **cả 8 câu đều 14-20 ký tự Hán**, không câu nào
    # dài. Tức arm sinh ra 1,81x là arm **TOÀN CÂU NGẮN** — đúng hình dạng mà
    # bộ `en_dai` đã chỉ ra là chỗ Chatterbox đọc lan man. Đó là lý do phải có
    # thêm bộ `zh` trộn ngắn/dài ở dưới, nếu không thì không tách được
    # *"tiếng Trung hỏng"* với *"câu ngắn hỏng"*.
    "zh_goc": {
        "tran": "zh-CN-XiaoxiaoNeural", "lang": "zh", "mau": "A_nu",
        "cau": [
            "今天天气很好，我们一起出去走走吧。",
            "他打开门，走进了那间黑暗的房间。",
            "她对他笑了笑，然后一句话也没说就走了。",
            "我们在那里等了整整一个下午。",
            "李小龙 是很多人心目中的英雄。",
            "他们全家搬到 乌鲁木齐 已经很多年了。",
            "从 北京 到 上海 的高铁只要几个小时。",
            "重庆 的火锅是全国最有名的。",
        ],
    },
    # ═══════════════════════════════════════════════════════════════════════
    # `zh` — 12 câu, TRỘN NGẮN VÀ DÀI, đúng khuôn hai bộ `en_*`
    # ═══════════════════════════════════════════════════════════════════════
    # 6 câu NGẮN: lấy thẳng `_bo_cau_thu_doc.CORPUS["zh"]` (bộ chuẩn đã có).
    # 6 câu DÀI: **KHÔNG bịa** — ghép các đoạn LIỀN NHAU của bản chép lời THẬT
    # trong `_do_tg_cache.json` khoá `chep|zh|90.0` (video Douyin anh Hùng
    # đang làm, Groq chép). Corpus `zh` chuẩn dài nhất mới 20 ký tự và bản chép
    # lời thật dài nhất 18, nên không có sẵn câu dài nào; ghép đoạn liền nhau
    # là cách duy nhất có câu dài mà vẫn là chữ THẬT của đúng nguồn sản xuất.
    # (Bỏ mấy đoạn lặp `你這個混蛋` — lặp chữ là một biến số khác chen vào.)
    "zh": {
        "tran": "zh-CN-XiaoxiaoNeural", "lang": "zh", "mau": "A_nu",
        "cau": [
            "今天天气很好，我们一起出去走走吧。",
            "他打开门，走进了那间黑暗的房间。",
            "她对他笑了笑，然后一句话也没说就走了。",
            "我们在那里等了整整一个下午。",
            "李小龙 是很多人心目中的英雄。",
            "重庆 的火锅是全国最有名的。",
            "老头只是扛着猪走在回家的路上，却被一群手持武器的童子军拦了下来，"
            "领头的男孩蛮不讲理，一口咬定。",
            "这头猪是老头偷来的，他要代表正义将其没收，面对黑洞洞的枪口。",
            "在伙伴们的欢呼声中，得意地大喊着继续前进，随后这支童子军队伍，"
            "便朝着最终目的地一路杀去。",
            "可不料他们刚走出一半，却突然遭到了伏击，头目强尼立刻下车。",
            "指挥手下分散搜索敌人的踪迹，可一番排查下来，只找到了一把冲锋枪，"
            "和一个蜷缩在墙角的男孩。",
            "强尼认定是对方开的枪，便命人扒掉他的衣服，将他的双手反绑在背后。",
        ],
    },
}

#: Arm CHẠY MẶC ĐỊNH — `<bộ>@<mẫu>`. Bốn arm này trả lời đúng bốn câu hỏi:
#:   · `zh_goc@A_nu`   — 1,81x có tái hiện không (dựng lại y nguyên arm cũ)
#:   · `zh_goc@B_nam`  — CÙNG bộ câu, ĐỔI mẫu: tật đi theo CẶP hay theo TIẾNG
#:   · `zh@A_nu`       — CÙNG mẫu, thêm câu DÀI: tật theo TIẾNG hay theo ĐỘ DÀI
#:   · `en_ngan@A_nu`  — ĐỐI CHỨNG chạy CÙNG LƯỢT. Không có nó thì không biết
#:     máy/bản gói hôm nay có còn giống hôm đo lần trước không, và mọi so sánh
#:     với bảng cũ là so hai môi trường khác nhau.
ARM_MAC_DINH = ("zh_goc@A_nu", "zh_goc@B_nam", "zh@A_nu", "en_ngan@A_nu")

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


def dai_tho(gc, p: Path) -> float:
    """Độ dài **CHƯA cắt lề** — đúng thước mà bảng cũ 1,81x đã dùng.

    ``_do_chatter_dangn.do_dai`` đọc thẳng chiều dài file WAV, tức **tính cả
    lề im hai đầu**. Muốn nói *"1,81x tái hiện hay không"* thì phải đo lại
    bằng ĐÚNG thước đó trước; đo bằng thước đã cắt lề rồi bảo *"không tái
    hiện"* là trả lời một câu hỏi khác.
    Hai thước ở đây chạy **cùng lượt, trên cùng file**, nên đọc được cả hai.
    """
    try:
        return float(gc._do_lang(p)[0])
    except Exception:                                          # noqa: BLE001
        return 0.0


def mot_bo(gc, ten_bo: str, cfg: dict, ref: Path, py: str,
           ten_mau: str = "nhip", vong: int = 0) -> dict:
    """Đo MỘT arm (bộ câu × mẫu). Trả dict số đo (đã in bảng ra màn hình)."""
    cau = list(cfg["cau"])
    lang = cfg["lang"]
    arm = f"{ten_bo}@{ten_mau}"
    thu = HOP / f"{ten_bo}__{ten_mau}" / f"v{vong}"
    thu.mkdir(parents=True, exist_ok=True)

    print(f"\n### ARM «{arm}» vòng {vong + 1} ({len(cau)} câu, tiếng {lang}) "
          f"— trần = {cfg['tran']}")
    # Trần là edge-tts: TIỀN ĐỊNH, nên sinh MỘT lần rồi dùng lại cho mọi vòng.
    # Sinh lại mỗi vòng không sai số nhưng tốn mạng và làm cột `giây chạy` của
    # arm lẫn thời gian tải edge-tts (= đo mạng, không đo model).
    kho_tran = HOP / f"tran__{ten_bo}"
    kho_tran.mkdir(parents=True, exist_ok=True)
    tran: list[float] = []
    tran_tho: list[float] = []
    for i, t in enumerate(cau):
        p = kho_tran / f"tran_{i:02d}.wav"
        sach = kho_tran / f"tran_sach_{i:02d}.wav"
        if not (p.exists() and sach.exists()):
            if not edge(t, cfg["tran"], p):
                tran.append(0.0)
                tran_tho.append(0.0)
                continue
            cat_le(p, sach)
        tran.append(float(gc._do_lang(sach)[0]))
        tran_tho.append(dai_tho(gc, p))
    print(f"  trần: {sum(tran):.2f}s (cắt lề) · {sum(tran_tho):.2f}s (thô)")

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
        # MỘT THƯỚC CHO CẢ HAI PHÍA. Bản đầu lấy trần bằng giá trị trả về của
        # `cat_le_im_moc` còn THÔ cũng vậy — cùng thước nên đúng; nhưng từ khi
        # trần được CACHE qua các vòng thì phải đo lại từ FILE, và lúc đó hai
        # phía dễ rơi vào hai thước khác nhau. Nay mọi độ dài đều đọc bằng
        # `gc._do_lang`, `cat_le` chỉ còn việc GHI RA file đã cắt lề.
        sach_tho = thu / f"tho_sach_{i:02d}.wav"
        cat_le(raw, sach_tho)
        d_tho = float(gc._do_lang(sach_tho)[0])
        d_tho_le = dai_tho(gc, raw)
        _dai, lang_giua = gc.khoang_lang_giua(raw)
        cat = thu / f"cat_{i:02d}.wav"
        kq = gc.cat_lang_giua(raw, cat)
        if kq.get("ok"):
            sach_cat = thu / f"cat_sach_{i:02d}.wav"
            cat_le(cat, sach_cat)
            d_cat = float(gc._do_lang(sach_cat)[0])
        else:
            d_cat = d_tho
        tr = tran[i] if i < len(tran) else 0.0
        tr_le = tran_tho[i] if i < len(tran_tho) else 0.0
        dong.append({
            "i": i, "chu": len(t), "tran": round(tr, 3),
            "tho": round(d_tho, 3), "cat": round(d_cat, 3),
            "tran_le": round(tr_le, 3), "tho_le": round(d_tho_le, 3),
            "ty_tho": round(d_tho / tr, 3) if tr > 0 else 0.0,
            "ty_cat": round(d_cat / tr, 3) if tr > 0 else 0.0,
            "ty_le": round(d_tho_le / tr_le, 3) if tr_le > 0 else 0.0,
            "so_lang": len(lang_giua),
            "lang_dai": round(max([b - a for a, b in lang_giua] or [0.0]), 3),
            "lang_tong": round(sum(b - a for a, b in lang_giua), 3),
            "cat_ok": bool(kq.get("ok")), "cat_ly_do": kq.get("ly_do", ""),
        })

    tong_tran = sum(d["tran"] for d in dong)
    tong_tho = sum(d["tho"] for d in dong)
    tong_cat = sum(d["cat"] for d in dong)
    tong_tran_le = sum(d["tran_le"] for d in dong)
    tong_tho_le = sum(d["tho_le"] for d in dong)
    ty = [d for d in dong if d["tran"] > 0]
    ty_le = [d for d in dong if d["tran_le"] > 0]
    TEMPO_TRAN = 1.50

    print("=" * 84)
    print(" i | chữ |  trần |   THÔ | tỉ lệ |   CẮT | tỉ lệ | THÔ-lề | lặng giữa")
    print("-" * 84)
    for d in dong:
        print(f"{d['i']:2d} | {d['chu']:3d} | {d['tran']:5.2f} | "
              f"{d['tho']:5.2f} | {d['ty_tho']:5.2f} | {d['cat']:5.2f} | "
              f"{d['ty_cat']:5.2f} | {d['ty_le']:6.2f} | {d['so_lang']} khoảng, "
              f"dài nhất {d['lang_dai']:.2f}s")
    print("=" * 84)
    r = {
        "arm": arm, "bo": ten_bo, "mau": ten_mau, "vong": vong,
        "lang": lang, "so_cau": len(dong),
        "tran": round(tong_tran, 2), "tho": round(tong_tho, 2),
        "cat": round(tong_cat, 2),
        "tran_le": round(tong_tran_le, 2), "tho_le": round(tong_tho_le, 2),
        "ty_tho": round(tong_tho / max(1e-9, tong_tran), 3),
        "ty_cat": round(tong_cat / max(1e-9, tong_tran), 3),
        # THƯỚC CŨ (chưa cắt lề) — chính là thước của con số 1,81x.
        "ty_le": round(tong_tho_le / max(1e-9, tong_tran_le), 3),
        "te_nhat_le": round(max([d["ty_le"] for d in ty_le] or [0]), 3),
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
    print(f"THƯỚC CŨ (CHƯA cắt lề, đúng thước của con số 1,81x): "
          f"trần {r['tran_le']:6.2f}s · THÔ {r['tho_le']:6.2f}s "
          f"({r['ty_le']:.2f}x) · câu tệ nhất {r['te_nhat_le']:.2f}x")
    print(f"CÂU TỆ NHẤT  THÔ {r['te_nhat_tho']:.2f}x · "
          f"CẮT {r['te_nhat_cat']:.2f}x   |   CHẠM TRẦN atempo 1,5: "
          f"THÔ {r['cham_tran_tho']}/{len(ty)} · CẮT {r['cham_tran_cat']}/{len(ty)}")
    print(f"LẶNG GIỮA CÂU {r['so_lang']} khoảng · tổng {r['lang_tong']:.2f}s · "
          f"dài nhất {r['lang_dai']:.2f}s   |   CẮT ĐƯỢC "
          f"{r['cat_duoc']}/{len(dong)} câu · bỏ {r['tho'] - r['cat']:.2f}s chết")
    return r


def tach_arm(s: str) -> tuple[str, str]:
    """``"zh_goc@A_nu"`` -> ``("zh_goc", "A_nu")``; ``"ja"`` -> mẫu của bộ."""
    if "@" in s:
        bo, mau = s.split("@", 1)
        return bo.strip(), mau.strip()
    return s.strip(), str(BO.get(s.strip(), {}).get("mau") or "nhip")


def tu_kiem_bo_cau() -> bool:
    """`zh_goc` có đúng là bộ câu của arm cũ không — ĐỐI CHIẾU, không tin tay.

    Bộ đó được chép tay vào file này để **đóng băng** arm cũ (xem ghi chú ở
    `BO["zh_goc"]`). Chép tay thì lệch được, mà lệch một câu là cả kết luận
    *"1,81x tái hiện hay không"* nói về một arm KHÁC. Nên mục này dựng lại bộ
    câu bằng đúng phép lọc của `_do_chatter_dangn.cau_cua("zh")` rồi so.
    """
    try:
        from _bo_cau_thu_doc import CORPUS
    except Exception as e:                                     # noqa: BLE001
        print(f"  [tự kiểm] KHÔNG đọc được corpus: {e}")
        return False
    goc = [c for loai in ("cau_thuong", "ban_dia")
           for (l, c, _t) in CORPUS["zh"] if l == loai][:8]
    dung = list(BO["zh_goc"]["cau"]) == goc
    print(f"  [tự kiểm] `zh_goc` khớp corpus chuẩn: "
          f"{'ĐÚNG' if dung else 'LỆCH'} ({len(goc)} câu)")
    if not dung:
        for a, b in zip(BO["zh_goc"]["cau"], goc):
            if a != b:
                print(f"    lệch: «{a}» vs «{b}»")
    # ...và bộ `zh` phải THẬT SỰ có cả câu ngắn lẫn câu dài, nếu không thì nó
    # chỉ là `zh_goc` viết dài dòng và không tách được hai giả thuyết.
    do_dai = sorted(len(c) for c in BO["zh"]["cau"])
    tron = do_dai[0] <= 20 and do_dai[-1] >= 40
    print(f"  [tự kiểm] bộ `zh` trộn ngắn/dài: "
          f"{'ĐÚNG' if tron else 'KHÔNG'} (ngắn nhất {do_dai[0]} · "
          f"dài nhất {do_dai[-1]} ký tự)")
    return dung and tron


def main() -> int:
    from app.core import giong_chatter as gc

    dsl = [a for a in sys.argv[1:] if not a.startswith("--")]
    so_vong = 1
    for a in sys.argv[1:]:
        if a.startswith("--vong"):
            try:
                so_vong = max(1, int(a.split("=", 1)[1]))
            except (IndexError, ValueError):
                so_vong = 3
    arms = [tach_arm(a) for a in (dsl or list(ARM_MAC_DINH))]
    arms = [(b, m) for b, m in arms if b in BO and m in MAU]
    if not arms:
        print("Không có arm nào hợp lệ.")
        return 2

    if HOP.exists():
        shutil.rmtree(HOP, ignore_errors=True)
    HOP.mkdir(parents=True, exist_ok=True)

    tt = gc.tinh_trang()
    print(f"Chatterbox: co={tt['co']} gpu={tt['gpu']} thieu={tt['thieu']}")
    if not tt["co"]:
        print("KHÔNG có môi trường Chatterbox -> dừng, không bịa số.")
        return 2
    print("TỰ KIỂM BỘ CÂU (chép tay thì lệch được):")
    tu_kiem_bo_cau()

    # Mẫu tham chiếu — sinh MỘT lần cho mỗi tên mẫu, dùng chung mọi vòng.
    ref: dict[str, Path] = {}
    for ten in sorted({m for _b, m in arms}):
        p = HOP / f"mau_{ten}.wav"
        cau = MAU_CAU if ten == "nhip" else CAU_MAU_DANGN
        print(f"Sinh mẫu «{ten}» = {MAU[ten]} (GIỌNG MÁY, không phải người)...")
        if not edge(cau, MAU[ten], p):
            print("Không sinh được mẫu -> dừng.")
            return 2
        ref[ten] = p

    # ═══ ĐAN XEN + XOAY THỨ TỰ ═══
    # Máy này LUÔN có prodown tải nền; đo liền mạch đã ra kết luận sai 2 lần
    # trong repo này. Vòng `v` bắt đầu từ arm thứ `v` nên không arm nào luôn
    # được chạy lúc máy vừa nghỉ / vừa nóng.
    ra: list[dict] = []
    for v in range(so_vong):
        thu_tu = arms[v % len(arms):] + arms[:v % len(arms)]
        print(f"\n{'#' * 74}\n# VÒNG {v + 1}/{so_vong} — thứ tự: "
              f"{', '.join(f'{b}@{m}' for b, m in thu_tu)}\n{'#' * 74}")
        for bo, mau in thu_tu:
            ra.append(mot_bo(gc, bo, BO[bo], ref[mau], tt["python"], mau, v))

    bang_tong(ra, so_vong)
    KQ.write_text(json.dumps(ra, ensure_ascii=False, indent=1),
                  encoding="utf-8")
    print(f"\nGhi {KQ.name}")
    return 0


def bang_tong(ra: list[dict], so_vong: int) -> None:
    """Bảng cuối — **in kèm SỐ LƯỢT và BIÊN ĐỘ THÔ để người đọc tự thấy nhiễu**.

    Lấy **lượt NHANH NHẤT** mỗi arm làm dòng chính (luật đo của repo này: máy
    luôn có việc nền, lượt chậm là lượt bị tranh CPU). Nhưng con số quan tâm ở
    đây là TỈ LỆ ĐỘ DÀI, mà Chatterbox có **đóng seed** nên tỉ lệ đó lẽ ra
    phải TIỀN ĐỊNH — vì vậy cột `biên độ` mới là cột đáng đọc: nó ≈ 0 thì bảng
    này đọc thẳng được, còn nó to thì mọi con số một-lượt (kể cả 1,81x của
    bảng cũ) là số RÚT THĂM.
    """
    theo: dict[str, list[dict]] = {}
    for r in ra:
        if r.get("loi"):
            continue
        theo.setdefault(str(r.get("arm")), []).append(r)
    if not theo:
        return
    print("\n" + "=" * 96)
    print(f"BẢNG TỔNG — {so_vong} vòng, đan xen + xoay thứ tự")
    print("=" * 96)
    print("arm                | n |  trần |   THÔ |  x THÔ |  x CẮT | "
          "x THƯỚC-CŨ | biên độ x THÔ")
    print("-" * 96)
    for arm, ds in theo.items():
        nhanh = min(ds, key=lambda d: d["may"]["wall_giay"])
        v_tho = [d["ty_tho"] for d in ds]
        print(f"{arm:<18} | {len(ds)} | {nhanh['tran']:5.2f} | "
              f"{nhanh['tho']:5.2f} | {nhanh['ty_tho']:6.3f} | "
              f"{nhanh['ty_cat']:6.3f} | {nhanh['ty_le']:10.3f} | "
              f"{min(v_tho):.3f}-{max(v_tho):.3f} "
              f"(rộng {max(v_tho) - min(v_tho):.3f})")
    print("-" * 96)
    for arm, ds in theo.items():
        nhanh = min(ds, key=lambda d: d["may"]["wall_giay"])
        w = [d["may"]["wall_giay"] for d in ds]
        print(f"{arm:<18} | tệ nhất THÔ {nhanh['te_nhat_tho']:.2f}x -> CẮT "
              f"{nhanh['te_nhat_cat']:.2f}x · chạm trần atempo 1,5 "
              f"{nhanh['cham_tran_tho']}->{nhanh['cham_tran_cat']}"
              f"/{nhanh['so_cau']} · lặng giữa {nhanh['so_lang']} khoảng "
              f"(dài nhất {nhanh['lang_dai']:.2f}s, tổng "
              f"{nhanh['lang_tong']:.2f}s) · giây chạy {min(w):.1f}-{max(w):.1f}")
    print("=" * 96)


if __name__ == "__main__":
    raise SystemExit(main())
