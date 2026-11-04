# -*- coding: utf-8 -*-
"""NGÔN NGỮ VIDEO KHI CHÉP LỜI LÀ CHỮ BỊA (03/11/2026, cổng 109).

Anh Hùng (ảnh kênh 2 nhóm mỹ bkt): Part xuất ra tên file "Part 1 Gå inn i
bygget. #Rengar #Meme #Random #AllRight" — video Mỹ quay công trường mà tên
file lại là tiếng Na Uy.

ĐO TRÊN DB THẬT: video "WHAT MY DAY LOOKS LIKE ON A CONSTRUCTION SITE" dài
1.088 giây chỉ có 173 từ (0,16 từ/giây; người nói thật ~2-3). Groq gặp tiếng
máy móc/ồn thì BỊA chữ: "Gå inn på denne sida", "Takk for watching",
"Ik heb een koffie gekocht", "ТРЕВОЖНАЯ МУЗЫКА" — trộn Na Uy · Hà Lan · Nga.
Video cùng kênh "A Day in the Life of a Construction Worker" bị dán nhãn
luôn "Norwegian Nynorsk" -> AI viết tiêu đề tiếng Na Uy theo nhãn đó.

App ĐÃ nhận ra "video không lời" (`chon_doan.co_loi_noi_that`) để chọn đoạn
bằng tiếng + hình, nhưng tên file / hashtag / tiêu đề đánh bóng vẫn đọc ngôn
ngữ + câu thoại từ chính bản chép lời bịa đó. Module này là CỬA CHUNG:
  * `khong_loi(tr)`  — chép lời có phải chữ bịa không (cùng thước co_loi_noi_that)
  * `ngon_ngu(tr, ten_nguon)` — có lời -> y hệt `recap.resolve_lang` cũ (bất
    biến); không lời -> đoán theo TÊN FILE GỐC (chữ người đăng đặt).
  * `tieu_de_tu_ten(ten_nguon)` — tên file gốc đã làm sạch, dùng làm tiêu đề
    lùi thay cho "câu thoại đầu" (vốn là chữ bịa).
Hàm thuần, không bao giờ ném.
"""
from __future__ import annotations

import os
import re


def _do_dai(tr: dict) -> float:
    try:
        d = float((tr or {}).get("duration") or 0)
    except (TypeError, ValueError):
        d = 0.0
    if d > 0:
        return d
    segs = (tr or {}).get("segments") or []
    try:
        return float(segs[-1].get("end") or 0) if segs else 0.0
    except (TypeError, ValueError, AttributeError):
        return 0.0


def khong_loi(tr: dict) -> bool:
    """True = bản chép lời là chữ Whisper BỊA (video không có lời nói thật).
    Chép lời rỗng/không có -> False (không có gì để nghi; giữ hành vi cũ)."""
    tr = tr or {}
    if not (tr.get("segments") or tr.get("text")):
        return False
    dur = _do_dai(tr)
    if dur <= 0:
        return False
    try:
        from app.ai import chon_doan
        co, _ly, _md = chon_doan.co_loi_noi_that(tr, dur)
        return not co
    except Exception:  # noqa: BLE001
        return False


def _ten_goc(ten_nguon: str) -> str:
    s = os.path.splitext(os.path.basename(str(ten_nguon or "")))[0]
    return s


def tieu_de_tu_ten(ten_nguon: str, limit: int = 60) -> str:
    """Tên file gốc -> tiêu đề gọn: bỏ #hashtag, mã [id]/(1), gạch dưới."""
    s = _ten_goc(ten_nguon)
    s = re.sub(r"#\S+", " ", s)
    s = re.sub(r"\[[^\]]*\]|\([0-9]+\)", " ", s)
    s = s.replace("_", " ")
    s = " ".join(s.split()).strip(" -–·.")
    if len(s) > limit:
        cut = s[:limit]
        sp = cut.rfind(" ")
        s = (cut[:sp] if sp > limit * 0.5 else cut).rstrip(" ,-–")
    return s


def ngon_ngu_ten(ten_nguon: str) -> str:
    """Ngôn ngữ đoán từ TÊN FILE gốc: chữ phi-Latin -> theo chữ viết; Latin có
    dấu Việt -> 'vi'; Latin còn lại -> 'en'; tên rỗng -> ''."""
    from app.ai import recap
    s = tieu_de_tu_ten(ten_nguon, limit=400)
    if not re.search(r"[^\W\d_]", s):
        return ""
    by = recap.detect_lang_by_script(s)
    if by:
        return by
    if recap.looks_vietnamese(s):
        return "vi"
    return "en"


def ngon_ngu(tr: dict, ten_nguon: str = "") -> str:
    """Ngôn ngữ đáng tin của video. Có lời -> y hệt recap.resolve_lang (bất
    biến). Không lời + có tên file -> theo tên file."""
    from app.ai import recap
    tr = tr or {}
    goc = recap.resolve_lang(tr.get("language", "") or "", tr.get("text", "") or "")
    if ten_nguon and khong_loi(tr):
        return ngon_ngu_ten(ten_nguon) or goc
    return goc


def dau_vao_hashtag(tr: dict, ten_nguon: str, title: str, text: str,
                    lang: str) -> tuple:
    """(title, text, lang, nguon) để sinh hashtag. Video không lời -> KHÔNG
    đưa chữ bịa cho AI: lấy tên file gốc làm nội dung, ngôn ngữ theo tên file;
    nguon='ten' để bộ nhớ đệm hashtag cũ (sinh từ chữ bịa) bị sinh lại.
    Video có lời -> trả nguyên đầu vào, nguon='' (bất biến)."""
    if ten_nguon and khong_loi(tr):
        ten = tieu_de_tu_ten(ten_nguon, limit=200)
        return (ten, ten, ngon_ngu_ten(ten_nguon) or lang, "ten")
    return (title, text, lang, "")


def hop_ngon_ngu(tieu_de: str, lang: str) -> bool:
    """Tiêu đề có viết bằng CHỮ của ngôn ngữ `lang` không (soi chữ viết, rẻ).
    en: chỉ chữ ASCII (Na Uy 'å/ø', Đức 'ß', Việt có dấu -> trượt) · vi: trông
    Việt · chữ phi-Latin: đúng hệ chữ. Ngôn ngữ Latin khác: không kết luận."""
    from app.ai import recap
    t = str(tieu_de or "").strip()
    if not t:
        return False
    la = str(lang or "").strip().lower()
    la = getattr(recap, "_LANG_ALIAS", {}).get(la, la)
    if la == "en":
        return all(ord(ch) < 128 or not ch.isalpha() for ch in t)
    if la == "vi":
        return recap.looks_vietnamese(t)
    if la in ("ja", "ko", "zh", "th", "ru", "ar", "hi", "he"):
        return recap.detect_lang_by_script(t) == la
    return False


def cung_ngon_ngu(a: str, b: str) -> bool:
    from app.ai import recap
    ali = getattr(recap, "_LANG_ALIAS", {})

    def _n(x):
        x = str(x or "").strip().lower()
        return ali.get(x, x)
    return bool(_n(a)) and _n(a) == _n(b)
