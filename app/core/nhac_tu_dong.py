# -*- coding: utf-8 -*-
"""NHẠC NỀN TỰ CHỌN THEO NỘI DUNG — NHỎ, NÉ LỜI, KHÔNG LỆCH KHÔNG KHÍ (02/11/2026).

Anh Hùng: *"tự chọn, kéo âm lượng nhạc nền mức nhỏ thôi ... đang kịch tính hấp
dẫn lại cho nhạc vui vẻ không được đâu"*. Bật bằng mẫu: Nhạc nền = "Tự chọn
theo nội dung" -> `bgm_path` mang chuỗi đánh dấu `MA_TU_DONG`. Chuỗi đó nằm
trong khoá chống trùng (`services.enqueue_export` băm `bgm_path`) nên clip KHÔNG
bật chế độ này giữ khoá Y NGUYÊN — 200-300 kênh không xuất lại.

LUẬT CHỌN TÂM TRẠNG (hàm `tam_trang`), theo thứ tự — dừng ở luật đầu khớp:
  1. CĂNG THẲNG đủ điểm (cảnh sát, súng, truy đuổi, tai nạn, 🚨...) -> 'tension'
  2. BUỒN đủ điểm (qua đời, tang lễ, ung thư, 😭...) -> 'emotional'
  3. BÍ ẨN đủ điểm (hồn ma, mất tích, điều tra, 👻...) -> 'mystery'
  4. có dấu hiệu nặng nhưng CHƯA đủ điểm -> 'calm' (KHÔNG ra nhạc vui)
  5. CHỈ KHI không có MỘT dấu hiệu nặng nào: VUI (haha, hài, 😂) -> 'playful';
     tích cực (cảm ơn, tuyệt vời, 😍) -> 'bright'
  6. không đủ bằng chứng -> 'calm' (nhạc êm trung tính).
=> **nhạc vui/tích cực KHÔNG BAO GIỜ được chọn khi có MỘT dấu hiệu nặng nào**
(cổng 106 kiểm, thử phá đảo thứ tự -> phải đỏ).

ÂM LƯỢNG (hàm `he_so_db`): đích = MỨC LỜI của chính clip − `DUOI_LOI_DB` (12 dB)
— dưới lời rất xa, nghe như lớp nền. Lúc đang nói còn hạ thêm `NE_LOI_DB`. Không
đo được lời (clip câm) -> đặt cố định rất nhỏ. KHÔNG BAO GIỜ tăng nhạc quá
`TANG_TOI_DA` (file kho đã chuẩn -20 LUFS).

BỎ QUA (hàm `bo_qua`): video gốc đã có lớp nền to (nhạc sẵn/ồn liên tục — đo
mức ở KHOẢNG KHÔNG NÓI so với lúc nói) -> không chèn: hai lớp nhạc chồng nhau
nghe rối, đúng loại "thêm vô duyên".
"""
from __future__ import annotations

import hashlib
import os
import re
import unicodedata
from typing import Optional

MA_TU_DONG = "bqmusic:auto:noi_dung"

#: Nhạc nằm dưới MỨC LỜI bấy nhiêu dB lúc KHÔNG nói. 18 -> 12 (02/11/2026):
#: anh Hùng nghe file thử "không nghe thấy tiếng nhạc, bé quá". 12 dB dưới lời
#: + né thêm 6 dB lúc nói (= 18 dB dưới giọng) là mức nhạc nền phổ biến.
DUOI_LOI_DB = 12.0
NE_LOI_DB = 6.0          # đang nói: hạ thêm
DOC_NE = 0.35            # giây vào/ra của bướu né lời (êm, không giật)
#: không bao giờ kéo nhạc to hơn file kho quá mức này. 3 -> 6 (02/11/2026):
#: có thêm mức "Rất to" (6 dB dưới lời); clip lời to (-10 dBFS) cần +4 dB,
#: trần 3 thì user chọn "Rất to" mà không to thêm được. Đỉnh vượt đã có
#: `alimiter` sau khi trộn chặn.
TANG_TOI_DA = 6.0
GIAM_TOI_DA = -40.0
#: không đo được lời: nhạc ở mức tuyệt đối rất nhỏ (LUFS xấp xỉ)
MUC_KHONG_LOI = -32.0
#: lớp nền gốc (lúc không nói) chỉ thấp hơn lời ÍT HƠN mức này -> BỎ QUA.
#: ĐO 02/11/2026 trên 18 video THẬT: nền lúc không nói thấp hơn lời 5,6-22,5
#: dB (gió, đường phố, phòng — video quay đời thực luôn có). Bản đầu đặt 12 dB
#: -> 4/4 video nghe thử bị bỏ oan = tính năng không bao giờ chèn. Cũng ĐÃ ĐO:
#: trộn nhạc kho vào chính các video đó, độ chênh mức đổi 0,5-8 dB và độ PHẲNG
#: PHỔ đổi < 0,05 -> KHÔNG phân biệt được "đã có nhạc" với "ồn nền" bằng số đo
#: rẻ. Nên chỉ bỏ khi nền GẦN TO BẰNG LỜI (< 6 dB); còn lại chèn — nhạc nằm
#: dưới lời 12-18 dB nên nếu nguồn lỡ có nhạc thì nhạc app chìm dưới, không đè.
#: 6 -> 3 (02/11/2026): anh Hùng "không sợ trùng, cứ tự động thêm vào" —
#: 6 dB vẫn bỏ 2/4 video nghe thử (đám đông ồn, nền thấp hơn lời 5,4 dB). Nay
#: chỉ bỏ khi nền TO GẦN BẰNG LỜI (kiểu video ca nhạc / nhạc sẵn rất to).
NEN_GOC_SAT_LOI_DB = 3.0
VAO_RA = (1.0, 1.5)      # mờ vào / mờ ra (giây)

# ---- BẢNG DẤU HIỆU: (MẠNH = 2 điểm, YẾU = 1 điểm); cần >= `NGUONG` điểm.
# Soi 3.000 clip thật 02/11/2026: chữ CÂU VIEW ("Shocking", "Secret") và chữ
# nhiều nghĩa ("crying" trong "My Wallet's Crying", "death" trong "Death Match",
# "shot" = cú quay) làm đoán sai -> bỏ hẳn hoặc để YẾU (một mình không đủ).
NGUONG = 2
_CANG_MANH = (
    "cảnh sát", "công an", "súng", "nổ súng", "truy đuổi", "cướp", "bắt giữ",
    "còng tay", "tai nạn", "hung thủ", "giết người", "ma túy", "ma tuý",
    "lừa đảo", "cứu với",
    "police", "cops", "gun", "gunshot", "chase", "robbery", "arrest",
    "arrested", "handcuff", "handcuffs", "crash", "accident", "killer",
    "murder", "kidnapping", "scam", "scammed", "scammer", "fraud",
    "emergency", "assault", "drunk driver", "dui", "sting operation",
    "shooting", "stabbing", "fentanyl",
    "警察", "抢劫", "车祸", "杀人", "事故", "경찰", "사고", "사기",
    "🚨", "🔪",
)
_CANG_YEU = (
    "đánh nhau", "tấn công", "trộm", "nguy hiểm", "đe doạ", "đe dọa",
    "cấp cứu", "la hét", "bỏ chạy", "đâm", "chém",
    "cop", "fight", "attack", "steal", "stealing", "danger", "dangerous",
    "threat", "scream", "screaming", "help me", "detained", "trespass",
    "officer", "deputy", "sheriff", "jail", "eviction", "showdown",
    "危险", "打架", "危ない", "逃げ", "위험",
    "😨", "😱", "😰", "🫠", "💀", "😡", "🤬",
)
_BUON_MANH = (
    "qua đời", "tử vong", "đám tang", "tang lễ", "ung thư", "thương tiếc",
    "passed away", "funeral", "cancer", "grief", "heartbroken", "tragic",
    "去世", "葬礼", "癌症", "亡くな", "葬式", "장례",
    "😭", "💔", "🕊",
)
_BUON_YEU = (
    "khóc", "nước mắt", "đã mất", "đau lòng", "mồ côi", "chia tay", "cô đơn",
    "died", "crying", "tears", "lonely", "miss you", "goodbye",
    "哭", "泣", "눈물", "😢", "🥺",
)
_BI_AN_MANH = (
    "hồn ma", "mất tích", "điều tra", "manh mối", "ma ám",
    "ghost", "haunted", "investigation", "unexplained",
    "supernatural", "paranormal", "ouija", "creepy",
    "鬼", "失踪", "幽霊", "귀신", "실종", "👻",
)
_BI_AN_YEU = (
    "bí ẩn", "kỳ lạ", "lạ lùng", "ma", "không ai biết",
    "mystery", "mysterious", "strange", "weird", "clue", "missing",
    "神秘", "謎", "미스터리", "🔍", "🕵",
)
_VUI = (
    "haha", "hihi", "hehe", "buồn cười", "chết cười", "hài", "vui quá",
    "trò đùa", "lol", "lmao", "funny", "hilarious", "joke", "prank",
    "laughing", "comedy", "哈哈", "笑", "웃", "ㅋㅋ",
    "😂", "🤣", "😆", "😜", "🤪",
)
_TICH_CUC = (
    "cảm ơn", "tuyệt vời", "hạnh phúc", "yêu thương", "tốt bụng", "ấm áp",
    "chúc mừng",
    "thank you", "amazing", "wholesome", "kindness", "happy", "beautiful",
    "wonderful", "congrat", "congratulations", "birthday",
    "谢谢", "幸福", "ありがとう", "감사", "행복",
    "😍", "🥰", "❤", "😊", "🎉", "🙏",
)


#: Mức "Độ to nhạc" user chọn trong mẫu: nhãn -> số dB nhạc nằm DƯỚI lời.
MUC_CHON = (("Rất nhỏ", 20), ("Nhỏ", 16), ("Vừa (mặc định)", 12),
            ("To", 9), ("Rất to", 6))
DUOI_LOI_MIN, DUOI_LOI_MAX = 4.0, 24.0


def ma_tu_dong(duoi_db=None) -> str:
    """Chuỗi đánh dấu cho `bgm_path`. Mức MẶC ĐỊNH -> ĐÚNG `MA_TU_DONG` cũ
    (khoá chống trùng không đổi); mức khác -> `MA_TU_DONG@<dB>` (đổi khoá ->
    clip xuất lại đúng mức mới)."""
    try:
        d = float(duoi_db)
    except (TypeError, ValueError):
        return MA_TU_DONG
    d = max(DUOI_LOI_MIN, min(DUOI_LOI_MAX, d))
    if abs(d - DUOI_LOI_DB) < 0.05:
        return MA_TU_DONG
    return f"{MA_TU_DONG}@{d:g}"


def muc_tu_ma(ref) -> float:
    """Số dB nhạc nằm dưới lời đọc từ chuỗi đánh dấu (hỏng -> mặc định)."""
    s = str(ref or "").strip()
    if "@" in s:
        try:
            return max(DUOI_LOI_MIN, min(DUOI_LOI_MAX,
                                         float(s.rsplit("@", 1)[1])))
        except ValueError:
            pass
    return DUOI_LOI_DB


def la_tu_dong(ref) -> bool:
    s = str(ref or "").strip()
    return s == MA_TU_DONG or s.startswith(MA_TU_DONG + "@")


def _chu(s: str) -> str:
    return unicodedata.normalize("NFC", str(s or "")).lower()


def _dem(text: str, tu: tuple) -> list:
    """Các khoá xuất hiện trong `text`. Khoá chữ Latin (cả tiếng Việt) khớp
    TRỌN TỪ — 'ma' không khớp trong 'mang', 'run' không khớp 'brunch'."""
    ra = []
    for k in tu:
        if re.search(r"[A-Za-zÀ-ỹ]", k):
            if re.search(r"(?<![\wÀ-ỹ])" + re.escape(k) + r"(?![\wÀ-ỹ])", text):
                ra.append(k)
        elif k in text:
            ra.append(k)
    return ra


def tam_trang(loi: str, tieu_de: str = "") -> tuple[str, str]:
    """(tâm trạng, lý do kèm bằng chứng). Hàm thuần — xem luật ở đầu file.
    Mỗi nhóm NẶNG chấm điểm: dấu hiệu MẠNH 2, YẾU 1, cần >= `NGUONG`."""
    t = _chu(tieu_de) + " | " + _chu(loi)
    for x in ("chết cười", "cười chết", "to death", "dying of laughter"):
        t = t.replace(x, " haha ")
    for nhom, manh, yeu, ten in (
            ("tension", _CANG_MANH, _CANG_YEU, "căng thẳng"),
            ("emotional", _BUON_MANH, _BUON_YEU, "buồn/cảm xúc"),
            ("mystery", _BI_AN_MANH, _BI_AN_YEU, "bí ẩn")):
        km, ky = _dem(t, manh), _dem(t, yeu)
        if 2 * len(km) + len(ky) >= NGUONG:
            return nhom, f"có dấu hiệu {ten}: {', '.join((km + ky)[:4])}"
    if any(_dem(t, b) for b in (_CANG_MANH, _CANG_YEU, _BUON_MANH, _BUON_YEU,
                                 _BI_AN_MANH, _BI_AN_YEU)):
        # có dấu hiệu nặng nhưng CHƯA đủ điểm -> không đủ chắc để chọn nhạc
        # nặng, và CŨNG KHÔNG được ra nhạc vui: lấy nhạc êm.
        return "calm", "có dấu hiệu nặng chưa rõ -> nhạc êm (không ra nhạc vui)"
    k = _dem(t, _VUI)
    if k:
        return "playful", f"đang vui/hài: {', '.join(k[:4])}"
    k = _dem(t, _TICH_CUC)
    if k:
        return "bright", f"tích cực: {', '.join(k[:4])}"
    return "calm", "không đủ dấu hiệu -> nhạc êm trung tính"


def chon_bai(tracks: list, mood: str, khoa: str) -> Optional[dict]:
    """Bài trong đúng tâm trạng, TIỀN ĐỊNH theo `khoa` (video + Part) để xuất
    lại ra cùng bài. Không có bài đúng tâm trạng -> lùi 'calm' (không bao giờ
    lùi sang vui/tích cực). Hàm thuần."""
    for m in (mood, "calm"):
        ds = sorted((t for t in tracks or [] if t.get("mood") == m),
                    key=lambda t: hashlib.sha256(
                        (str(khoa) + "|" + str(t.get("id"))).encode())
                    .hexdigest())
        if ds:
            return ds[0]
    return None


def bo_qua(loi_db: Optional[float], nen_khong_noi_db: Optional[float]) -> str:
    """Lý do KHÔNG chèn nhạc — LUÔN '' từ 02/11/2026.

    Anh Hùng chốt: *"mặc định video nào cũng phải chèn thêm nhạc nền, nhưng để
    vừa thôi"*. Bản đầu bỏ qua khi nền gốc to (ngưỡng 12 -> 6 -> 3 dB) nhưng
    ĐÃ ĐO: không phân biệt được "đã có nhạc" với "ồn nền" (xem
    `NEN_GOC_SAT_LOI_DB`), nên bỏ qua chỉ làm mất nhạc oan. Mức nhạc luôn bám
    MỨC LỜI (dưới 12 dB, nói thì hạ thêm) nên không bao giờ đè giọng.
    Giữ hàm (và hằng số) để nhật ký vẫn ghi mức nền gốc; caller không bỏ qua."""
    return ""


#: Giá trị ô "Nhạc nền" của MẪU -> chế độ thật. Mặc định = TỰ CHỌN.
#: 'off' là giá trị mặc định CŨ của mọi mẫu (không phân biệt được user cố ý tắt
#: hay chưa đụng tới) -> tính là TỰ CHỌN theo lời anh Hùng "video nào cũng
#: phải chèn"; muốn tắt thật thì chọn "Tắt hẳn" (`none`).
def che_do_mau(mode) -> str:
    m = str(mode or "").strip()
    if m in ("random", "fixed", "none", "auto"):
        return m
    return "auto"


def he_so_db(loi_db: Optional[float], bai_lufs: float,
             duoi_db: Optional[float] = None) -> float:
    """Hệ số (dB) cho file nhạc. `duoi_db` = mức user chọn (None = mặc định
    `DUOI_LOI_DB`). Hàm thuần."""
    duoi = DUOI_LOI_DB if duoi_db is None else max(
        DUOI_LOI_MIN, min(DUOI_LOI_MAX, float(duoi_db)))
    dich = (MUC_KHONG_LOI + (DUOI_LOI_DB - duoi)
            if loi_db is None or loi_db < -60 else float(loi_db) - duoi)
    return max(GIAM_TOI_DA, min(TANG_TOI_DA, dich - float(bai_lufs)))


def bieu_thuc_ne(cau: list, dur: float) -> str:
    """Biểu thức `volume` (eval=frame) hạ thêm `NE_LOI_DB` trong lúc nói, vào/ra
    êm `DOC_NE` giây. `cau` = [(đầu, cuối, ...)] trên timeline ĐẦU RA. Gộp câu
    sát nhau (< 0,6 s) để nhạc không nhấp nhô giữa 2 câu. '' = không né."""
    kh = []
    for c in sorted(cau or []):
        a, b = max(0.0, float(c[0])), min(float(dur), float(c[1]))
        if b - a < 0.15:
            continue
        if kh and a - kh[-1][1] < 0.6:
            kh[-1][1] = max(kh[-1][1], b)
        else:
            kh.append([a, b])
    if not kh:
        return ""
    sau = 1.0 - 10.0 ** (-NE_LOI_DB / 20.0)
    r = DOC_NE
    bu = [f"clip(min((t-{a - r:.3f})/{r:.3f},({b + r:.3f}-t)/{r:.3f}),0,1)"
          for a, b in kh[:80]]
    tong = bu[0]
    for x in bu[1:]:
        tong = f"max({tong},{x})"
    return f"volume='1-{sau:.4f}*{tong}':eval=frame"


#: lời giả định khi nghe thử mà CHƯA chọn video (dBFS, mức lời phổ biến)
LOI_GIA_DINH = -16.0


def dung_nghe_thu(out_wav: str, mood: Optional[str] = None,
                  duoi_db: Optional[float] = None, src: Optional[str] = None,
                  transcript: Optional[dict] = None, t0: float = 0.0,
                  dai: float = 20.0, khoa: str = "",
                  nhac_file: Optional[str] = None,
                  vol: Optional[float] = None) -> dict:
    """Dựng file WAV NGHE THỬ nhạc nền — ĐÚNG công thức lúc xuất.

    Có `src` (video đang chọn): lấy `dai` giây tiếng gốc từ `t0`, ĐO mức lời
    thật (`_do_muc_clip`), đặt nhạc dưới lời `duoi_db`, né lời theo câu chép
    (nếu có), mờ vào/ra, trộn + chặn đỉnh. Không có video: phát nhạc một mình
    ở đúng mức sẽ dùng với lời -16 dBFS. `mood=None` -> tự đoán từ lời.
    Trả {'ok', 'tam_trang', 'bai', 'he_so_db', 'ly_do' | 'loi'}. KHÔNG ném.
    Không đụng Qt (gọi từ luồng nền được)."""
    import subprocess
    try:
        from app.core import ffmpeg_utils as F
        from app.core import music_library as ML
        from app.core.sfx_chon import cau_ra_timeline
        from config import settings
        ff = settings.FFMPEG_PATH
        nw = 0x08000000 if os.name == "nt" else 0
        dai = max(5.0, min(60.0, float(dai)))
        t0 = max(0.0, float(t0))
        cau = cau_ra_timeline(transcript or {}, [(t0, t0 + dai)], 1.0)
        ly = "anh chọn"
        if nhac_file:
            # NHẠC RIÊNG của anh Hùng (thư mục / 1 bài): nghe ĐÚNG như lúc xuất
            # = hệ số cố định `vol` của thanh "Âm lượng nhạc", không né lời.
            if not os.path.isfile(str(nhac_file)):
                return {"ok": False, "loi": "không thấy file nhạc: "
                        + os.path.basename(str(nhac_file))}
            nhac = str(nhac_file)
            bai = {"title": os.path.basename(nhac), "author": "nhạc của anh",
                   "lufs": None}
            mood = "nhạc của anh"
        else:
            if not mood:
                loi = " ".join(c[2] for c in cau)
                mood, ly = tam_trang(loi, os.path.basename(str(src or "")))
            bai = chon_bai(list(ML.catalog()), mood, khoa or f"nghe|{src}|{t0}")
            if bai is None:
                return {"ok": False, "loi": "kho nhạc rỗng"}
            nhac = ML.resolve(ML.PREFIX + bai["id"])
        co_goc = bool(src) and os.path.isfile(str(src))
        loi_db = None
        if co_goc:
            mc = F._do_muc_clip(["-ss", f"{t0:.3f}", "-t", f"{dai:.3f}",
                                 "-i", str(src)])
            if mc is not None and -70.0 < mc["nen"] < 0.0:
                loi_db = mc["loi"]
            else:
                co_goc = False          # video câm / đo hỏng -> nghe nhạc riêng
        if nhac_file:
            import math
            v = max(0.0, min(1.0, float(0.15 if vol is None else vol)))
            g = 20.0 * math.log10(max(v, 1e-4))
            ne = ""                     # nhạc riêng lúc xuất KHÔNG né lời
        else:
            g = he_so_db(loi_db if co_goc else LOI_GIA_DINH,
                         bai.get("lufs", -20.0), duoi_db)
            ne = bieu_thuc_ne(cau, dai) if co_goc else ""
        vi, vo = VAO_RA
        loc = (f"atrim=0:{dai:.3f},asetpts=PTS-STARTPTS,volume={g:.2f}dB"
               + (f",{ne}" if ne else "")
               + f",afade=t=in:d={vi:.2f},afade=t=out:st={dai - vo:.3f}"
               f":d={vo:.2f}")
        if co_goc:
            cmd = [ff, "-nostdin", "-y", "-hide_banner", "-loglevel", "error",
                   "-ss", f"{t0:.3f}", "-t", f"{dai:.3f}", "-i", str(src),
                   "-stream_loop", "-1", "-i", nhac, "-filter_complex",
                   f"[0:a]aresample=48000,apad=whole_dur={dai:.3f}[v];"
                   f"[1:a]aresample=48000,{loc}[m];"
                   "[v][m]amix=inputs=2:duration=first:normalize=0,"
                   "alimiter=limit=0.89:level=0[o]", "-map", "[o]"]
        else:
            cmd = [ff, "-nostdin", "-y", "-hide_banner", "-loglevel", "error",
                   "-stream_loop", "-1", "-i", nhac, "-filter_complex",
                   f"[0:a]aresample=48000,{loc},alimiter=limit=0.89:level=0[o]",
                   "-map", "[o]"]
        cmd += ["-ac", "2", "-ar", "44100", "-t", f"{dai:.3f}", str(out_wav)]
        r = subprocess.run(cmd, capture_output=True, timeout=180,
                           creationflags=nw, stdin=subprocess.DEVNULL)
        if r.returncode != 0 or not os.path.isfile(out_wav) \
                or os.path.getsize(out_wav) < 10000:
            return {"ok": False, "loi": (r.stderr or b"").decode(
                "utf-8", "replace")[-200:] or "ffmpeg không ra file"}
        return {"ok": True, "tam_trang": mood, "bai": bai.get("title"),
                "tac_gia": bai.get("author"), "he_so_db": round(g, 1),
                "ly_do": ly, "co_loi": co_goc}
    except Exception as e:  # noqa: BLE001 — nghe thử lỗi không được làm sập
        return {"ok": False, "loi": f"{type(e).__name__}: {e}"}
