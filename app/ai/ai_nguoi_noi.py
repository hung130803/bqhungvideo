"""AI NHẬN BIẾT NGƯỜI KỂ CHUYỆN — chỗ nào LỒNG TIẾNG, chỗ nào GIỮ NGUYÊN GỐC.

Anh Hùng, 18/08/2026, nguyên văn: *"nhận biết chỗ video gốc người thật nói thì
GIỮ NGUYÊN, không lồng tiếng; chỗ người kể chuyện nói thì mới lồng tiếng — chứ
đoạn người thật nó dịch không đâu vào đâu, mất hay"*.

Trước module này, đường thay giọng lồng tiếng **MỌI đoạn có lời**. Nguồn là
video "giải thích phim": phần lớn là người kể thuyết minh (đáng lồng), nhưng
xen vào là trích đoạn phim còn nguyên tiếng gốc — diễn viên nói trong khung,
tiếng hò, tiếng hát. Lồng tiếng lên mấy chỗ đó ra lời vô nghĩa và mất chất
phim.

────────────────────────────────────────────────────────────────────────────
HAI LOẠI SAI KHÔNG NGANG NHAU — kiến trúc dựng theo đúng thứ tự đó
────────────────────────────────────────────────────────────────────────────
  · **LỒNG OAN** lên người thật  -> mất chất phim (anh Hùng phàn nàn cái này)
  · **BỎ SÓT** người kể          -> mất nội dung video

Thà bỏ sót hơn lồng oan, NHƯNG chỉ ở mức RÌA. Ở mức HỆ THỐNG thì ngược lại:
`quyet_dinh` mặc định **LỒNG TIẾNG** và chỉ đổi sang GIỮ GỐC khi có **BẰNG
CHỨNG DƯƠNG**. Lý do là số học: một mẻ chấm hỏng có thể phủ 20 câu liền, mà
giữ gốc 20 câu liền là **rút ruột video** — tệ hơn hẳn lồng oan một câu. Vì
vậy `khong_tin` (không chấm nổi) **KHÔNG** được quyền giữ gốc.

────────────────────────────────────────────────────────────────────────────
BÀI HỌC ĐẮT NHẤT — LLM ĐẢO NHÃN CẢ MẺ, VÀ NÓ TỰ TIN NHẤT ĐÚNG LÚC SAI NHẤT
────────────────────────────────────────────────────────────────────────────
Lượt đo đầu (`_do_nguoi_noi_llm.py`, 577 câu / 4 video THẬT của anh Hùng,
Groq thật) chấm ra **67/577 = 11,6%** câu "tiếng gốc". Soi lại thì nhãn dính
**ĐÚNG BIÊN MẺ**: v1 và v2 đều là câu **100-124** (mẻ thứ 5), v4 là **50-64**
(mẻ cuối). Cả mẻ 20-25 câu ra "goc" với `tin` model tự khai **0,95-1,00**,
trong khi đó là những câu kể chuyện rõ nhất bộ. Tức:

  **`tin` do model tự khai LÀ SỐ VÔ DỤNG để bắt lỗi này.**

Chữa bằng 3 lớp, và phải đủ cả 3 (`cham_llm`):
  1. **MỒI ĐỐI CHỨNG** trộn vào từng mẻ — 4 câu tôi biết trước đáp án (2 kể ·
     2 gốc), đánh số LẪN trong dãy 1..N nên model không phân biệt được.
  2. Mẻ chấm SAI mồi -> **BỎ CẢ MẺ**, gọi lại (tối đa `LAN_GOI_LAI`). Vẫn sai
     -> `khong_tin`, và `khong_tin` không được giữ gốc.
  3. **BỎ PHIẾU `SO_LUOT` lượt**, lấy đa số.

SỐ ĐO TRƯỚC/SAU trên cùng 577 câu, cùng model, cùng corpus:

  | | nhãn "goc" | trong đó SAI |
  |---|---|---|
  | không mồi, 1 lượt | 67 | **66** |
  | có mồi + 3 phiếu | 4 | **2** |

  Mồi bắt được **8/99 lượt gọi** phải bỏ (~8%). Mỗi lượt bỏ là ~20 câu được
  cứu. **Bỏ mồi đi là quay lại 11,6% lồng-oan-ngược.**

────────────────────────────────────────────────────────────────────────────
BA TÍN HIỆU — vai trò KHÁC NHAU, đừng gộp một rổ
────────────────────────────────────────────────────────────────────────────
(a) **LLM đọc bản chép lời** (`cham_llm`) — văn phong kể chuyện khác đối
    thoại. Đo được trên bộ đối chứng: bắt **2/2** đoạn tiếng gốc THUẦN, bỏ
    sót người kể **2/573 = 0,35%**. Đây là tín hiệu MẠNH NHẤT trong hai tín
    hiệu chấm được, đúng như đề bài dự đoán.

(b) **Đặc trưng giọng ECAPA-TDNN** (`cham_giong`) — người kể là MỘT giọng
    chiếm phần lớn thời lượng. Chạy ở **TIẾN TRÌNH RIÊNG**: `import torch`
    sau khi Qt nạp là **ACCESS VIOLATION** và `try/except` KHÔNG chặn được
    (khuôn ở `giong_ngoai.py`). **BẮT BUỘC `tu_kiem_giong()` TRƯỚC** — MFCC
    và cao độ đã đo là thước HỎNG (nhiễu tự nó 97,7 > khoảng cách thật 48,4),
    nên thước nào không tách nổi 2 giọng edge-tts thì mọi số sau vô nghĩa.

(c) **Phụ đề CHÁY SẴN của người kể** (`cham_phu_de`) — nguồn Douyin/reup đốt
    lời người kể vào khung, nên dải phụ đề TRỐNG = người kể không nói.
    **NÓI THẲNG MỘT GIỚI HẠN: tín hiệu này chính là thứ tôi đã dùng để DỰNG
    bộ đối chứng, nên KHÔNG được tính điểm cho nó trên cùng bộ đó** — làm vậy
    là tự chấm bài mình. Nó có mặt ở đây vì nó rẻ và đúng với nguồn anh Hùng
    đang làm, nhưng con số của nó phải đo trên bộ đối chứng KHÁC.

────────────────────────────────────────────────────────────────────────────
GIỮ GỐC LÀ GIỮ NGUYÊN — KHÔNG TÁCH, KHÔNG TRỘN LẠI
────────────────────────────────────────────────────────────────────────────
`khoang_giu_goc()` trả các khoảng thời gian ở **THANG NGUỒN**. Nơi gọi phải
để nguyên tiếng gốc ở đó: **không tách giọng, không trộn lại, không chuẩn hoá
độ to**. Mỗi lượt tách-rồi-trộn là một cơ hội mất tiếng (đã có tiền lệ
`asplit` làm độ dài đầu ra không tiền định), mà chỗ này thứ cần giữ chính là
tiếng đang có.

Module này KHÔNG tự sửa audio và KHÔNG gọi ffmpeg để trộn — nó chỉ QUYẾT ĐỊNH
và trả khoảng. Việc nối vào đường xuất là việc riêng, chưa làm.
"""
from __future__ import annotations

import json
import os
import random
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Sequence

# ==========================================================================
# HẰNG SỐ
# ==========================================================================

#: hai quyết định — dùng chuỗi chứ không bool để nhật ký đọc ra nghĩa
LONG_TIENG = "long_tieng"
GIU_GOC = "giu_goc"

#: số câu THẬT mỗi mẻ gửi LLM. 20 câu + 4 mồi -> prompt ~1,3k token, còn chỗ
#: cho câu trả lời trong ngân sách `llm.max_tokens_groq`.
ME_CAU = 20
#: số lượt bỏ phiếu cho mỗi mẻ
SO_LUOT = 3
#: mẻ chấm sai mồi thì gọi lại tối đa bấy nhiêu lần
LAN_GOI_LAI = 3

#: MỒI ĐỐI CHỨNG — đáp án do NGƯỜI đặt, model không được biết. Tiếng Trung vì
#: nguồn anh Hùng đang làm là tiếng Trung; `moi_theo_tieng` đổi theo corpus.
MOI_ZH = (
    ("这部电影上映首周就拿下了三亿票房", "ke"),
    ("男主回到家后发现桌上的东西被人动过", "ke"),
    ("别过来！你到底想干什么", "goc"),
    ("啊啊啊 救命啊 快跑", "goc"),
)
MOI_VI = (
    ("Bộ phim ra mắt tuần đầu đã thu về ba trăm tỉ đồng", "ke"),
    ("Nam chính về nhà thì phát hiện đồ trên bàn đã bị ai đó động vào", "ke"),
    ("Đừng lại đây! Anh định làm gì hả", "goc"),
    ("Á á á cứu tôi với chạy mau", "goc"),
)
MOI_EN = (
    ("The film made three hundred million in its opening week", "ke"),
    ("He came home and found that something on the desk had been moved", "ke"),
    ("Stay back! What the hell do you want from me", "goc"),
    ("Aaah help me somebody run", "goc"),
)

#: TRẦN BỎ SÓT — tỉ lệ câu bị gán GIỮ GỐC trên CẢ VIDEO không được vượt mức
#: này. Đo trên corpus thật: video "giải thích phim" có 0,0-1,5% đoạn tiếng
#: gốc. Vượt 15% gần như chắc chắn là bộ chấm hỏng (mẻ đảo nhãn đo được
#: 11,6%), và hậu quả là RÚT RUỘT video — nên vượt trần thì HUỶ HẾT, quay về
#: lồng tiếng toàn bộ, tức đúng hành vi hôm nay.
TRAN_GIU_GOC = 0.15

#: đoạn ngắn hơn mức này thì ECAPA không đủ mẫu để nói gì (đo: dưới 0,35 giây
#: embedding gần như là nhiễu)
GIAY_TOI_THIEU_GIONG = 0.35

#: giọng khớp TÂM dưới mức này thì coi là KHÁC người kể. Số mặc định để None
#: có chủ đích: nó PHẢI lấy từ `tu_kiem_giong()` của chính máy đang chạy, đặt
#: hằng số ở đây là mời người sau dùng số đo của máy khác.
NGUONG_GIONG_MAC_DINH: Optional[float] = None


# ==========================================================================
# KIỂU DỮ LIỆU
# ==========================================================================

@dataclass
class Doan:
    """Một câu trong bản chép lời. Thang giây theo VIDEO NGUỒN."""
    i: int
    start: float
    end: float
    text: str = ""

    @property
    def dai(self) -> float:
        return max(0.0, float(self.end) - float(self.start))


@dataclass
class KetQua:
    """Quyết định cho MỘT đoạn, kèm đủ dấu vết để nhật ký nói được vì sao."""
    i: int
    quyet: str = LONG_TIENG
    ly_do: str = ""
    #: từng tín hiệu: "goc" / "ke" / "khong_tin" / None (không chạy)
    llm: Optional[str] = None
    giong: Optional[float] = None
    phu_de: Optional[float] = None
    #: số tín hiệu ĐỘC LẬP nói "không phải người kể"
    so_dau: int = 0

    @property
    def giu(self) -> bool:
        return self.quyet == GIU_GOC


@dataclass
class TomTat:
    """Tóm tắt cả video — thứ đi vào nhật ký dây chuyền."""
    so_doan: int = 0
    so_giu: int = 0
    giay_giu: float = 0.0
    ty_le_giu: float = 0.0
    huy_vi_vuot_tran: bool = False
    canh_bao: list = field(default_factory=list)


# ==========================================================================
# TIỆN ÍCH THUẦN
# ==========================================================================

def doan_tu_cau(cau: Sequence[dict]) -> list[Doan]:
    """Đổi danh sách `{start,end,text}` (của `thay_giong.cau_tu_transcript`)
    sang `Doan`. Hàm THUẦN."""
    ra = []
    for i, c in enumerate(cau or []):
        try:
            a = float(c.get("start", 0) or 0)
            b = float(c.get("end", 0) or 0)
        except (TypeError, ValueError):
            continue
        ra.append(Doan(i=i, start=a, end=b, text=str(c.get("text") or "")))
    return ra


def cat_theo_tu(cau: Sequence[dict], words: Sequence[dict],
                le: float = 0.04) -> list[Doan]:
    """Thu mốc mỗi câu về đúng TỪ ĐẦU và TỪ CUỐI của nó. Hàm THUẦN.

    **VÌ SAO CẦN — đây là một trong hai chỗ bỏ sót ĐO ĐƯỢC của việc này:**
    whisper đặt `segments[0].start = 0.00` trong khi TỪ đầu tiên mới ở
    **3,58 giây** (video `v1_dutu` của anh Hùng). Tức câu số 0 nuốt trọn 3,5
    giây mở đầu vốn là nhạc/tiếng phim, rồi cả 5,52 giây bị lồng tiếng đè lên
    — mà xét theo NỘI DUNG thì câu đó ĐÚNG là lời người kể, nên không bộ phân
    loại nào bắt được. Đây là lỗi CẮT ĐOẠN, không phải lỗi phân loại.
    Cắt theo mốc từ đưa câu 0 về 3,58-5,48; phần 0-3,58 không còn câu nào phủ
    nên nó được để nguyên — đúng cái cần.

    **KHÔNG CHỮA ĐƯỢC MỌI CA, ghi thẳng:** ở `v2_nieu` whisper gán từ từ
    0,00 (nó nghe ra chữ trong cả đoạn nhạc mở đầu) nên cắt theo từ KHÔNG đổi
    gì; ca đó phải TÁCH câu làm hai, việc chưa làm.
    """
    ws = []
    for w in (words or []):
        try:
            ws.append((float(w.get("start", 0) or 0),
                       float(w.get("end", 0) or 0)))
        except (TypeError, ValueError):
            continue
    ws.sort()
    ra = doan_tu_cau(cau)
    if not ws:
        return ra
    for x in ra:
        trong = [(a, b) for a, b in ws
                 if a >= x.start - 0.01 and b <= x.end + 0.01]
        if not trong:
            continue
        a = max(x.start, trong[0][0] - le)
        b = min(x.end, trong[-1][1] + le)
        if b - a > 0.05:
            x.start, x.end = round(a, 3), round(b, 3)
    return ra


def _co_cjk(s: str) -> bool:
    """Có chữ Hán/kana không. KHÔNG tính hangul — tiếng Hàn CÓ dấu cách nên
    nó thuộc nhóm chữ latin về mặt tách từ (bài học cổng 54)."""
    for ch in s or "":
        o = ord(ch)
        if (0x3000 <= o <= 0x30FF or 0x3400 <= o <= 0x4DBF
                or 0x4E00 <= o <= 0x9FFF or 0xF900 <= o <= 0xFAFF
                or 0xFF01 <= o <= 0xFF9F):
            return True
    return False


def moi_theo_tieng(doan: Sequence[Doan]) -> tuple:
    """Chọn bộ MỒI cùng thứ tiếng với corpus.

    Mồi khác thứ tiếng với câu thật là tự tay dựng thêm một tín hiệu cho model
    dò ra mồi ("câu nào tiếng lạ thì là mồi"), lúc đó mồi mất tác dụng canh.
    """
    chu = "".join(d.text for d in doan[:60])
    if _co_cjk(chu):
        return MOI_ZH
    thap = chu.lower()
    if any(k in thap for k in ("ạ", "ộ", "ế", "ữ", "ơ", "ă", "đ")):
        return MOI_VI
    return MOI_EN


# ==========================================================================
# TÍN HIỆU (a) — LLM ĐỌC BẢN CHÉP LỜI
# ==========================================================================

HE_THONG_LLM = ("Bạn phân loại từng câu trong bản chép lời video "
                "'giải thích phim'. Chỉ trả JSON.")

MAU_LLM = """Video kiểu "giải thích phim": một NGƯỜI KỂ thuyết minh ngoài hình
tóm tắt cốt truyện, xen giữa là đoạn TRÍCH TỪ CHÍNH BỘ PHIM còn nguyên tiếng
gốc.

Phân loại MỖI câu:
- "ke"  = lời NGƯỜI KỂ. Kể ngôi thứ BA, gọi nhân vật bằng tên hoặc "nam chính
  / cô gái / người cha", tả diễn biến, tả bối cảnh, nêu doanh thu hoặc điểm
  đánh giá.
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


def _mot_luot_llm(goi_json: Callable, muc: list[tuple[int, str]]) -> dict:
    """Gọi LLM một lượt cho danh sách (số, chữ). Trả {số: {"ai","vi_sao"}}."""
    dong = "\n".join(f"{j}. {t}" for j, t in muc)
    data = goi_json(MAU_LLM.format(n=len(muc), cau=dong), HE_THONG_LLM)
    if isinstance(data, dict):
        for k in ("ket", "data", "cau", "items", "result"):
            if isinstance(data.get(k), list):
                data = data[k]
                break
        else:
            data = []
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


def _cham_me_llm(goi_json: Callable, doan: list[Doan], lo: list[int],
                 moi: tuple, rnd: random.Random,
                 ghi: Optional[Callable[[str], None]] = None):
    """Chấm MỘT mẻ: mồi trộn lẫn + bỏ mẻ nếu sai mồi + bỏ phiếu.

    Trả (nhãn theo chỉ số thật, số lượt qua mồi, số lần gọi).
    """
    phieu: dict[int, list[str]] = {i: [] for i in lo}
    qua = goi = 0
    for _ in range(SO_LUOT):
        kem = list(moi)
        rnd.shuffle(kem)
        tron = ([(("that", i), doan[i].text) for i in lo]
                + [(("moi", k), t) for k, (t, _) in enumerate(kem)])
        rnd.shuffle(tron)
        so: dict[int, tuple] = {}
        gui: list[tuple[int, str]] = []
        for j, (khoa, t) in enumerate(tron, start=1):
            so[j] = khoa
            gui.append((j, t))
        for _lan in range(LAN_GOI_LAI):
            goi += 1
            try:
                ra = _mot_luot_llm(goi_json, gui)
            except Exception as e:            # mạng/hạn mức/JSON — KHÔNG NÉM
                if ghi:
                    ghi(f"loi goi LLM: {type(e).__name__}: {str(e)[:120]}")
                continue
            sai = sum(1 for j, khoa in so.items()
                      if khoa[0] == "moi"
                      and (j not in ra or ra[j]["ai"] != kem[khoa[1]][1]))
            if sai:
                if ghi:
                    ghi(f"me {lo[0]}-{lo[-1]}: sai {sai}/{len(kem)} moi "
                        f"-> BO ME, goi lai")
                continue
            qua += 1
            for j, khoa in so.items():
                if khoa[0] == "that" and j in ra:
                    phieu[khoa[1]].append(ra[j]["ai"])
            break
    nhan = {}
    for i, ps in phieu.items():
        if not ps:
            nhan[i] = "khong_tin"
            continue
        ng = sum(1 for x in ps if x == "goc")
        nhan[i] = "goc" if ng * 2 > len(ps) else "ke"
    return nhan, qua, goi


def cham_llm(doan: Sequence[Doan], goi_json: Optional[Callable] = None,
             ghi: Optional[Callable[[str], None]] = None,
             seed: int = 20260818) -> dict[int, str]:
    """TÍN HIỆU (a). Trả {chỉ số đoạn: "ke" | "goc" | "khong_tin"}.

    `goi_json(prompt, system)` mặc định là `llm.complete_json` — tách ra tham
    số để cổng test chấm được hàm này mà không gọi mạng.

    KHÔNG BAO GIỜ NÉM: mọi lỗi thành "khong_tin", mà "khong_tin" thì không
    được quyền giữ gốc -> hỏng tín hiệu này là quay về đúng hành vi hôm nay.
    """
    ds = list(doan)
    if not ds:
        return {}
    if goi_json is None:
        try:
            from app.ai import llm as _llm
        except Exception:
            return {d.i: "khong_tin" for d in ds}
        goi_json = _llm.complete_json
    moi = moi_theo_tieng(ds)
    rnd = random.Random(seed)
    ra: dict[int, str] = {}
    tong_qua = tong_goi = 0
    for k in range(0, len(ds), ME_CAU):
        lo = [d.i for d in ds[k:k + ME_CAU]]
        theo_i = {d.i: d for d in ds}
        nhan, qua, goi = _cham_me_llm(
            goi_json, theo_i, lo, moi, rnd, ghi)
        ra.update(nhan)
        tong_qua += qua
        tong_goi += goi
    if ghi:
        ghi(f"LLM: {tong_goi} lan goi, {tong_qua} luot qua moi, "
            f"'goc' {sum(1 for v in ra.values() if v == 'goc')}/{len(ra)}")
    return ra


# ==========================================================================
# TÍN HIỆU (b) — ĐẶC TRƯNG GIỌNG ECAPA-TDNN (TIẾN TRÌNH RIÊNG)
# ==========================================================================

#: Script chạy ở TIẾN TRÌNH RIÊNG. Nhúng thành chuỗi chứ không `-m <module>`:
#: bản `.exe` không có cây mã nguồn (cùng khuôn `giong_ngoai._viet_runner`).
MA_GIONG = r'''
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
job = json.load(open(sys.argv[1], encoding="utf-8"))
for p in job.get("them_path") or []:
    sys.path.insert(0, p)
import numpy as np, torch, soundfile as sf
from speechbrain.inference.speaker import EncoderClassifier
try:
    from speechbrain.utils.fetching import LocalStrategy
    _ls = {"local_strategy": LocalStrategy.COPY}
except Exception:
    _ls = {}
dev = "cuda" if torch.cuda.is_available() else "cpu"
m = EncoderClassifier.from_hparams(source=job["nguon"], savedir=job["savedir"],
                                  run_opts={"device": dev}, **_ls)
def emb(p):
    x, sr = sf.read(p, dtype="float32")
    if x.ndim > 1:
        x = x.mean(axis=1)
    if sr != 16000 or x.shape[0] < 1600:
        return None
    with torch.no_grad():
        e = m.encode_batch(torch.from_numpy(x)[None].to(dev))
    v = e.squeeze().detach().cpu().numpy().astype(float)
    n = float(np.linalg.norm(v))
    return (v / n).tolist() if n > 0 else None
ra = {}
for k, p in job["files"].items():
    try:
        ra[k] = emb(p)
    except Exception as ex:
        ra[k] = None
        print(f"LOI {k}: {type(ex).__name__} {ex}", file=sys.stderr)
print("BQJSON\t" + json.dumps({"dev": dev, "torch": torch.__version__,
                               "emb": ra}))
'''

NGUON_ECAPA = "speechbrain/spkrec-ecapa-voxceleb"
_NO_WIN = 0x08000000 if os.name == "nt" else 0


def _thu_muc_lam() -> Path:
    """Chỗ đặt runner + model. Đọc `config.DATA_DIR` MỖI LẦN GỌI (bài học
    `tg_so.duong_so`: cất hằng số là bản đóng gói trỏ sai chỗ)."""
    try:
        from config import DATA_DIR
        return Path(DATA_DIR) / "_nguoi_noi"
    except Exception:
        return Path(__file__).resolve().parents[2] / "_nguoi_noi"


def _python_torch() -> list[Path]:
    """Ứng viên python CÓ torch, theo thứ tự ưu tiên. KHÔNG import torch để
    kiểm — import torch trong tiến trình đã nạp Qt là ACCESS VIOLATION."""
    goc = Path(__file__).resolve().parents[2]
    ds = [goc / "_giong_ngoai" / "venv" / "Scripts" / "python.exe",
          goc / ".venv" / "Scripts" / "python.exe"]
    return [p for p in ds if p.exists()]


def _duong_speechbrain() -> list[str]:
    """Thư mục cài rời của speechbrain (nếu có), cùng khuôn `_lib` của
    Demucs: cài vào chỗ RIÊNG, không đụng `.venv` đang chạy sản xuất."""
    goc = Path(__file__).resolve().parents[2]
    ds = [goc / "_kq_nn" / "sb", goc / "_lib_sb"]
    return [str(p) for p in ds if p.is_dir()]


def _chay_emb(files: dict[str, str], py: Optional[str] = None) -> dict:
    """Chạy runner ở tiến trình riêng, trả {"dev","torch","emb"}."""
    d = _thu_muc_lam()
    d.mkdir(parents=True, exist_ok=True)
    run = d / "_giong_runner.py"
    run.write_text(MA_GIONG, encoding="utf-8")
    job = d / "_giong_job.json"
    job.write_text(json.dumps({
        "files": files, "nguon": NGUON_ECAPA,
        "savedir": str(d / "ecapa_model"),
        "them_path": _duong_speechbrain()}, ensure_ascii=False),
        encoding="utf-8")
    if py is None:
        uv = _python_torch()
        if not uv:
            raise RuntimeError("khong tim thay python co torch")
        py = str(uv[0])
    p = subprocess.run([py, "-u", str(run), str(job)], capture_output=True,
                       text=True, encoding="utf-8", errors="replace",
                       creationflags=_NO_WIN, timeout=7200)
    for dong in (p.stdout or "").splitlines():
        if dong.startswith("BQJSON\t"):
            return json.loads(dong[7:])
    raise RuntimeError(f"runner giong that bai rc={p.returncode}: "
                       f"{(p.stderr or '')[-600:]}")


def tu_kiem_giong(sinh_wav: Callable[[str, Path], None],
                  py: Optional[str] = None) -> dict:
    """TỰ KIỂM BỘ DÒ — BẮT BUỘC chạy trước khi tin `cham_giong`.

    `sinh_wav(giong, duong)` phải ghi ra WAV **16 kHz mono** của giọng đó.
    Chạy chính thước ECAPA trên 2 giọng x 3 câu, nơi biết chắc giọng nào là
    giọng nào. Trả `{"tach": bool, "trong_min", "cheo_max", "nguong", ...}`.

    Vì sao bắt buộc: **MFCC và cao độ là thước HỎNG** để so giọng (đã đo:
    nhiễu tự nó 97,7 > khoảng cách thật 48,4). Không có mục này thì mọi con
    số của tín hiệu giọng chỉ là con dấu.
    """
    import numpy as np
    d = _thu_muc_lam() / "tukiem"
    d.mkdir(parents=True, exist_ok=True)
    CAU = ["Hôm nay trời rất đẹp, chúng ta cùng đi dạo một chút nhé.",
           "Cơn bão lớn nhất trong lịch sử đang tiến vào thành phố này.",
           "Anh ấy mở cửa ra và thấy một người lạ đang đứng ngoài sân."]
    GIONG = ["vi-VN-NamMinhNeural", "vi-VN-HoaiMyNeural"]
    files = {}
    for gi, v in enumerate(GIONG):
        for ci, c in enumerate(CAU):
            w = d / f"g{gi}_c{ci}.wav"
            if not w.exists() or w.stat().st_size < 4000:
                sinh_wav(v, w)
            files[f"g{gi}_c{ci}"] = str(w)
    kq = _chay_emb(files, py)
    E = {k: np.array(v) for k, v in (kq.get("emb") or {}).items() if v}
    trong, cheo = [], []
    ks = sorted(E)
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            s = float(E[ks[i]] @ E[ks[j]])
            (trong if ks[i][:2] == ks[j][:2] else cheo).append(s)
    if not trong or not cheo:
        return {"tach": False, "ly_do": f"chi do duoc {len(E)}/{len(files)}"}
    tmin, cmax = min(trong), max(cheo)
    return {"tach": bool(tmin > cmax), "trong_min": round(tmin, 4),
            "trong_max": round(max(trong), 4), "cheo_max": round(cmax, 4),
            "cheo_min": round(min(cheo), 4),
            "nguong": round((tmin + cmax) / 2, 4),
            "thiet_bi": kq.get("dev"), "torch": kq.get("torch"),
            "so_emb": len(E)}


def cat_doan_wav(wav16: str | Path, doan: Sequence[Doan], thu_muc: str | Path,
                 ffmpeg: Optional[str] = None) -> dict[int, str]:
    """Cắt từng đoạn ra WAV 16k mono. Trả {chỉ số: đường dẫn}.

    BẪY ĐÃ ĐO: `ffmpeg` trả mã 0 mà file 0 KiB (`-ss` vượt độ dài) -> phải
    kiểm KÍCH THƯỚC, đừng tin mã thoát.
    """
    ff = ffmpeg or str(Path(__file__).resolve().parents[2] / "bin"
                       / "ffmpeg.exe")
    d = Path(thu_muc)
    d.mkdir(parents=True, exist_ok=True)
    ra = {}
    for x in doan:
        if x.dai < GIAY_TOI_THIEU_GIONG:
            continue
        p = d / f"{x.i:05d}.wav"
        if not (p.exists() and p.stat().st_size > 4000):
            r = subprocess.run(
                [ff, "-y", "-v", "error", "-ss", f"{x.start:.3f}",
                 "-t", f"{x.dai:.3f}", "-i", str(wav16), "-vn",
                 "-ac", "1", "-ar", "16000", str(p)],
                capture_output=True, creationflags=_NO_WIN, timeout=300)
            if r.returncode != 0:
                continue
        if p.exists() and p.stat().st_size > 4000:
            ra[x.i] = str(p)
    return ra


def tam_nguoi_ke(M, w, vong: int = 5, bo: float = 0.15):
    """TÂM giọng chiếm phần lớn THỜI LƯỢNG. Hàm THUẦN (nhận numpy).

    Lặp: tính tâm có TRỌNG SỐ GIÂY -> bỏ `bo` phần xa tâm nhất -> tính lại.
    Trọng số phải là GIÂY chứ không phải số câu: người kể nói nhiều giây hơn,
    còn đếm câu thì một tràng đối thoại ngắn cũng nặng bằng.
    """
    import numpy as np
    giu = np.ones(M.shape[0], dtype=bool)
    tam = None
    for _ in range(max(1, vong)):
        t = (M[giu] * w[giu, None]).sum(axis=0)
        n = float(np.linalg.norm(t))
        if n <= 0:
            break
        tam = t / n
        s = M @ tam
        moc = float(np.quantile(s[giu], bo))
        moi_giu = s >= moc
        if moi_giu.sum() < 3:
            break
        giu = moi_giu
    return tam


def cham_giong(wav16: str | Path, doan: Sequence[Doan],
               thu_muc: Optional[str | Path] = None,
               py: Optional[str] = None,
               ghi: Optional[Callable[[str], None]] = None,
               ) -> dict[int, float]:
    """TÍN HIỆU (b). Trả {chỉ số: độ giống TÂM người kể} (-1..1, càng cao
    càng chắc là người kể). Đoạn không đo được thì KHÔNG có khoá.

    KHÔNG NÉM: thiếu torch/speechbrain -> trả {} -> tín hiệu này im lặng
    không tham gia, quyết định lùi về các tín hiệu còn lại.
    """
    import numpy as np
    ds = [d for d in doan if d.dai >= GIAY_TOI_THIEU_GIONG]
    if not ds:
        return {}
    tm = Path(thu_muc) if thu_muc else (_thu_muc_lam() / "doan")
    try:
        files = cat_doan_wav(wav16, ds, tm)
        if len(files) < 10:
            if ghi:
                ghi(f"giong: chi cat duoc {len(files)} doan -> bo qua")
            return {}
        kq = _chay_emb({str(k): v for k, v in files.items()}, py)
    except Exception as e:
        if ghi:
            ghi(f"giong: bo qua ({type(e).__name__}: {str(e)[:140]})")
        return {}
    E = {int(k): np.array(v) for k, v in (kq.get("emb") or {}).items() if v}
    if len(E) < 10:
        if ghi:
            ghi(f"giong: chi {len(E)} embedding -> bo qua")
        return {}
    ids = sorted(E)
    M = np.stack([E[i] for i in ids])
    theo_i = {d.i: d for d in ds}
    w = np.array([theo_i[i].dai for i in ids], dtype=float)
    tam = tam_nguoi_ke(M, w)
    if tam is None:
        return {}
    s = M @ tam
    if ghi:
        q = np.quantile(s, [0.05, 0.5])
        ghi(f"giong: {len(ids)} doan, thiet bi {kq.get('dev')}, "
            f"giong TAM 5% {q[0]:.3f} trung vi {q[1]:.3f}")
    return {int(i): float(v) for i, v in zip(ids, s)}


# ==========================================================================
# TÍN HIỆU (c) — PHỤ ĐỀ CHÁY SẴN CỦA NGƯỜI KỂ
# ==========================================================================

def cham_phu_de(video: str | Path, doan: Sequence[Doan],
                ghi: Optional[Callable[[str], None]] = None,
                ) -> dict[int, float]:
    """TÍN HIỆU (c). Trả {chỉ số: mật độ nét trong dải phụ đề}.

    **GIỚI HẠN PHẢI ĐỌC TRƯỚC KHI DÙNG SỐ NÀY:** đây chính là tín hiệu đã
    dùng để DỰNG bộ đối chứng của việc này, nên điểm của nó trên bộ đó là tự
    chấm bài mình. Muốn có con số thật thì phải đo trên bộ đối chứng KHÁC.

    Dùng lại `che_chu.do_dai_chu` + `che_chu._mat_na` — đã có cổng 56 canh,
    không viết bộ dò ảnh thứ hai.
    """
    try:
        from app.core import che_chu as cc
        import numpy as np
    except Exception as e:
        if ghi:
            ghi(f"phu de: bo qua ({type(e).__name__})")
        return {}
    try:
        dai = cc.do_dai_chu(str(video))
        tt = cc.thong_tin(str(video))
    except Exception as e:
        if ghi:
            ghi(f"phu de: bo qua ({type(e).__name__}: {str(e)[:100]})")
        return {}
    if not dai or not dai.co_chu or dai.y1 <= dai.y0:
        if ghi:
            ghi(f"phu de: nguon KHONG co chu chay san ({dai.ly_do}) "
                f"-> tin hieu nay im lang")
        return {}
    W = int(tt.get("rong") or 0)
    h = dai.y1 - dai.y0
    if W <= 0 or h <= 0:
        return {}
    ff = str(Path(__file__).resolve().parents[2] / "bin" / "ffmpeg.exe")
    ra = {}
    for x in doan:
        t = (x.start + x.end) / 2.0
        try:
            r = subprocess.run(
                [ff, "-v", "error", "-ss", f"{t:.3f}", "-i", str(video),
                 "-frames:v", "1", "-vf",
                 f"crop={W}:{h}:0:{dai.y0},format=gray",
                 "-f", "rawvideo", "-"],
                capture_output=True, creationflags=_NO_WIN, timeout=120)
        except Exception:
            continue
        if r.returncode != 0 or len(r.stdout) < W * h:
            continue
        g = np.frombuffer(r.stdout[:W * h], dtype=np.uint8).reshape(h, W)
        ra[x.i] = round(float(cc._mat_na(g).mean()), 5)
    return ra


# ==========================================================================
# KẾT HỢP — QUYẾT ĐỊNH
# ==========================================================================

def quyet_dinh(doan: Sequence[Doan],
               llm: Optional[dict] = None,
               giong: Optional[dict] = None,
               phu_de: Optional[dict] = None,
               nguong_giong: Optional[float] = None,
               nguong_phu_de: float = 0.02,
               can_so_dau: int = 1,
               tran_giu: float = TRAN_GIU_GOC,
               ) -> tuple[list[KetQua], TomTat]:
    """Gộp các tín hiệu -> quyết định từng đoạn. Hàm THUẦN (không I/O).

    `can_so_dau` = cần bao nhiêu tín hiệu ĐỘC LẬP nói "không phải người kể"
    thì mới giữ gốc. 1 = tin LLM một mình (đo được: bỏ sót 0,35%); 2 = đòi
    hai tín hiệu đồng ý (chặt hơn, bỏ sót ít hơn, nhưng bắt được ít hơn).

    `nguong_giong` PHẢI lấy từ `tu_kiem_giong()` của máy đang chạy. Để None
    thì tín hiệu giọng KHÔNG được tính vào `so_dau` — thiếu tự kiểm thì thà
    không dùng còn hơn dùng một thước chưa ai kiểm.

    HAI CHỐT AN TOÀN, đừng gỡ:
      · `khong_tin` (LLM không chấm nổi) KHÔNG bao giờ được giữ gốc;
      · tỉ lệ giữ gốc vượt `tran_giu` -> HUỶ HẾT, về lồng tiếng toàn bộ. Mẻ
        đảo nhãn đo được 11,6%, mà giữ gốc 11,6% câu liền nhau là rút ruột
        video.
    """
    ds = list(doan)
    ra: list[KetQua] = []
    tt = TomTat(so_doan=len(ds))
    if nguong_giong is None:
        nguong_giong = NGUONG_GIONG_MAC_DINH
    for x in ds:
        k = KetQua(i=x.i)
        dau: list[str] = []
        if llm is not None:
            k.llm = llm.get(x.i)
            if k.llm == "goc":
                dau.append("loi thoai")
        if giong is not None and x.i in giong:
            k.giong = round(float(giong[x.i]), 4)
            if nguong_giong is not None and k.giong < nguong_giong:
                dau.append("giong khac nguoi ke")
        if phu_de is not None and x.i in phu_de:
            k.phu_de = round(float(phu_de[x.i]), 5)
            if k.phu_de < nguong_phu_de:
                dau.append("khong co phu de nguoi ke")
        k.so_dau = len(dau)
        # `khong_tin` không được quyền giữ gốc, dù tín hiệu khác có kêu
        if k.llm == "khong_tin":
            k.quyet = LONG_TIENG
            k.ly_do = "LLM khong cham noi -> long tieng (an toan)"
        elif k.so_dau >= max(1, can_so_dau):
            k.quyet = GIU_GOC
            k.ly_do = " + ".join(dau)
        else:
            k.quyet = LONG_TIENG
            k.ly_do = "la loi nguoi ke"
        ra.append(k)

    giu = [k for k in ra if k.giu]
    theo_i = {x.i: x for x in ds}
    tt.so_giu = len(giu)
    tt.giay_giu = round(sum(theo_i[k.i].dai for k in giu), 3)
    tt.ty_le_giu = round(len(giu) / max(1, len(ds)), 4)
    if tt.ty_le_giu > tran_giu:
        tt.huy_vi_vuot_tran = True
        tt.canh_bao.append(
            f"giu goc {tt.ty_le_giu*100:.1f}% cau > tran "
            f"{tran_giu*100:.0f}% -> HUY HET, long tieng toan bo "
            f"(nghi bo cham hong)")
        for k in ra:
            k.quyet = LONG_TIENG
            k.ly_do = "huy vi vuot tran giu goc"
        tt.so_giu = 0
        tt.giay_giu = 0.0
    return ra, tt


def khoang_giu_goc(kq: Sequence[KetQua], doan: Sequence[Doan],
                   nhap: float = 0.06, gop_khe: float = 0.25,
                   ) -> list[tuple[float, float]]:
    """Các khoảng (giây, THANG NGUỒN) phải GIỮ NGUYÊN TIẾNG GỐC.

    `nhap` lùi mép vào trong một chút để không liếm sang câu người kể bên
    cạnh (mốc whisper vốn không sắc). `gop_khe` gộp hai khoảng cách nhau dưới
    mức đó — cắt vụn thì nơi gọi phải làm nhiều mối nối, mà mỗi mối nối là
    một chỗ có thể mất tiếng.

    Hàm THUẦN.
    """
    theo_i = {x.i: x for x in doan}
    tho = []
    for k in kq:
        if not k.giu or k.i not in theo_i:
            continue
        x = theo_i[k.i]
        a, b = x.start + nhap, x.end - nhap
        if b > a:
            tho.append((round(a, 3), round(b, 3)))
    tho.sort()
    ra: list[list[float]] = []
    for a, b in tho:
        if ra and a - ra[-1][1] <= gop_khe:
            ra[-1][1] = max(ra[-1][1], b)
        else:
            ra.append([a, b])
    return [(round(a, 3), round(b, 3)) for a, b in ra]


def bao_cao(kq: Sequence[KetQua], tt: TomTat,
            doan: Optional[Sequence[Doan]] = None) -> str:
    """Khối chữ cho nhật ký dây chuyền. KHÔNG EMOJI."""
    theo_i = {x.i: x for x in (doan or [])}
    dong = [f"Nguoi noi: {tt.so_doan} doan | giu goc {tt.so_giu} "
            f"({tt.ty_le_giu*100:.1f}%, {tt.giay_giu:.1f}s) | "
            f"long tieng {tt.so_doan - tt.so_giu}"]
    for c in tt.canh_bao:
        dong.append(f"  CANH BAO: {c}")
    for k in kq:
        if not k.giu:
            continue
        x = theo_i.get(k.i)
        moc = f"{x.start:7.2f}-{x.end:7.2f}" if x else f"#{k.i}"
        chu = (x.text[:40] if x else "")
        dong.append(f"  GIU GOC {moc}  [{k.ly_do}]  {chu}")
    return "\n".join(dong)
