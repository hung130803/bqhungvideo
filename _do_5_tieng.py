# -*- coding: utf-8 -*-
"""GIỌNG NÀO ĐỌC ĐƯỢC MẤY TRONG NĂM TIẾNG — Việt · Anh · Hàn · Nhật · Trung.

Anh Hùng 19/08/2026: *"Giọng nào đọc chỉ 1 ngôn ngữ thì ghi rõ; cái nào 1
giọng đọc được cả tiếng Anh tiếng Việt cũng được"* · *"giọng nào đa ngôn ngữ
cứ báo tôi nhé, nhiều giọng đọc hết oke cả Hàn Nhật Mỹ Trung mà rất hay ấy"*.

═══════════════════════════════════════════════════════════════════════════
MỆNH ĐỀ TRUNG TÂM: NHÃN "Multilingual" **KHÔNG PHẢI BẰNG CHỨNG**
═══════════════════════════════════════════════════════════════════════════
App đang gắn nhãn "đọc được mọi thứ tiếng" cho 12 giọng chỉ vì **TÊN GIỌNG
CÓ CHỮ "Multilingual"** — tức đang tin lời nhà cung cấp, chưa ai bắt đọc thử.

Ca đối chiếu nằm ngay trong repo và nó đắt: **Chatterbox** cũng tự nhận đa
ngôn ngữ, ép đọc *"Một cơn bão chưa từng có"* thì ra ***"Mokonbel, Chutanko,
Tronglaichsatanglaich"*** — sai 100%, **không ném lỗi, mã thoát 0**. Đó chính
xác là thứ một cái nhãn sai sẽ đẩy vào tay anh Hùng: chọn giọng, xuất 300
video, không một dòng báo.

Nên file này KHÔNG hỏi *"Microsoft ghi gì"*, nó hỏi *"ĐỌC RA CÓ ĐÚNG CHỮ
KHÔNG"* — và trả lời bằng số.

═══════════════════════════════════════════════════════════════════════════
ĐI QUA CỬA THẬT
═══════════════════════════════════════════════════════════════════════════
``dubbing._synth_all_words`` — đúng cửa lượt THAY GIỌNG đi (cửa có mốc từng
chữ), tự rẽ sang Piper / VieNeu / OmniVoice / Chatterbox / ElevenLabs theo
tiền tố mã. **Không dựng đường riêng**: đo đường không ai đi là đo cái không
tồn tại.

═══════════════════════════════════════════════════════════════════════════
BỐN NHÓM ARM — THIẾU NHÓM NÀO THÌ SỐ VÔ NGHĨA
═══════════════════════════════════════════════════════════════════════════
* **TRẦN**  giọng bản ngữ đọc tiếng của CHÍNH NÓ. Máy nghe cũng sai, nên
  không có TRẦN thì không biết "12% sai" là tốt hay tệ. Đây là mốc để so,
  KHÔNG phải số 0. Mỗi tiếng lấy **2 giọng** để TRẦN là một DẢI chứ không
  phải một điểm.
* **SÀN**   giọng MỘT-TIẾNG bị ép đọc tiếng KHÁC. Đây là hình dạng của một
  ca HỎNG THẬT. Không có SÀN thì không chứng minh được ngưỡng **tách được**
  hai nhóm — mà ngưỡng không tách được hai nhóm thì chỉ là một con số tròn
  nghĩ ra.
* **ĐÍCH**  mọi giọng ``*Multilingual*`` × cả 5 tiếng.
* **NGOÀI** VieNeu · Piper · OmniVoice · Chatterbox × cả 5 tiếng.

═══════════════════════════════════════════════════════════════════════════
BẪY: MÁY NGHE CHỮA HỘ MÁY ĐỌC -> ĐO **CẢ HAI** CỘT
═══════════════════════════════════════════════════════════════════════════
Groq whisper-large-v3 là MỘT MÔ HÌNH NGÔN NGỮ: nghe *"nét phờ lích"* trong
câu *"đứng đầu bảng xếp hạng ___"* nó vẫn viết ra ``Netflix``. ``_do_doc_roi``
đã đo được chênh thật: **trong câu 5% vs đọc rời 24%**. Nên mỗi arm đo:

* **TRONG CÂU** — có ngữ cảnh, máy nghe chữa hộ được;
* **ĐỌC RỜI**  — token một mình, không còn gì cho mô hình ngôn ngữ bám vào.

**Kết luận "đọc được" dựa vào cột ĐỌC RỜI.** Token đọc rời cố ý lấy loại
``ban_dia`` (tên riêng BẢN ĐỊA): đó là chỗ một giọng "biết đọc tiếng này"
khác hẳn một giọng "đang đoán theo mặt chữ".

═══════════════════════════════════════════════════════════════════════════
THƯỚC — VÀ VÌ SAO KHÔNG DÙNG LẠI THƯỚC CŨ
═══════════════════════════════════════════════════════════════════════════
``_thuoc_da_ngu`` (xem docstring file đó). ``_do_vieneu_en.wer`` mà lượt
trước định dùng trả **0,0% sai cho mọi chữ Hàn/Nhật/Trung kể cả khi chép ra
một câu hoàn toàn khác** — dùng nó thì mọi giọng đều "đọc được" cả 3 tiếng
CJK. ``tu_kiem()`` chạy TRƯỚC mọi lượt đo và DỪNG nếu thước không kêu.

**CẤM SO CHÉO TIẾNG**: vi/en chấm theo TỪ, ko/ja/zh chấm theo KÝ TỰ. Mọi kết
luận so với TRẦN của CHÍNH tiếng đó.

═══════════════════════════════════════════════════════════════════════════
KHÔNG TIỀN ĐỊNH -> CHẠY NHIỀU LƯỢT, BÁO DẢI
═══════════════════════════════════════════════════════════════════════════
OmniVoice từng ra **41,8%** và **99,4%** trên CÙNG một hàm; VieNeu đo được
trải 0,36 nửa cung giữa hai lượt cùng giọng cùng câu. edge-tts tiền định
(nói thẳng ra, không giả vờ đo nhiều lượt); nhóm NGOÀI chạy ``BQ_5T_VONG``
lượt và bảng in **DẢI**.

Chạy:  .venv\\Scripts\\python -u _do_5_tieng.py
Env:   BQ_5T_NHOM=tran,san,dich,ngoai   BQ_5T_VONG=2   BQ_5T_LAI=1
       BQ_5T_ARM=<tên arm,...>          BQ_5T_NN=vi,en
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import statistics as st
import sys
import time
from pathlib import Path

for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                          # noqa: BLE001
        pass

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
os.environ.setdefault("BQ_FFMPEG_SLOTS", "1")

from _bo_cau_thu_doc import CORPUS, NHAN_NN                    # noqa: E402
from _thuoc_da_ngu import co_trong, tu_kiem, ty_le_sai         # noqa: E402

HOP = REPO / "bq_do_5_tieng"
NGHE = REPO / "_NGHE_THU_ANH_HUNG" / "da_ngon_ngu"
CACHE = HOP / "cache.json"

#: Năm tiếng anh Hùng cần phủ.
NN5 = ("vi", "en", "ko", "ja", "zh")

#: Câu ĐỌC CẢ CÂU: `cau_thuong` (câu bản ngữ TRƠN) trả lời đúng câu hỏi
#: *"giọng này có đọc nổi tiếng này không"*. `ban_dia` là phần khó nhất của
#: chính tiếng đó và cũng là nguồn token "trong câu".
SO_CAU_THUONG = 3
SO_CAU_BAN_DIA = 3
SO_TOKEN_ROI = 4


def cau_thuong(nn: str) -> list[tuple[str, str, list[str]]]:
    return [x for x in CORPUS[nn] if x[0] == "cau_thuong"][:SO_CAU_THUONG]


def cau_ban_dia(nn: str) -> list[tuple[str, str, list[str]]]:
    return [x for x in CORPUS[nn] if x[0] == "ban_dia"][:SO_CAU_BAN_DIA]


def token_roi(nn: str) -> list[str]:
    ra, da = [], set()
    for loai, _c, toks in CORPUS[nn]:
        if loai != "ban_dia":
            continue
        for t in toks:
            if t not in da:
                da.add(t)
                ra.append(t)
    return ra[:SO_TOKEN_ROI]


# ---------------------------------------------------------------------------
# ARM
# ---------------------------------------------------------------------------
#: Giọng bản ngữ làm TRẦN — 2 giọng/tiếng để trần là một DẢI.
TRAN_GIONG: dict[str, tuple[str, ...]] = {
    "vi": ("vi-VN-HoaiMyNeural", "vi-VN-NamMinhNeural"),
    "en": ("en-US-AndrewNeural", "en-US-AriaNeural"),
    "ko": ("ko-KR-SunHiNeural", "ko-KR-InJoonNeural"),
    "ja": ("ja-JP-NanamiNeural", "ja-JP-KeitaNeural"),
    "zh": ("zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural"),
}

#: SÀN — giọng MỘT-TIẾNG bị ép đọc tiếng KHÁC. Lấy đúng 2 giọng đã làm TRẦN
#: của vi và en để cùng một giọng vừa cho ra TRẦN vừa cho ra SÀN — nhờ vậy
#: chênh lệch giữa hai con số KHÔNG thể đổ cho "giọng này vốn kém".
SAN_GIONG = ("vi-VN-HoaiMyNeural", "en-US-AndrewNeural")


def _da_ngu() -> list[str]:
    """MỌI giọng edge-tts mang nhãn `Multilingual`. Lấy từ DANH MỤC THẬT
    (`dubbing._fetch_all_voices`) chứ không từ `nhan_nha.BANG` — bảng đó chỉ
    có giọng ĐÃ ĐO nhấn nhá, lấy nó là tự giới hạn vào tập con mà không ai
    biết."""
    try:
        from app.core import dubbing
        ds = [v["ShortName"] for v in dubbing._fetch_all_voices()
              if "multilingual" in str(v.get("ShortName", "")).lower()]
        if ds:
            return sorted(set(ds))
    except Exception as e:                                     # noqa: BLE001
        print(f"  (không lấy được danh mục edge-tts: {e}; lùi về nhan_nha)")
    from app.core import nhan_nha
    return sorted(m for m in nhan_nha.BANG if "multilingual" in m.lower())


def _ma_ov() -> str:
    """Một mã giọng OmniVoice có thật ("" = không có).

    **LỖI CỦA CHÍNH SCRIPT, ĐÃ SỬA — GHI LẠI VÌ NÓ IM LẶNG:**
    `giong_ngoai.danh_sach_giong()` trả `(MÃ, nhãn)` chứ không phải
    `(nhãn, mã)`. Bản đầu (chép từ `_do_song_ngu.py` của lượt trước) unpack
    ngược nên `str(ma).startswith("ov:")` luôn False -> hàm trả `""` ->
    **cả nhóm OmniVoice biến mất khỏi bảng, không một dòng báo**. Đọc bảng
    ra thì tưởng "máy chưa cài OmniVoice". Nay kiểm CẢ HAI vị trí.
    """
    try:
        from app.core import giong_ngoai as gn
        for cap in (gn.danh_sach_giong() or []):
            for x in cap:
                if str(x or "").startswith("ov:"):
                    return str(x)
    except Exception:                                          # noqa: BLE001
        pass
    return ""


def _mau_cb() -> str:
    """File mẫu cho Chatterbox ("" = không có). Chatterbox là giọng NHÂN
    BẢN: mã của nó là ``cb:<tiếng>|<đường dẫn mẫu>``, không có mã dựng sẵn."""
    for p in sorted((REPO / "_do_chatter" / "mau").glob("*.wav")):
        if p.stat().st_size > 20000:
            return str(p)
    return ""


def _ma_cb(nn: str, mau: str) -> tuple[str, str]:
    """(mã Chatterbox cho tiếng `nn`, ghi chú).

    **CHATTERBOX KHÔNG CÓ TIẾNG VIỆT** — `giong_chatter.TIENG` có 23 tiếng
    và `vi` KHÔNG nằm trong đó. Đây chính là gốc của ca *"Một cơn bão chưa
    từng có"* -> *"Mokonbel, Chutanko, Tronglaichsatanglaich"*: chữ là tiếng
    Việt nhưng `language_id` buộc phải là một tiếng KHÁC, nên model đọc mặt
    chữ Việt bằng luật phát âm của tiếng đó. `generate()` vẫn ra tiếng, vẫn
    mã thoát 0.

    Vậy arm tiếng Việt của Chatterbox phải đo ĐÚNG cảnh người dùng gặp: chọn
    Chatterbox cho một kênh tiếng Việt thì thứ họ nhận được là mã `en`.
    """
    from app.core import giong_chatter as gc
    if nn in gc.TIENG:
        return gc.ma_nhan_ban(mau, nn), ""
    return gc.ma_nhan_ban(mau, "en"), f"KHÔNG có tiếng {nn} -> ép dùng 'en'"


def arm_tran() -> list[tuple[str, str, str, bool]]:
    ra = []
    for nn in NN5:
        for g in TRAN_GIONG[nn]:
            ra.append((f"TRAN_{nn}_{_gon(g)}", g, nn, True))
    return ra


def arm_san() -> list[tuple[str, str, str, bool]]:
    ra = []
    for g in SAN_GIONG:
        me = g.split("-")[0]
        for nn in NN5:
            if nn == me:
                continue
            ra.append((f"SAN_{_gon(g)}_x_{nn}", g, nn, True))
    return ra


def arm_dich() -> list[tuple[str, str, str, bool]]:
    ra = []
    for ma in _da_ngu():
        for nn in NN5:
            ra.append((f"ML_{_gon(ma)}_x_{nn}", ma, nn, True))
    return ra


def arm_ngoai() -> list[tuple[str, str, str, bool]]:
    """Giọng KHÔNG phải edge-tts. **KHÔNG TIỀN ĐỊNH** -> chạy nhiều vòng.

    Chỉ nhận giọng máy này CÀI RỒI: giọng chưa tải mà đưa vào thì cửa chung
    **lùi êm về edge-tts** và bảng sẽ ghi số của edge-tts dưới tên giọng
    khác — đúng loại "phép đo phát chứng nhận cho thứ không tồn tại". Cột
    `nguon_that` canh lại chuyện đó một lần nữa.
    """
    ra: list[tuple[str, str, str, bool]] = []

    def them(ma: str, ten: str) -> None:
        for nn in NN5:
            ra.append((f"{ten}_x_{nn}", ma, nn, False))

    try:
        from app.core import giong_vieneu as gv
        if gv.co_vieneu():
            them("vn:Ngọc Huyền", "VN_NgocHuyen")
            them("vn:Adam", "VN_Adam")
    except Exception:                                          # noqa: BLE001
        pass
    try:
        # MÃ PIPER PHẢI LẤY TỪ `piper_tts.TEN_MODEL`, ĐỪNG GÕ TAY.
        # `piper:vais1000` (tên gọn trong tài liệu) KHÔNG phải mã thật — mã
        # thật là `piper:vi_VN-vais1000-medium`. Gõ nhầm thì cửa chung không
        # tìm ra model rồi **lùi êm về edge-tts**, và bảng sẽ ghi số của
        # edge-tts dưới tên Piper. Cùng bệnh `nhan_nha.BANG` đã ghi đúng khoá
        # dài mà `_do_nhan_nha_vn` tra bằng khoá ngắn nên mất dòng mốc.
        from app.core import piper_tts as pt
        if pt.co_piper():
            them(pt.TIEN_TO + pt.TEN_MODEL, "PIPER_vais1000")
    except Exception:                                          # noqa: BLE001
        pass
    try:
        from app.core import giong_ngoai as gn
        if gn.co_omnivoice():
            ma = _ma_ov()
            if ma:
                them(ma, f"OV_{_gon(ma)}")
    except Exception:                                          # noqa: BLE001
        pass
    try:
        from app.core import giong_chatter as gc
        mau = _mau_cb()
        if gc.co_chatter() and mau:
            for nn in NN5:
                ma, ghi = _ma_cb(nn, mau)
                if ma:
                    ra.append((f"CB_nhanban_x_{nn}", ma, nn, False))
                    if ghi:
                        print(f"  CB tiếng {nn}: {ghi}")
    except Exception as e:                                     # noqa: BLE001
        print(f"  (Chatterbox: {type(e).__name__}: {e})")
    return ra


def _gon(ma: str) -> str:
    """Mã giọng -> tên arm ngắn, an toàn cho tên thư mục."""
    s = ma.split("|")[0]
    s = s.replace("Neural", "").replace("Multilingual", "ML")
    return re.sub(r"[^0-9A-Za-z_]+", "_", s).strip("_")


NHOM_ARM = {"tran": arm_tran, "san": arm_san,
            "dich": arm_dich, "ngoai": arm_ngoai}


# ---------------------------------------------------------------------------
# đọc + chép
# ---------------------------------------------------------------------------
#: Nghỉ giữa hai arm. edge-tts là dịch vụ MIỄN PHÍ của Microsoft và nó CHẶN
#: TỐC ĐỘ khi bị gọi liên tục — đo được ở lượt đầu: file `.mp3` ra **0 byte**
#: và mỗi câu mất tới 2 phút vì `_synth_all_words` thử lại 4 lần với backoff.
#: Nghỉ ngắn giữa các arm rẻ hơn hẳn việc đo lại cả bảng.
NGHI_GIUA_ARM = float(os.environ.get("BQ_5T_NGHI", "1.5"))

#: Số byte tối thiểu để coi là "có tiếng". `Path.exists()` KHÔNG đủ: vòng thử
#: lại của `_synth_all_words` mở file bằng `open(p,"wb")` nên lần thử hỏng để
#: lại một file **0 byte vẫn tồn tại**. Kiểm bằng `exists()` là đưa file rỗng
#: cho máy nghe rồi đếm kết quả rỗng đó thành "giọng đọc sai".
BYTE_TOI_THIEU = 1000


def _co_tieng(p: Path) -> bool:
    try:
        return p.exists() and p.stat().st_size >= BYTE_TOI_THIEU
    except OSError:
        return False


def doc_loat(texts: list[str], voice: str, thu: Path, tt: str,
             thu_lai: int = 1) -> tuple[list[bool], list[Path]]:
    """CỬA THẬT `dubbing._synth_all_words` (cửa có mốc từng chữ).

    Trả `(ok, paths)` với `ok[i]` = câu #i RA FILE CÓ TIẾNG THẬT.

    **`ok` của cửa chung KHÔNG đủ tin để kết luận** nên còn kiểm cỡ file, và
    còn ĐỌC LẠI riêng những câu hỏng (`thu_lai` lượt). Lý do: một câu hỏng vì
    edge-tts chặn tốc độ mà bị đếm thành "giọng này không đọc được tiếng đó"
    là **kết luận sai về một sản phẩm**, không phải một điểm nhiễu.
    """
    from app.core import dubbing
    thu.mkdir(parents=True, exist_ok=True)
    paths = [thu / f"{tt}{i:03d}.mp3" for i in range(len(texts))]
    ok, _w = asyncio.run(dubbing._synth_all_words(
        texts, voice, [str(p) for p in paths], el_lui=False))
    ok = [bool(o) and _co_tieng(p) for o, p in zip(ok, paths)]
    for _ in range(max(0, thu_lai)):
        con = [i for i, o in enumerate(ok) if not o]
        if not con:
            break
        time.sleep(3.0)
        ok2, _w2 = asyncio.run(dubbing._synth_all_words(
            [texts[i] for i in con], voice, [str(paths[i]) for i in con],
            el_lui=False))
        for j, i in enumerate(con):
            ok[i] = bool(ok2[j]) and _co_tieng(paths[i])
    return ok, paths


def chep(mp3: Path, lang: str | None) -> tuple[str, str]:
    from app.core import transcribe as TR
    try:
        r = TR.transcribe(str(mp3), language=lang)
        return str(r.get("text") or ""), str(r.get("language") or "")
    except Exception as e:                                     # noqa: BLE001
        return f"[lỗi chép: {type(e).__name__}: {str(e)[:60]}]", ""


def nguon_that(voice: str) -> str:
    """Giọng này THẬT SỰ do ai đọc (không phải cái user chọn).

    Cửa chung LÙI ÊM về edge-tts khi Piper/VieNeu/OmniVoice/Chatterbox chưa
    tải. Ghi lại nguồn THẬT để bảng không bao giờ khoe một giọng nó không hề
    dùng — đúng luật `doc_thu` đã chốt ở cổng 65.
    """
    from app.core import giong_bang
    ng = giong_bang.nguon(voice)
    if ng == giong_bang.EDGE:
        return "edge-tts"
    try:
        if ng == giong_bang.PIPER:
            from app.core import piper_tts as pt
            return "Piper" if pt.co_piper() else "edge-tts (LÙI)"
        if ng == giong_bang.VIENEU:
            from app.core import giong_vieneu as gv
            return "VieNeu" if gv.co_vieneu() else "edge-tts (LÙI)"
        if ng == giong_bang.OMNIVOICE:
            from app.core import giong_ngoai as gn
            return "OmniVoice" if gn.co_omnivoice() else "edge-tts (LÙI)"
        if ng == giong_bang.CHATTER:
            from app.core import giong_chatter as gc
            return "Chatterbox" if gc.co_chatter() else "edge-tts (LÙI)"
    except Exception:                                          # noqa: BLE001
        return "?"
    return giong_bang.TEN_NGUON.get(ng, ng)


# ---------------------------------------------------------------------------
# một arm - một lượt
# ---------------------------------------------------------------------------
def chay_arm(ten: str, voice: str, nn: str, vong: int, cache: dict,
             lam_lai: bool) -> dict:
    khoa = f"{ten}|{voice}|{nn}|v{vong}"
    if cache.get(khoa) and not lam_lai:
        return cache[khoa]

    ct = cau_thuong(nn)
    cb = cau_ban_dia(nn)
    tk = token_roi(nn)
    thu = HOP / f"{ten}_v{vong}"
    t0 = time.time()
    ok_c, p_c = doc_loat([c for _l, c, _t in ct], voice, thu, "s")
    ok_b, p_b = doc_loat([c for _l, c, _t in cb], voice, thu, "b")
    ok_t, p_t = doc_loat(tk, voice, thu, "t")
    t_doc = time.time() - t0

    hang_cau, hang_tc, hang_tr = [], [], []
    for i, (_l, c, _t) in enumerate(ct):
        if not ok_c[i]:
            hang_cau.append({"cau": c, "chep": "", "doc_duoc": False,
                             "nn_tu_nhan": ""})
            continue
        txt, _ = chep(p_c[i], nn)
        # NHÃN NGÔN NGỮ: thước PHỤ, ĐỘC LẬP với việc chấm chữ. Hỏi bằng
        # `language=None` để máy nghe TỰ đoán — nó trả lời câu "tiếng phát ra
        # nghe có giống tiếng này không", khác hẳn câu "chữ có đúng không".
        hang_cau.append({"cau": c, "chep": txt, "doc_duoc": True,
                         "nn_tu_nhan": chep(p_c[i], None)[1]})
    for i, (_l, c, toks) in enumerate(cb):
        txt = chep(p_b[i], nn)[0] if ok_b[i] else ""
        for t in toks:
            hang_tc.append({"token": t, "chep": txt, "doc_duoc": ok_b[i]})
    for i, t in enumerate(tk):
        hang_tr.append({"token": t, "doc_duoc": ok_t[i],
                        "chep": chep(p_t[i], nn)[0] if ok_t[i] else ""})

    kq = {"arm": ten, "voice": voice, "nn": nn, "vong": vong,
          "nguon_that": nguon_that(voice), "giay": round(t_doc, 1),
          "cau": hang_cau, "tc": hang_tc, "tr": hang_tr}
    cache[khoa] = kq
    HOP.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return kq


def cham(kq: dict) -> dict:
    """Chấm một arm.

    **HAI LOẠI HỎNG PHẢI ĐẾM RIÊNG — đây là chỗ bản đầu sai và nó sai theo
    kiểu ra kết luận về sản phẩm:**

    * ``hong``  = máy đọc KHÔNG ra được file có tiếng (mạng chập chờn,
      edge-tts chặn tốc độ). Lượt đo đầu tiên gặp thật: `.mp3` ra **0 byte**
      và mỗi câu mất tới 2 phút vì vòng thử lại backoff.
    * ``sai``   = ra tiếng ĐÀNG HOÀNG nhưng chép ngược ra SAI CHỮ.

    Bản đầu gộp cả hai vào một cột -> một arm bị Microsoft chặn tốc độ sẽ
    hiện ra là *"giọng này KHÔNG đọc được tiếng Hàn"*. Nay mẫu số **chỉ gồm
    câu/token ĐỌC ĐƯỢC**, và ``hong`` được in ra để người đọc tự thấy arm nào
    ít mẫu quá thì đừng tin.
    """
    nn = kq["nn"]
    sai, bo, hong_cau = [], 0, 0
    for h in kq["cau"]:
        if not h["doc_duoc"]:
            hong_cau += 1
            continue
        r, n = ty_le_sai(h["cau"], h["chep"], nn)
        if n == 0:                    # câu không có gì để chấm -> BỎ HẲN
            bo += 1                   # (đừng cộng vào như một mẫu "0% sai")
            continue
        sai.append(min(r, 1.5))

    def _dem(hang: list[dict]) -> tuple[int, int, int]:
        hong = sum(1 for h in hang if not h["doc_duoc"])
        duoc = [h for h in hang if h["doc_duoc"]]
        s = sum(1 for h in duoc if not co_trong(h["token"], h["chep"], nn))
        return s, len(duoc), hong

    tc_sai, tc_n, tc_hong = _dem(kq["tc"])
    tr_sai, tr_n, tr_hong = _dem(kq["tr"])
    nhan = [h["nn_tu_nhan"] for h in kq["cau"] if h.get("nn_tu_nhan")]
    dung = _NHAN_DUNG[nn]
    return {
        "arm": kq["arm"], "voice": kq["voice"], "nn": nn, "vong": kq["vong"],
        "nguon_that": kq.get("nguon_that", "?"),
        # NaN (không phải 100) khi KHÔNG có mẫu nào đọc được: 100 nghĩa là
        # "đo được và sai hết", NaN nghĩa là "chưa đo được". Trộn hai cái đó
        # là đúng bệnh file này đang đi chữa.
        "sai_cau": 100 * st.mean(sai) if sai else float("nan"),
        "n_cau": len(sai), "bo_cau": bo, "hong_cau": hong_cau,
        "tc_sai": tc_sai, "tc_n": tc_n, "tc_hong": tc_hong,
        "tr_sai": tr_sai, "tr_n": tr_n, "tr_hong": tr_hong,
        "doc_duoc": sum(1 for h in kq["cau"] if h["doc_duoc"]),
        "nn_dung": sum(1 for x in nhan if x.lower() in dung), "nn_n": len(nhan),
        "nn_khac": sorted({x for x in nhan if x.lower() not in dung}),
    }


#: Nhãn ngôn ngữ máy nghe có thể trả về. Groq trả **CHỮ** (`Vietnamese`) trên
#: video thật của anh Hùng chứ không phải mã ISO — thiếu dạng nào là cột nhãn
#: báo sai mà không một dòng cảnh báo (bài học `chuan_ngon_ngu`, cổng 52).
_NHAN_DUNG = {
    "vi": {"vi", "vietnamese"},
    "en": {"en", "english"},
    "ko": {"ko", "korean"},
    "ja": {"ja", "japanese"},
    "zh": {"zh", "chinese", "zh-cn", "mandarin"},
}


def dai(xs: list[float], d: int = 1) -> str:
    if not xs:
        return "-"
    if len(xs) == 1 or min(xs) == max(xs):
        return f"{xs[0]:.{d}f}"
    return f"{min(xs):.{d}f}-{max(xs):.{d}f}"


# ---------------------------------------------------------------------------
def main() -> int:
    HOP.mkdir(parents=True, exist_ok=True)
    cache: dict = {}
    if CACHE.exists():
        try:
            cache = json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:                                      # noqa: BLE001
            cache = {}
    lam_lai = os.environ.get("BQ_5T_LAI") == "1"
    so_vong = max(1, int(os.environ.get("BQ_5T_VONG", "2")))
    nhom = [x.strip() for x in
            (os.environ.get("BQ_5T_NHOM") or "tran,san,dich,ngoai").split(",")
            if x.strip()]
    chi = {x.strip() for x in (os.environ.get("BQ_5T_ARM") or "").split(",")
           if x.strip()}
    chi_nn = {x.strip() for x in (os.environ.get("BQ_5T_NN") or "").split(",")
              if x.strip()}

    print("=" * 78)
    print("GIỌNG NÀO ĐỌC ĐƯỢC MẤY TRONG NĂM TIẾNG (Việt · Anh · Hàn · Nhật · "
          "Trung)")
    print("cửa thật `dubbing._synth_all_words` · thước: Groq chép ngược chính "
          "file vừa đọc")
    print("=" * 78)
    if not tu_kiem():
        print("THƯỚC KHÔNG KÊU -> DỪNG, không in bảng số.")
        return 2

    arms: list[tuple[str, str, str, bool]] = []
    for n in nhom:
        arms += NHOM_ARM[n]() if n in NHOM_ARM else []
    if chi:
        arms = [a for a in arms if a[0] in chi]
    if chi_nn:
        arms = [a for a in arms if a[2] in chi_nn]

    n_ml = len({a[1] for a in arms if "multilingual" in a[1].lower()})
    print(f"\n{len(arms)} arm · {so_vong} vòng (arm tiền định chỉ chạy vòng 1)"
          f" · {n_ml} giọng Multilingual")
    for nn in NN5:
        print(f"  bộ câu {NHAN_NN[nn]:6s}: {len(cau_thuong(nn))} câu thường + "
              f"{len(cau_ban_dia(nn))} câu bản địa + {len(token_roi(nn))} "
              f"token đọc rời")

    tat: dict[str, list[dict]] = {}
    t0 = time.time()
    for v in range(1, so_vong + 1):
        k = (v - 1) % max(1, len(arms))
        thu_tu = arms[k:] + arms[:k]              # ĐAN XEN + XOAY mỗi vòng
        print(f"\n--- VÒNG {v}/{so_vong} ---", flush=True)
        for i, (ten, voice, nn, tien_dinh) in enumerate(thu_tu, 1):
            if tien_dinh and v > 1:
                continue
            try:
                kq = chay_arm(ten, voice, nn, v, cache, lam_lai)
            except Exception as e:                             # noqa: BLE001
                print(f"  [{i:3d}/{len(thu_tu)}] {ten:34s} LỖI "
                      f"{type(e).__name__}: {str(e)[:70]}", flush=True)
                continue
            c = cham(kq)
            tat.setdefault(ten, []).append(c)
            hong = c["hong_cau"] + c["tc_hong"] + c["tr_hong"]
            print(f"  [{i:3d}/{len(thu_tu)}] {ten:34s} "
                  f"sai câu {c['sai_cau']:5.1f}% · trong câu "
                  f"{c['tc_sai']}/{c['tc_n']} · đọc rời {c['tr_sai']}/"
                  f"{c['tr_n']} · nhãn {c['nn_dung']}/{c['nn_n']}"
                  + (f" · HỎNG {hong}" if hong else "")
                  + f" · {kq['giay']:.0f}s", flush=True)
            time.sleep(NGHI_GIUA_ARM)

    if not tat:
        print("\nKHÔNG arm nào chạy được -> không có bảng.")
        return 1
    (HOP / "ket_qua.json").write_text(
        json.dumps(tat, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nXONG {len(tat)} arm · {time.time()-t0:.0f} giây")
    print(f"SỐ LIỆU: {HOP / 'ket_qua.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
