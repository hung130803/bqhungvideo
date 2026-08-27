# -*- coding: utf-8 -*-
"""NHẤN NHÁ — nâng CAO ĐỘ đúng CHỮ ĐÁNG NHẤN. **ANH HÙNG ĐÃ DUYỆT BẰNG TAI.**

Anh Hùng nghe `_NGHE_THU_ANH_HUNG/nhan_nha_them/` và phán: *"CÓ NHẤN NHÁ"* —
+2,0 nửa cung tai anh ấy NHẬN RA (đo: NamMinh 4,10 -> 4,23 -> 4,53). Lời kêu
*"NGẮT QUÃNG QUÁ NHIỀU"* đi kèm là bệnh KHÁC, của chính FILE NGHE THỬ (nó nối
RAW, không xén lề: mỗi mối nối 1.118 ms chết) — **không phải do lớp này**, đã
đo: lớp nhấn KHÔNG đẻ thêm im (2,74->2,73 · 2,79->2,88 · 1,04->1,05 ·
1,96->1,97 · 1,91->1,91).

**BỐN CHỐT AN TOÀN, mỗi cái có SỐ ĐO đứng sau — đừng "dọn gọn" mất cái nào:**

(1) **CHỈ LIỀU NHẸ (+2,0 nửa cung). KHOÁ CỨNG cấm liều mạnh với TIẾNG VIỆT.**
    Tiếng Việt là ngôn ngữ CÓ THANH ĐIỆU: đẩy cao độ mạnh là đổi luôn DẤU, tức
    đổi NGHĨA. Đo trên `vn:Thanh Bình`: liều mạnh (+4,0) đưa đọc sai
    **3,33% -> 11,67%**, `bão` -> `báo`, `mất` -> `mắt`. Đây KHÔNG phải tham
    số để chỉnh tay; `_lieu_cho` chặn ở MÃ, không chặn ở giao diện.

(2) **`tempo` PHẢI LÀ 1,0 — ĐỘ DÀI FILE KHÔNG ĐƯỢC ĐỔI.** Bảng liều của lượt
    đo dùng `tempo=0,90` (kéo dài chữ nhấn 11%) nghe hay hơn, **nhưng ở đây
    không dùng được**: mốc TỪNG CHỮ đi ra từ `_synth_all_words` được dùng để
    dựng phụ đề và để `khop_thoi_gian` đặt câu vào khung hình. Kéo dài một chữ
    là dời MỌI mốc sau nó -> lệch tiếng-hình, đúng lỗi v1.87. Và `f0_nua_cung`
    (thước nhấn nhá) đo ĐỘ TRẢI CAO ĐỘ nên `tempo` **không đóng góp một phần
    nghìn nào** vào con số — bỏ nó đi không mất gì đo được.

(3) **HẬU KIỂM ĐỘ DÀI, lệch quá `LECH_TOI_DA` thì VỨT bản đã chỉnh.**
    `rubberband` là bộ xử lý theo khung, `tempo=1,0` vẫn có thể lệch vài ms.
    Không tin nó tự khai — ĐO lại file ra. Nhờ chốt này, "khớp hình không đổi"
    là bảo đảm ĐO ĐƯỢC chứ không phải lời hứa.

(4) **`formant=preserved` BẮT BUỘC.** Nâng cao độ mà không giữ formant là kéo
    cả khoang cộng hưởng lên = giọng "chuột Mickey" — tai nghe ra ngay.

**GỌI `rubberband` QUA `bin/ffmpeg.exe` NHƯ CHƯƠNG TRÌNH RỜI.** `librubberband`
là GPL-2.0; app này BÁN RA nên **TUYỆT ĐỐI KHÔNG `pip install pyrubberband`** —
link vào tiến trình là mất quyền giữ kín mã. Mô hình "chương trình rời, trao
đổi bằng dòng lệnh + file" là đúng cái đã chạy với ffmpeg nhiều năm, và
`LICENSES.txt` mục 1 đã khai.

**CHỌN CHỮ BẰNG LUẬT NGÔN NGỮ, 0 LƯỢT LLM.** Bản GỘP vào prompt dịch đo ra
1,00x lượt nhưng làm câu trả lời dài thêm 23-33% token, ăn vào `max_tokens`
(cổng 74) -> để dành.

Hàm THUẦN (trừ `ap_loat` gọi ffmpeg) — unit test được, không mạng, không LLM.
"""
from __future__ import annotations

import os
import re
import subprocess
import unicodedata
from pathlib import Path
from typing import Optional

from config import settings

_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


# ═══════════════════════ bảng luật chọn chữ ═══════════════════════
#: Từ ĐỂ HỎI — câu hỏi bao giờ cũng dồn trọng âm vào đây.
HOI = {
    "vi": {"ai", "gì", "nào", "đâu", "sao", "mấy", "bao", "nhiêu", "chăng",
           "hả", "à", "ư", "thế"},
    "en": {"who", "what", "where", "when", "why", "how", "which", "whose"},
}

#: Từ PHỦ ĐỊNH — chỗ lật nghĩa cả câu; đọc lướt là người nghe hiểu NGƯỢC.
PHU_DINH = {
    "vi": {"không", "chẳng", "chưa", "đừng", "chớ", "khỏi", "mất", "hết"},
    "en": {"not", "no", "never", "nothing", "nobody", "none", "cannot",
           "don't", "doesn't", "didn't", "can't", "won't", "isn't", "wasn't",
           "aren't", "weren't", "hasn't", "haven't"},
}

#: Từ CỰC ĐOAN / so sánh nhất — "cú hích" của câu viral.
CUC_DOAN = {
    "vi": {"nhất", "cực", "rất", "quá", "hoàn", "toàn", "tuyệt", "duy",
           "cả", "mọi", "tất", "ngay", "chính", "thật", "vô", "cùng"},
    "en": {"most", "best", "worst", "only", "all", "entire", "whole", "every",
           "unlike", "anything", "ever", "absolutely", "completely",
           "totally", "exactly", "right"},
}

#: Từ CHỨC NĂNG — **CẤM nhấn**. Thiếu bảng này thì luật "từ cuối câu" sẽ nhấn
#: vào `này` / `đó` / `the` và nghe ra đúng chữ "vô nghĩa" anh Hùng đã chê.
CHUC_NANG = {
    "vi": {"là", "và", "của", "cho", "với", "thì", "mà", "ở", "trong", "ra",
           "vào", "đã", "sẽ", "đang", "bị", "được", "các", "những", "một",
           "này", "kia", "đó", "ấy", "nó", "tôi", "bạn", "anh", "chị", "em",
           "về", "từ", "khi", "nếu", "vì", "nên", "cũng", "còn", "lại",
           "rồi", "sau", "trước", "trên", "dưới", "tới", "đến", "phải"},
    "en": {"a", "an", "the", "of", "to", "in", "on", "at", "for", "and", "or",
           "but", "is", "are", "was", "were", "be", "been", "being", "he",
           "she", "it", "they", "we", "you", "i", "his", "her", "its",
           "their", "our", "your", "my", "this", "that", "these", "those",
           "had", "has", "have", "do", "does", "did", "will", "would",
           "can", "could", "from", "with", "by", "as", "into", "up", "out"},
}

#: Trần chữ nhấn trên MỘT câu. Nhấn 5 chữ trong câu 10 chữ thì không còn là
#: "nhấn", nó thành đọc gằn.
TRAN_MOI_CAU = 2

#: Sàn điểm. **CÓ SÀN, không phải cứ lấy top-N**: câu toàn từ chức năng thì
#: đáp án ĐÚNG là KHÔNG NHẤN GÌ. Lấy top-N vô điều kiện chính là cách sinh ra
#: "nhấn bừa".
SAN_DIEM = 1.5


# ═══════════════════════ liều ═══════════════════════
#: Liều DUY NHẤT được phép. Xem chốt (1) ở docstring.
LIEU_NHE = 2.0

#: Trần CỨNG cho ngôn ngữ CÓ THANH ĐIỆU. `vn:Thanh Bình` đo được đọc sai
#: **3,33% -> 11,67%** ở liều mạnh (+4,0): `bão`->`báo`, `mất`->`mắt`.
#: Số này ghi ở đây để người sau đừng nới nó mà không đo lại.
TRAN_CO_THANH_DIEU = 2.0

#: Ngôn ngữ CÓ THANH ĐIỆU — nâng cao độ là đổi DẤU, tức đổi NGHĨA.
CO_THANH_DIEU = ("vi", "zh", "th", "yue", "lo", "my")

#: `tempo` KHÔNG BAO GIỜ khác 1,0 ở đường này. Xem chốt (2).
TEMPO = 1.0

#: Lệch độ dài tối đa cho phép sau khi chỉnh (giây). Quá mức này -> VỨT bản
#: đã chỉnh, giữ nguyên bản gốc. Xem chốt (3).
LECH_TOI_DA = 0.030

#: `formant=preserved` BẮT BUỘC — xem chốt (4).
RB_THEM = "formant=preserved:pitchq=quality"


def _sach(w: str) -> str:
    """Bỏ dấu câu quanh token, hạ chữ thường. GIỮ nguyên dấu tiếng Việt."""
    return str(w or "").strip(" \t\r\n.,!?;:\"'…()[]{}«»“”‘’-–—").lower()


def _bo_dau(w: str) -> str:
    s = unicodedata.normalize("NFD", str(w or ""))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def _co_so(w: str) -> bool:
    return any(c.isdigit() for c in str(w or ""))


def _ten_rieng(w: str, dau_cau: bool) -> bool:
    """Viết HOA mà KHÔNG ở đầu câu -> tên riêng / thương hiệu."""
    t = str(w or "").strip(" \t\r\n.,!?;:\"'…()[]{}")
    return (not dau_cau) and len(t) >= 2 and t[0].isupper() and not t.isupper()


def _nn(lang: str) -> str:
    l = str(lang or "").lower()
    return "vi" if l.startswith("vi") else "en"


def co_thanh_dieu(lang: str) -> bool:
    l = str(lang or "").lower().replace("_", "-").split("-")[0]
    return l in CO_THANH_DIEU


def lieu_cho(lang: str) -> float:
    """Liều nửa cung được phép cho ngôn ngữ này — **CỬA DUY NHẤT**.

    KHOÁ CỨNG NẰM Ở ĐÂY, không nằm ở giao diện: mẫu cũ đọc từ đĩa / payload
    job / lối gọi chưa nối đều phải đi qua hàm này (cùng khuôn
    `che_chu.chuan_muc_mo`). Đặt chốt ở thanh kéo thôi là mẫu lưu sẵn vẫn lọt.
    """
    if co_thanh_dieu(lang):
        return min(LIEU_NHE, TRAN_CO_THANH_DIEU)
    return LIEU_NHE


def cham_tung_tu(text: str, lang: str = "vi") -> list[tuple[str, float, str]]:
    """Chấm ĐIỂM ĐÁNG NHẤN cho từng token. Trả [(token, điểm, lý do)].

    Điểm là TỔNG các luật khớp — chữ vừa là số liệu vừa đứng cuối câu thì đáng
    nhấn hơn chữ chỉ khớp một luật. **KHÔNG chuẩn hoá về 0-1**: cái cần là XẾP
    HẠNG trong CÙNG một câu, không phải so điểm giữa hai câu.

    Đếm từ dùng lại `recap._word_tokens` (CJK-aware) — KHÔNG `.split()`: câu
    Trung/Nhật không có dấu cách thì `.split()` ra ĐÚNG 1 token và mọi luật ở
    đây tắt IM LẶNG (bệnh đã sập ở cổng 40 · 52 · 54).
    """
    from app.ai import recap

    nn = _nn(lang)
    toks = recap._word_tokens(str(text or ""))
    if not toks:
        return []
    ket = set()
    for i, t in enumerate(toks):
        if re.search(r"[.!?…]$", t) or i == len(toks) - 1:
            ket.add(i)
    dau_cau = {0} | {i + 1 for i in ket if i + 1 < len(toks)}

    ra: list[tuple[str, float, str]] = []
    for i, t in enumerate(toks):
        s = _sach(t)
        sd = _bo_dau(s)
        diem, ly = 0.0, []
        if s in CHUC_NANG[nn] or sd in {_bo_dau(x) for x in CHUC_NANG[nn]}:
            ra.append((t, 0.0, "chức năng — CẤM nhấn"))
            continue
        if _co_so(t):
            diem += 3.0
            ly.append("số liệu")
        if s in HOI[nn]:
            diem += 2.5
            ly.append("từ để hỏi")
        if s in PHU_DINH[nn]:
            diem += 2.5
            ly.append("phủ định")
        if s in CUC_DOAN[nn]:
            diem += 2.0
            ly.append("cực đoan")
        if _ten_rieng(t, i in dau_cau):
            diem += 2.0
            ly.append("tên riêng")
        if i in ket:
            diem += 1.5
            ly.append("cuối câu")
        if len(s) >= 6 and nn == "en":
            diem += 0.5
            ly.append("từ dài")
        ra.append((t, diem, " + ".join(ly) if ly else ""))
    return ra


def chon(text: str, lang: str = "vi", toi_da: int = TRAN_MOI_CAU,
         san: float = SAN_DIEM) -> list[int]:
    """Chỉ số token đáng nhấn, nhiều nhất `toi_da`, điểm phải >= `san`.

    Hai chữ nhấn KHÔNG được đứng CẠNH NHAU — nhấn liền hai chữ nghe thành đọc
    gằn, không thành hai điểm nhấn.
    """
    diem = cham_tung_tu(text, lang)
    hang = sorted(range(len(diem)), key=lambda i: (-diem[i][1], i))
    ra: list[int] = []
    for i in hang:
        if diem[i][1] < san:
            break
        if any(abs(i - j) <= 1 for j in ra):
            continue
        ra.append(i)
        if len(ra) >= toi_da:
            break
    return sorted(ra)


def khop_cua(moc: list, idx: list[int], toks: list[str]) -> list:
    """Đổi CHỈ SỐ TOKEN -> cửa sổ (giây) trên mốc máy đọc trả về.

    Mốc của máy đọc và token của bộ luật **có thể lệch số phần tử** (edge-tts
    gộp cụm, gióng hàng tách khác) -> khớp theo MẶT CHỮ trước. Không khớp được
    thì **BỎ chữ đó** chứ không đoán bừa: nhấn nhầm chữ tệ hơn không nhấn.
    """
    if not moc:
        return []
    sach = lambda s: re.sub(r"[^\w]", "", str(s)).lower()      # noqa: E731
    mm = []
    for m in moc:
        try:
            mm.append((float(m[0]), float(m[1]), sach(m[2])))
        except (TypeError, ValueError, IndexError):
            continue
    ra = []
    for i in idx:
        if i >= len(toks):
            continue
        c = sach(toks[i])
        if not c:
            continue
        hit = [k for k, (_a, _b, t) in enumerate(mm) if t and t == c]
        if not hit:
            hit = [k for k, (_a, _b, t) in enumerate(mm) if t and c in t]
        if not hit:
            continue                     # KHÔNG đoán bừa
        a, b, _t = mm[hit[0]]
        if b > a:
            ra.append((a, b))
    return sorted(set(ra))


def chuoi_rb(st_nua_cung: float, tempo: float = TEMPO) -> str:
    """`pitch` của `rubberband` là **HỆ SỐ TẦN SỐ**, không phải nửa cung.

    Đặt thẳng `pitch=2` là nhảy một QUÃNG TÁM (giọng chuột), không phải "nhấn
    nhẹ" -> phải quy đổi `2**(st/12)`.
    """
    p = 2.0 ** (float(st_nua_cung) / 12.0)
    return f"rubberband=pitch={p:.6f}:tempo={float(tempo):.4f}:{RB_THEM}"


def graph_nhan(dai: float, cua: list[tuple[float, float]],
               st_nc: float, tempo: float = TEMPO) -> str:
    """Chuỗi filter: cắt file thành mảnh, mảnh NÀO trong `cua` thì chỉnh.

    `atrim`+`concat` trong MỘT graph, không mở nhiều lượt ffmpeg — cùng khuôn
    `_tach_va_noi_manh` / `_SH_MAU` của đường xuất.
    """
    if dai <= 0 or not cua:
        return ""
    moc: list[float] = [0.0]
    for a, b in cua:
        moc += [max(0.0, a), min(dai, b)]
    moc.append(dai)
    moc = sorted(set(round(x, 4) for x in moc))
    cap = [(moc[i], moc[i + 1]) for i in range(len(moc) - 1)
           if moc[i + 1] - moc[i] > 0.005]
    if not cap:
        return ""
    trong = lambda a, b: any(a >= x - 1e-3 and b <= y + 1e-3    # noqa: E731
                             for x, y in cua)
    ph = []
    n = len(cap)
    ra = [f"[0:a]asplit={n}" + "".join(f"[s{i}]" for i in range(n)) + ";"]
    for i, (a, b) in enumerate(cap):
        f = f"[s{i}]atrim={a:.4f}:{b:.4f},asetpts=PTS-STARTPTS"
        if trong(a, b) and abs(st_nc) > 1e-6:
            f += "," + chuoi_rb(st_nc, tempo)
        ra.append(f + f"[p{i}];")
        ph.append(f"[p{i}]")
    ra.append("".join(ph) + f"concat=n={n}:v=0:a=1[out]")
    return "".join(ra)


def _dai(p: str | Path) -> float:
    try:
        r = subprocess.run(
            [settings.FFPROBE_PATH, "-v", "error", "-show_entries",
             "format=duration", "-of", "default=nk=1:nw=1", str(p)],
            capture_output=True, text=True, timeout=60,
            creationflags=_CREATE_NO_WINDOW)
        return float((r.stdout or "0").strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0.0


def bat_khong() -> bool:
    """Cờ TẮT/BẬT. **MẶC ĐỊNH TẮT** — tắt thì mọi thứ Y HỆT bản cũ."""
    return str(os.environ.get("BQ_NHAN_NHA", "")).strip().lower() in (
        "1", "true", "yes", "on")


def ap_mot(path: str | Path, text: str, moc: list, lang: str) -> bool:
    """Áp nhấn nhá vào MỘT file, TẠI CHỖ. Trả True nếu ĐÃ đổi file.

    Fail-safe theo mọi hướng: không mốc / không chọn được chữ / ffmpeg lỗi /
    **độ dài lệch quá `LECH_TOI_DA`** -> GIỮ NGUYÊN bản gốc và trả False.
    """
    from app.ai import recap

    p = Path(path)
    if not p.exists() or not moc:
        return False
    toks = recap._word_tokens(str(text or ""))
    idx = chon(str(text or ""), lang)
    if not idx or not toks:
        return False
    cua = khop_cua(moc, idx, toks)
    if not cua:
        return False
    d0 = _dai(p)
    if d0 <= 0:
        return False
    g = graph_nhan(d0, cua, lieu_cho(lang))
    if not g:
        return False
    tam = p.with_name(p.stem + "._nn.wav")
    try:
        r = subprocess.run(
            [settings.FFMPEG_PATH, "-y", "-v", "error", "-i", str(p),
             "-filter_complex", g, "-map", "[out]", "-ac", "1",
             "-ar", "44100", "-c:a", "pcm_s16le", str(tam)],
            capture_output=True, text=True, timeout=300,
            creationflags=_CREATE_NO_WINDOW)
        if r.returncode != 0 or not tam.exists() or tam.stat().st_size < 2000:
            return False
        d1 = _dai(tam)
        # CHỐT (3): độ dài KHÔNG được đổi — không thì mốc từng chữ đi ra ngoài
        # hàm này thành SAI, và đó là lỗi lệch tiếng-hình v1.87.
        if abs(d1 - d0) > LECH_TOI_DA:
            return False
        os.replace(str(tam), str(p))
        return True
    except (OSError, subprocess.SubprocessError):
        return False
    finally:
        try:
            if tam.exists():
                tam.unlink()
        except OSError:
            pass


def ap_loat(texts: list[str], paths: list[str], ok: list[bool],
            words: list[list], lang: str,
            bat: Optional[bool] = None) -> int:
    """Áp nhấn nhá cho CẢ LOẠT. Trả số câu ĐÃ đổi. **KHÔNG BAO GIỜ NÉM.**

    Đây là cửa được `dubbing._synth_all_words` gọi ở MỌI đường ra, nên nó phải
    im lặng chịu mọi kiểu dữ liệu xấu: lệch độ dài list, mốc rỗng, file mất.
    """
    if bat is None:
        bat = bat_khong()
    if not bat:
        return 0
    dem = 0
    for i, p in enumerate(paths or ()):
        try:
            if i >= len(ok) or not ok[i] or not p:
                continue
            t = texts[i] if i < len(texts) else ""
            m = words[i] if i < len(words) else []
            if ap_mot(p, t, m, lang):
                dem += 1
        except Exception:                                    # noqa: BLE001
            continue
    return dem
