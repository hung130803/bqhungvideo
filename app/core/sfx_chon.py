# -*- coding: utf-8 -*-
"""CHỌN TIẾNG ĐỘNG **HỢP LÝ** — ÍT MÀ ĐÚNG CHỖ (02/11/2026). Hàm THUẦN.

Anh Hùng: *"giờ có vài kiểu ít quá mà đơn điệu ... mà nó thêm nhiều đoạn cũng
buồn cười nữa"*. ĐO TRÊN NHẬT KÝ DÂY CHUYỀN THẬT (22/10-02/11/2026, 1.317 Part,
5.160 lượt chèn — `_NGHE_THU_ANH_HUNG/sfx_moi/SO_DO.txt`):

  * 70/97 kiểu hiệu ứng hình **KHÔNG có trong bảng kiểu -> tiếng** nên rơi về
    'impact' mặc định -> `impact` chiếm **57%** mọi tiếng, kể cả ở các kiểu chỉ
    CHỈNH MÀU dịu (`mau_am_diu`) hay tuyết rơi = một cú "keng" thuỷ tinh giữa
    cảnh êm. Đúng chữ "vô duyên".
  * 1 Part có tới **17** tiếng; 341 cặp tiếng cách nhau **< 2 giây**.
  * Chỗ nối GẦN LIỀN MẠCH (nhảy <= 1,2 s, hình gần như không đổi) vẫn chèn tiếng.
  * 49% Part có >= 2 tiếng CÙNG HỌ (xử lý ở bộ bốc file, `ffmpeg_utils`).

Module này nhận DANH SÁCH ỨNG VIÊN mốc (điểm nối + điểm nhấn) rồi quyết định
GIỮ mốc nào, loại tiếng gì — theo 5 luật, mỗi luật có lý do trong mã:
  1. Bảng kiểu hiệu ứng -> tiếng ĐẦY ĐỦ; kiểu chỉ là tông màu/hạt/mưa = KHÔNG
     tiếng (`None`).
  2. Chỗ nối 'pop' (gần liền mạch) KHÔNG chèn.
  3. Ngân sách mật độ theo độ dài clip + khoảng cách tối thiểu; quá ngân sách
     thì giữ mốc QUAN TRỌNG hơn (hook > cao trào > nối đổi cảnh).
  4. Không 3 tiếng CÙNG NHÓM liền nhau; comedy tối đa 1/clip.
  5. NGỮ CẢNH LỜI THOẠI: câu đang nói là chuyện NẶNG (chết, tai nạn, khóc...)
     thì bỏ tiếng vui/ding/pop; câu đang cười thì cú nhấn đổi sang comedy.

KHÔNG đụng: đường `edit_plan`/`story_beats` (dựng chuyện có kế hoạch riêng) và
thư mục tiếng động RIÊNG của user. `BQ_SFX_CU=1` -> trả nguyên danh sách cũ.
"""
from __future__ import annotations

import math
import os
import re
import unicodedata
from typing import Optional

#: Luật 1 — KIỂU HIỆU ỨNG HÌNH -> NHÓM TIẾNG. `None` = kiểu này KHÔNG cần tiếng
#: (chỉnh màu, hạt phim, thời tiết, ánh sáng dịu): chèn cú nhấn vào đó chính là
#: "chèn chỗ không hợp". Khoá phải phủ ĐỦ `hieu_ung.KHO` — cổng 105 kiểm.
BANG_HIEU_UNG: dict = {
    # dời chỗ / va đập
    "zoom_nhoi": "impact", "rung_lac": "impact", "meo_kinh": "impact",
    "rung_xoay": "impact", "meo_kinh_tt": "impact", "tuong_phan": "impact",
    "sh_tuong_phan": "impact",
    # chuyển động nhanh -> tiếng vút (whip pan)
    "zoom_day": "riser", "zoom_lui": "transition", "luot_ngang": "transition",
    "luot_doc": "transition", "xien_hinh": "transition",
    "phoi_canh": "transition", "truot_hinh": "transition",
    "mo_huong": "transition",
    # lộ ra / sáng
    "loe_sang": "reveal", "nhay_sang": "riser",
    # tối / nén
    "sup_toi": "suspense", "song_meo": "suspense",
    # vỡ hình / nhiễu số
    "o_vuong": "scratch", "xao_dong": "scratch", "glitch_khoi": "scratch",
    "lech_bang": "scratch", "nhieu_analog": "scratch", "xao_khoi": "scratch",
    "xao_doc": "scratch", "doi_o": "scratch", "xe_dong": "scratch",
    # mờ nhanh -> tiếng chạm nhẹ
    "mo_net": "pop", "mo_vuong": "pop", "mo_khoi_tt": "pop",
    # chữ
    "dem_nguoc": "drumroll",
    # MOOD / chỉnh màu / hạt / viền: KHÔNG tiếng
    "quang_sang": None, "hat_phim": None, "hat_nhieu": None,
    "sh_hat_phim": None, "toi_vien": None, "sh_toi_vien": None,
    "vien_phim": None, "vien_net": None, "dong_quet": None,
    "nghieng_may": None, "bac_sang": None,
    "nhay_don_mem": None, "nhip_sang_doi": None,
    "mau_am_diu": None, "mau_lanh_diu": None, "mau_phim_cu": None,
    "mau_don_sac": None, "mau_ruc_nhe": None, "mau_pastel": None,
    # LỚP PHỦ HẠT: chỉ kiểu có "sự kiện" mới kêu
    "lap_lanh": "reveal", "lap_lanh_bui": "reveal", "lap_lanh_sao": "reveal",
    "lap_lanh_vang": "reveal", "tuyet_tinh_the": "reveal",
    "la_kim_tuyen": "reveal", "tien_roi": "reveal", "xu_vang": "reveal",
    "confetti": "reveal", "confetti_dai": "reveal", "confetti_no": "reveal",
    "phao_hoa": "reveal", "bong_bay": "reveal",
    "trai_tim": "pop", "trai_tim_nho": "pop", "bong_bong": "pop",
    "trai_tim_vo": "sad", "dom_ma": "suspense",
    "tuyet_roi": None, "tuyet_bui": None, "tuyet_bao": None,
    "mua_roi": None, "mua_rao": None, "mua_bui": None, "giot_kinh": None,
    "dom_bokeh": None, "bokeh_nho": None, "den_nhap_nhay": None,
    "tan_lua": None, "tan_lua_day": None, "tan_tro": None,
    "tia_sang": None, "tia_sang_doc": None, "nang_xuyen": None,
    "bui_phim": None, "bui_bay": None, "xuoc_phim": None,
    "la_roi": None, "la_bay": None, "canh_hoa": None, "khoi_bay": None,
    "bot_nuoc": None, "song_nuoc": None, "suong_mo": None,
    "hat_so": None, "luoi_so": None,
}

#: Kiểu hiệu ứng LẠ (bản sau thêm kiểu mà quên khai) -> theo NHÓM điểm của nó.
#: Không rơi về 'impact' cho mọi thứ nữa (đó là lỗi 57%).
THEO_LOAI_DIEM = {"hook": "impact", "caotrao": "impact", "dong": "scratch",
                  "noi": "transition", "chot": None, "tinh": None, "ke": None}

#: Luật 3 — ngân sách: 1 tiếng (hook) + 1 tiếng mỗi `GIAY_MOI_TIENG` giây.
#: Đo: trung vị Part hiện tại 3 tiếng (đúng mức này cho clip 30-45 s); đuôi
#: dài 7-17 tiếng toàn ở clip 60-140 s nhiều điểm nối = chỗ "thêm nhiều quá".
GIAY_MOI_TIENG = 15.0
TOI_THIEU, TOI_DA = 2, 6
#: Hai tiếng gần nhau hơn mức này thì bỏ cái kém quan trọng. Cũ: 0,8 s (đo:
#: 341 cặp < 2 s = tiếng nọ chưa tắt tiếng kia đã vào, nghe "rào rào").
CACH_MIN = 2.0

#: Luật 3 — độ ưu tiên (cao giữ trước). Mốc hook luôn giữ.
UU_TIEN_HOOK = 100

_NANG = (
    # tiếng Việt CÓ DẤU (so trên chữ thường)
    "qua đời", "tử vong", "thiệt mạng", "đã mất", "đã chết", "bị giết",
    "tai nạn", "ung thư", "đám tang", "tang lễ", "nước mắt", "đau buồn",
    "thương tiếc", "hy sinh", "tự tử", "đau lòng", "bi kịch", "mồ côi",
    "bạo hành", "khóc", "chết",
    # tiếng Anh
    "passed away", "died", "death", "dead", "killed", "funeral", "cancer",
    "tragedy", "tragic", "crying", "tears", "suicide", "grief", "mourning",
    "abuse", "murdered",
    # Trung / Nhật (không dấu cách -> dò chuỗi con, mỗi khoá >= 2 ký tự)
    "去世", "死亡", "葬礼", "癌症", "悲剧", "遇难", "哭了",
    "亡くな", "死ん", "葬式", "泣い",
)
#: "chết cười" / "cười chết" là câu VUI — gỡ trước khi dò chuyện nặng.
_NANG_TRU = ("chết cười", "cười chết", "đẹp chết", "chết mê", "to death",
             "dead funny", "dying of laughter")
_VUI = ("haha", "hihi", "hehe", "buồn cười", "chết cười", "cười chết",
        "hài hước", "lol", "lmao", "hilarious", "funny", "laughing",
        "[laughter]", "(laughs)", "哈哈", "笑")


def tat() -> bool:
    """`BQ_SFX_CU=1` -> dùng nguyên cách chọn mốc cũ (để đo A/B / gỡ rối)."""
    return str(os.environ.get("BQ_SFX_CU", "")).strip() in ("1", "true", "yes")


def nhom_cho_hieu_ung(khoa: str, loai_diem: str = "") -> Optional[str]:
    """Kiểu hiệu ứng -> nhóm tiếng hoặc None (không chèn). Hàm thuần."""
    k = str(khoa or "")
    if k in BANG_HIEU_UNG:
        return BANG_HIEU_UNG[k]
    return THEO_LOAI_DIEM.get(str(loai_diem or ""), "impact")


def _chu(s: str) -> str:
    return unicodedata.normalize("NFC", str(s or "")).lower()


def _co(text: str, tu: tuple) -> bool:
    """Dò từ khoá; khoá chữ Latin phải khớp TRỌN TỪ (tránh 'dead' trong
    'deadline', 'khóc' trong ... ) — khoá CJK khớp chuỗi con."""
    for k in tu:
        if re.search(r"[A-Za-zÀ-ỹ]", k):
            if re.search(r"(?<![\wÀ-ỹ])" + re.escape(k) + r"(?![\wÀ-ỹ])",
                         text):
                return True
        elif k in text:
            return True
    return False


def ngu_canh_cau(text: str) -> str:
    """'nang' (chuyện buồn/nghiêm trọng) · 'vui' (đang cười) · '' . Hàm thuần."""
    t = _chu(text)
    if not t:
        return ""
    t_nang = t
    for x in _NANG_TRU:
        t_nang = t_nang.replace(x, " ")
    if _co(t_nang, _NANG):
        return "nang"
    if _co(t, _VUI):
        return "vui"
    return ""


def cau_ra_timeline(transcript: Optional[dict], segs: list,
                    vspeed: float = 1.0) -> list:
    """Câu chép lời (giây NGUỒN) -> [(đầu, cuối, chữ)] trên timeline ĐẦU RA.
    Đoạn có thể NGƯỢC THỜI GIAN (hook-first) nên cộng dồn theo ĐÚNG thứ tự
    `segs`. Câu cắt ngang ranh giới đoạn thì lấy phần giao. Hàm thuần."""
    ra: list = []
    cau = (transcript or {}).get("segments") or []
    if not cau:
        return ra
    v = max(0.01, float(vspeed or 1.0))
    acc = 0.0
    for s, e in segs or []:
        try:
            s, e = float(s), float(e)
        except (TypeError, ValueError):
            continue
        if e <= s:
            continue
        for c in cau:
            try:
                a, b = float(c.get("start")), float(c.get("end"))
            except (TypeError, ValueError, AttributeError):
                continue
            lo, hi = max(a, s), min(b, e)
            if hi > lo:
                ra.append(((acc + lo - s) / v, (acc + hi - s) / v,
                           str(c.get("text") or "")))
        acc += e - s
    return ra


def _ngu_canh_tai(cau: list, t: float) -> str:
    """Ngữ cảnh lời tại giây `t`: câu đang nói chứa mốc (±0,4 s)."""
    kq = ""
    for a, b, chu in cau or []:
        if a - 0.4 <= t <= b + 0.4:
            n = ngu_canh_cau(chu)
            if n == "nang":
                return "nang"
            kq = kq or n
    return kq


def _uu_tien(m: dict) -> int:
    if m.get("loai_diem") == "hook":
        return UU_TIEN_HOOK
    cat, vai = m.get("cat"), m.get("vai")
    if vai == "nối":
        return {"impact": 70, "riser": 60, "reveal": 55}.get(cat, 35)
    if m.get("loai_diem") == "caotrao":
        return 65
    return {"impact": 50, "reveal": 48, "riser": 46, "scratch": 44}.get(cat, 40)


def ngan_sach(dur: float) -> int:
    """Số tiếng TỐI ĐA cho clip dài `dur` giây. Hàm thuần."""
    n = 1 + int(math.ceil(max(0.0, float(dur or 0)) / GIAY_MOI_TIENG))
    return max(TOI_THIEU, min(TOI_DA, n))


def chon_moc(ung_vien: list, dur: float, cau: Optional[list] = None) -> tuple:
    """Lọc ứng viên mốc tiếng động theo 5 luật.

    `ung_vien` = [{'t', 'cat' (nhóm hoặc None), 'vai' ('nối'|'điểm nhấn'),
    'loai_diem', 'khoa'}]. Trả (giữ, bỏ): `giữ` = [(t, cat, vai)] theo thời
    gian (đúng khuôn `_sfx_diem` của `ffmpeg_utils`), `bỏ` = [(t, lý do)] để
    ghi nhật ký. Hàm thuần — test được."""
    bo: list = []
    uv: list = []
    for m in ung_vien or []:
        try:
            t = float(m["t"])
        except (KeyError, TypeError, ValueError):
            continue
        if not (0.0 <= t < float(dur or 0)):
            continue
        cat = m.get("cat")
        if cat is None or cat == "none":
            bo.append((t, "kiểu hình này không cần tiếng"))
            continue
        if m.get("vai") == "nối" and cat == "pop":
            bo.append((t, "chỗ nối gần liền mạch — chèn tiếng là lố"))
            continue
        x = dict(m, t=t)
        # Luật 5 — ngữ cảnh lời thoại
        nc = _ngu_canh_tai(cau or [], t)
        if nc == "nang" and x.get("loai_diem") != "hook":
            if cat in ("comedy", "pop", "reveal", "scratch"):
                bo.append((t, f"đang nói chuyện nặng — bỏ tiếng {cat}"))
                continue
            if cat == "impact":
                x["cat"] = "suspense"
        elif nc == "vui" and cat in ("impact", "pop") and x.get("vai") != "nối":
            x["cat"] = "comedy"
        x["uu"] = _uu_tien(x)
        uv.append(x)
    # Luật 3 — giữ theo độ ưu tiên, tôn trọng khoảng cách + ngân sách
    tran = ngan_sach(dur)
    giu: list = []
    for x in sorted(uv, key=lambda m: (-m["uu"], m["t"])):
        if len(giu) >= tran:
            bo.append((x["t"], f"quá ngân sách {tran} tiếng/clip"))
            continue
        if any(abs(x["t"] - g["t"]) < CACH_MIN for g in giu):
            bo.append((x["t"], f"cách tiếng khác < {CACH_MIN:g}s"))
            continue
        giu.append(x)
    giu.sort(key=lambda m: m["t"])
    # Luật 4 — không 3 tiếng cùng nhóm liền nhau; comedy tối đa 1
    kq: list = []
    co_comedy = False
    for x in giu:
        c = x["cat"]
        if (len(kq) >= 2 and kq[-1]["cat"] == c and kq[-2]["cat"] == c
                and x.get("loai_diem") != "hook"):
            bo.append((x["t"], f"tiếng {c} thứ 3 liên tiếp"))
            continue
        if c == "comedy":
            if co_comedy:
                x["cat"] = "pop"
            co_comedy = True
        kq.append(x)
    return ([(m["t"], m["cat"], m.get("vai", "điểm nhấn")) for m in kq],
            sorted(bo))


def ho_tieng(path: str) -> str:
    """HỌ của một file tiếng: bỏ đuôi số thứ tự và `_vN` (biến thể đổi cao độ
    của CÙNG một tiếng). `impactGlass_light_003_v2.opus` -> `impactGlass_light`.
    Hàm thuần."""
    n = os.path.basename(str(path or ""))
    n = re.sub(r"\.[A-Za-z0-9]+$", "", n)
    n = re.sub(r"_v\d+$", "", n)
    n = re.sub(r"[_]?\d+$", "", n)
    return n.lower()
