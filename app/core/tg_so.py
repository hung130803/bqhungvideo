# -*- coding: utf-8 -*-
"""SỔ TRẠNG THÁI THAY GIỌNG — nhớ VIDEO NÀO ĐÃ XONG, lưu RA ĐĨA.

Anh Hùng: *"ấn chạy chỉ chạy những video CHƯA chạy xong thôi, cái nào xong rồi
thì ấn chạy không chạy nữa, trừ khi muốn làm lại"*.

VÌ SAO PHẢI GHI RA ĐĨA, KHÔNG ĐƯỢC ĐỂ Ở RAM (bẫy đã gặp thật, xem
"pipeline-ram-only-needs-resume"): app tự cập nhật / tắt máy giữa chừng là mất
sạch sổ -> lượt sau chạy lại từ đầu 300 video đã xong. Sổ nằm ở
`DATA_DIR/thay_giong_so.json`, ghi kiểu THAY NGUYÊN FILE (`os.replace`) nên
không bao giờ đọc phải file viết dở.

KHOÁ THEO (đường dẫn + CỠ + mtime) — y cách `che_chu._khoa_video` nhớ dải chữ.
Chỉ theo tên là sai: anh Hùng thay video khác cùng tên vào thư mục thì app đọc
lại trạng thái của bản CŨ rồi bỏ qua, không một dòng báo. Sổ vẫn giữ THÊM
đường dẫn thường (`_theo_duong`) để trả lời được câu "file này đổi rồi, trước
đó nó thế nào" và để dọn mục cũ khi làm lại.

KHÔNG BAO GIỜ NÉM LỖI: sổ hỏng/đĩa đầy thì coi như CHƯA BIẾT GÌ (video sẽ chạy
lại) — thà làm thừa còn hơn bỏ sót video chưa làm.
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

import config

#: Tên file sổ. Đặt trong DATA_DIR (test trỏ `BQ_DATA_DIR` sang thư mục tạm
#: nên KHÔNG bao giờ đụng sổ thật của anh Hùng).
TEN_SO = "thay_giong_so.json"

#: Trạng thái hợp lệ. "loi" CỐ Ý không tính là đã xong -> lượt Chạy sau TỰ
#: LÀM LẠI (anh Hùng: "nếu cái nào phân tích thay lỗi phải có mục CHẠY LẠI").
XONG = "xong"
LOI = "loi"
BO_QUA = "bo_qua"          # user chuột phải chọn "Bỏ qua video này"

#: Nhãn TIẾNG VIỆT của 9 bước — KHÔNG EMOJI (máy anh Hùng thiếu font).
#: BƯỚC 7 "Đang đọc nhanh" THÊM Ở v2.27.0 cùng lúc với `doc_nhanh_vua_khung`.
#: Thiếu nó thì lời nhắn *"Đọc nhanh lại câu còn dài quá khung..."* rơi vào
#: khoá `"đọc"` = bước 5, tức bảng tiến độ **CHẠY NGƯỢC** (…6/8 "Đang rút gọn"
#: rồi tụt về 5/8 "Đang đọc") — đúng cái anh Hùng nhìn thấy là "chạy lùi/treo".
TEN_BUOC = ("Đang rút tiếng", "Đang tách giọng", "Đang chép lời",
            "Đang dịch", "Đang đọc", "Đang rút gọn", "Đang đọc nhanh",
            "Đang khớp tiếng", "Đang ghép")

_KHOA = threading.RLock()
_NHO: dict = {}            # bản sao trong RAM của file sổ
_MTIME: float = -1.0       # mtime của file lúc nạp -> file đổi thì nạp lại
_DA_NAP = False


def duong_so() -> Path:
    """Đường dẫn file sổ. Đọc `config.DATA_DIR` MỖI LẦN GỌI (không cất sẵn
    vào hằng số): cổng test đổi `BQ_DATA_DIR` rồi nạp lại config, cất sẵn là
    sổ test ghi vào DATA_DIR THẬT của anh Hùng."""
    return Path(config.DATA_DIR) / TEN_SO


def khoa_video(p: str | Path) -> str:
    """`<đường dẫn thường hoá>|<cỡ>|<mtime_ns>` — file mất/không đọc được thì
    chỉ còn phần đường dẫn (vẫn tra được, chỉ là không chắc bằng)."""
    try:
        d = str(Path(p).resolve()).lower()
    except OSError:
        d = str(p).lower()
    try:
        st = os.stat(str(p))
        return f"{d}|{st.st_size}|{st.st_mtime_ns}"
    except OSError:
        return f"{d}|?|?"


def _duong(p: str | Path) -> str:
    try:
        return str(Path(p).resolve()).lower()
    except OSError:
        return str(p).lower()


def _nap(bat_buoc: bool = False) -> dict:
    """Nạp sổ từ đĩa nếu file đổi (hoặc chưa nạp lần nào)."""
    global _MTIME, _DA_NAP
    f = duong_so()
    try:
        mt = f.stat().st_mtime
    except OSError:
        mt = -1.0
    if _DA_NAP and not bat_buoc and mt == _MTIME:
        return _NHO
    _NHO.clear()
    try:
        d = json.loads(f.read_text(encoding="utf-8") or "{}")
        if isinstance(d, dict):
            for k, v in (d.get("muc") or {}).items():
                if isinstance(v, dict):
                    _NHO[str(k)] = v
    except (OSError, ValueError):
        pass                      # sổ hỏng/chưa có -> coi như chưa biết gì
    _MTIME = mt
    _DA_NAP = True
    return _NHO


def nap_lai() -> dict:
    """Ép đọc lại từ đĩa — dùng để GIẢ LẬP TẮT APP rồi mở lại trong cổng test."""
    with _KHOA:
        return dict(_nap(bat_buoc=True))


def _ghi_dia() -> None:
    """Ghi cả sổ ra đĩa kiểu thay-nguyên-file. Lỗi thì im lặng (không được
    làm chết lượt chạy chỉ vì không ghi được sổ)."""
    global _MTIME
    f = duong_so()
    tam = f.with_suffix(".json.tmp")
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        tam.write_text(
            json.dumps({"phien_ban": 1, "muc": _NHO}, ensure_ascii=False,
                       indent=1), encoding="utf-8")
        os.replace(str(tam), str(f))
        _MTIME = f.stat().st_mtime
    except OSError:
        try:
            tam.unlink()
        except OSError:
            pass


def ghi(video: str | Path, trang_thai: str, **thong_tin) -> dict:
    """Ghi trạng thái MỘT video. Trả về đúng mục vừa ghi."""
    with _KHOA:
        _nap()
        muc = {"trang_thai": str(trang_thai),
               "duong": _duong(video),
               "ten": Path(str(video)).name,
               "luc": round(time.time(), 3)}
        for k, v in thong_tin.items():
            muc[k] = v
        _NHO[khoa_video(video)] = muc
        _ghi_dia()
        return dict(muc)


def tra(video: str | Path) -> dict:
    """Mục của video (rỗng = CHƯA BIẾT).

    Tra theo khoá ĐẦY ĐỦ (đường dẫn + cỡ + mtime). File đã đổi = khoá khác =
    coi như CHƯA LÀM — đúng ý: anh Hùng thay file mới cùng tên vào thì phải
    chạy lại, không được đọc trạng thái của bản cũ.
    """
    with _KHOA:
        _nap()
        k = khoa_video(video)
        m = _NHO.get(k)
        if m:
            return dict(m)
        return {}


def tra_theo_duong(video: str | Path) -> dict:
    """Mục GẦN NHẤT theo ĐƯỜNG DẪN, bất kể cỡ/mtime — để hiện "file đã đổi,
    lần trước làm lúc ...". KHÔNG dùng cho quyết định bỏ qua."""
    with _KHOA:
        _nap()
        d = _duong(video)
        ra: dict = {}
        for m in _NHO.values():
            if m.get("duong") == d and m.get("luc", 0) >= ra.get("luc", -1):
                ra = m
        return dict(ra)


def da_xong(video: str | Path) -> bool:
    """True = ĐÃ LÀM XONG video này (đúng file này) -> lượt Chạy BỎ QUA."""
    return tra(video).get("trang_thai") == XONG


def bo_qua(video: str | Path) -> bool:
    """True = user CHỦ ĐỘNG bảo bỏ qua (chuột phải -> Bỏ qua video này)."""
    return tra(video).get("trang_thai") == BO_QUA


def can_chay(video: str | Path) -> bool:
    """Video có cần chạy trong lượt Chạy thường không.

    CHỐT CỦA VIỆC 3 — cửa DUY NHẤT quyết định "bỏ qua hay không". Lỗi thì
    CHẠY LẠI (lỗi ≠ đã xong).
    """
    return tra(video).get("trang_thai") not in (XONG, BO_QUA)


def xoa(video: str | Path) -> int:
    """Quên mọi mục của video này (chuột phải -> Làm lại video này).

    Xoá theo ĐƯỜNG DẪN chứ không theo khoá đầy đủ: có mục cũ của bản file
    trước thì cũng dọn luôn, không để rác tích lại theo 300 kênh.
    """
    with _KHOA:
        _nap()
        d = _duong(video)
        bo = [k for k, m in _NHO.items() if m.get("duong") == d]
        for k in bo:
            _NHO.pop(k, None)
        if bo:
            _ghi_dia()
        return len(bo)


def xoa_nhieu(videos) -> int:
    """Quên nhiều video một lượt (chuột phải -> Làm lại tất cả)."""
    with _KHOA:
        _nap()
        ds = {_duong(v) for v in videos}
        bo = [k for k, m in _NHO.items() if m.get("duong") in ds]
        for k in bo:
            _NHO.pop(k, None)
        if bo:
            _ghi_dia()
        return len(bo)


def tom_tat(videos) -> dict:
    """Đếm nhanh cho nhãn UI: {xong, loi, bo_qua, chua}."""
    ra = {"xong": 0, "loi": 0, "bo_qua": 0, "chua": 0}
    for v in videos:
        tt = tra(v).get("trang_thai")
        if tt == XONG:
            ra["xong"] += 1
        elif tt == LOI:
            ra["loi"] += 1
        elif tt == BO_QUA:
            ra["bo_qua"] += 1
        else:
            ra["chua"] += 1
    return ra


def don_muc_mat_file(gioi_han: int = 5000) -> int:
    """Dọn mục trỏ tới file KHÔNG CÒN trên đĩa khi sổ quá to.

    Chỉ chạy khi sổ vượt `gioi_han` mục — 300 kênh chạy cả năm mới tới đó, và
    dọn sớm là mất trạng thái của video anh Hùng tạm rút ổ cứng ra.
    """
    with _KHOA:
        _nap()
        if len(_NHO) <= gioi_han:
            return 0
        bo = [k for k, m in _NHO.items()
              if not os.path.exists(str(m.get("duong") or ""))]
        for k in bo:
            _NHO.pop(k, None)
        if bo:
            _ghi_dia()
        return len(bo)


def thu_muc_dich_mac_dinh(thu_muc_nguon: str | Path) -> str:
    """`<thư mục nguồn>\\_da_thay_tieng` — dùng khi user để trống ô Thư mục đích.

    Đặt ở đây (không ở UI) để job handler và UI dùng CHUNG một quy tắc: hai
    bên đoán khác nhau là file ra nằm chỗ user không ngờ.
    """
    return str(Path(thu_muc_nguon) / "_da_thay_tieng")


def trung_thu_muc(nguon: str | Path, dich: str | Path) -> bool:
    """Nguồn và đích có là MỘT chỗ không (ghi đè mất gốc).

    So bằng `os.path.normcase(realpath)` — `D:\\a` và `d:\\a\\` và lối tắt
    junction đều phải nhận ra là một.
    """
    try:
        a = os.path.normcase(os.path.realpath(str(nguon)))
        b = os.path.normcase(os.path.realpath(str(dich)))
    except OSError:
        return False
    return bool(a) and a == b


def duong_ra(video: str | Path, thu_muc_dich: str | Path) -> str:
    """Chỗ đặt video MỚI: giữ NGUYÊN tên file gốc, chỉ đổi thư mục."""
    return str(Path(thu_muc_dich) / Path(str(video)).name)


# ══════════════════════════════════════════════════════════════════════
# ƯỚC LƯỢNG CHI PHÍ GIỌNG TRẢ PHÍ (ElevenLabs) — TIỀN CỦA ANH HÙNG
# ══════════════════════════════════════════════════════════════════════
# Thay giọng chạy CẢ THƯ MỤC, mỗi video hàng nghìn ký tự, mà gói free chỉ
# **10.000 ký tự/tháng/tài khoản** (đang xoay 5 tài khoản ≈ 50.000). Vài video
# là cạn. Nên phải nói TRƯỚC khi chạy, đừng để hết giữa mẻ rồi mới biết.
#
#: Ký tự BẢN DỊCH trên MỘT PHÚT phim — **SỐ ĐO, không phải ước bừa**: bản dịch
#: thật của video `近期热播的7部新片推荐…mp4` (`_do_dich_soat.json`) ra **2.275
#: ký tự / 50 câu** cho **107,24 giây** phim = 1.273 ký tự/phút.
#: Đây là ƯỚC LƯỢNG chứ không phải con số chắc: video nói dày/thưa lệch nhau
#: nhiều, nên mọi chỗ hiện số này phải ghi rõ chữ "ước lượng".
#:
#: VÀ NÓ LÀ **SÀN DƯỚI**, không phải số cuối: bước 4b `rut_gon_vua_khung` và
#: 4c `doc_nhanh_vua_khung` ĐỌC LẠI những câu tràn khung, mỗi lượt đọc lại là
#: một lượt tính tiền nữa. Con số ở đây chỉ đếm LƯỢT ĐỌC ĐẦU. Vì vậy câu cảnh
#: báo phải nói "ít nhất", đừng hứa là đủ.
KY_TU_MOI_PHUT = 1273

#: Chỉ đo độ dài THẬT của tối đa ngần này video rồi suy ra cho cả mẻ. Đo hết
#: 300 video là 300 lượt `ffprobe` ngay lúc user vừa bấm Chạy — hộp thoại đứng
#: hàng chục giây. Lấy mẫu rồi nhân là đủ cho một con số CẢNH BÁO.
MAU_DO_DAI_TOI_DA = 12


def uoc_ky_tu(videos, do_dai_giay=None) -> dict:
    """Ước lượng số ký tự ElevenLabs cần cho cả mẻ `videos`.

    `do_dai_giay(path) -> float` là hàm đo độ dài (tiêm vào để test được mà
    không cần ffprobe/file thật). None -> tự dùng `dubbing.probe_duration`.

    Trả {so_video, mau, giay_tb, tong_giay, ky_tu, uoc_luong=True}. Không đo
    được video nào -> `giay_tb=0` và `ky_tu=0` kèm `khong_do_duoc=True`; nơi
    gọi phải nói thẳng "không ước lượng được" chứ ĐỪNG hiện 0 như thể miễn phí.
    """
    ds = [str(v) for v in (videos or [])]
    if not ds:
        return {"so_video": 0, "mau": 0, "giay_tb": 0.0, "tong_giay": 0.0,
                "ky_tu": 0, "uoc_luong": True, "khong_do_duoc": False}
    if do_dai_giay is None:
        from app.core.dubbing import probe_duration as do_dai_giay
    mau = ds[:MAU_DO_DAI_TOI_DA]
    giay = []
    for p in mau:
        try:
            d = float(do_dai_giay(p) or 0)
        except Exception:  # noqa: BLE001
            d = 0.0
        if d > 0:
            giay.append(d)
    if not giay:
        return {"so_video": len(ds), "mau": len(mau), "giay_tb": 0.0,
                "tong_giay": 0.0, "ky_tu": 0, "uoc_luong": True,
                "khong_do_duoc": True}
    tb = sum(giay) / len(giay)
    tong = tb * len(ds)
    return {"so_video": len(ds), "mau": len(giay), "giay_tb": round(tb, 1),
            "tong_giay": round(tong, 1),
            "ky_tu": int(round(tong / 60.0 * KY_TU_MOI_PHUT)),
            "uoc_luong": True, "khong_do_duoc": False}


def _so(n) -> str:
    """12345 -> '12.345' (kiểu Việt). Tách riêng để phép thay dấu KHÔNG chạm
    vào phần chữ của câu."""
    return f"{int(n):,}".replace(",", ".")


def loi_chi_phi(uoc: dict, con_lai) -> str:
    """Câu cảnh báo chi phí (tiếng Việt, KHÔNG emoji) — '' nếu không cần lo.

    `con_lai` = tổng ký tự còn lại trên mọi key, hoặc None khi KHÔNG đọc được
    hạn mức (mạng/không key). None **KHÔNG** được coi là "còn nhiều": nói
    thẳng là không đọc được.
    """
    if uoc.get("khong_do_duoc"):
        return ("Không đo được độ dài video nên KHÔNG ước lượng được số ký "
                "tự sẽ tiêu. Cứ chạy thì có thể hết hạn mức giữa chừng.")
    can = int(uoc.get("ky_tu") or 0)
    n = int(uoc.get("so_video") or 0)
    # `.replace(",", ".")` phải áp lên RIÊNG con số. Áp lên cả câu thì nó nuốt
    # luôn dấu phẩy của tiếng Việt ("Mẻ này 20 video, ước lượng" -> "video.").
    dau = (f"Giọng ElevenLabs tính tiền theo KÝ TỰ. Mẻ này {n} video, ước "
           f"lượng cần ÍT NHẤT khoảng {_so(can)} ký tự (chưa tính các câu "
           f"phải đọc lại cho vừa khung)")
    if con_lai is None:
        return (dau + ", nhưng KHÔNG đọc được hạn mức còn lại (mạng lỗi hoặc "
                "chưa cắm key). Chạy tiếp là chạy mò.")
    conl = _so(con_lai)
    if can > con_lai:
        thieu = _so(can - int(con_lai))
        return (dau + f"; hạn mức còn {conl} ký tự — THIẾU khoảng {thieu}.\n\n"
                "Chạy tiếp thì tới lúc hết hạn mức app sẽ TỰ LÙI về giọng "
                "edge-tts cho các video còn lại (video vẫn ra, chỉ khác "
                "giọng) và ghi rõ video nào bị lùi trong nhật ký.")
    return (dau + f"; hạn mức còn {conl} ký tự — đủ dùng.")


def loi_doc_hieu(tho: str) -> str:
    """Đổi lỗi thô (mã lỗi/exception) thành LÝ DO ĐỌC HIỂU ĐƯỢC.

    Anh Hùng đọc bảng này, không đọc traceback. Không khớp mẫu nào thì trả
    lại nguyên văn (cắt ngắn) — thà khó hiểu còn hơn giấu mất lỗi thật.
    """
    t = (tho or "").strip()
    if not t:
        return ""
    s = t.lower()
    cap = (
        ("demucs", "Máy chưa có bộ tách giọng — bấm nút Tải bộ tách giọng."),
        ("torch", "Máy chưa có bộ tách giọng — bấm nút Tải bộ tách giọng."),
        ("không chép được câu nào",
         "Video không có lời thoại để thay (chỉ nhạc/tiếng động)."),
        ("không câu nào khớp được",
         "Không khớp được câu nào vào khung thời gian của video."),
        ("không thấy video", "Không tìm thấy file video (đã bị di chuyển?)."),
        ("cancel", "Bạn đã bấm Dừng."),
        ("huy", "Bạn đã bấm Dừng."),
        ("hủy", "Bạn đã bấm Dừng."),
        ("rate_limit", "Hết lượt AI — đợi vài phút rồi bấm Chạy lại."),
        ("429", "Hết lượt AI — đợi vài phút rồi bấm Chạy lại."),
        ("too large", "Đoạn quá dài cho AI — chạy lại để app chia nhỏ."),
        ("413", "Đoạn quá dài cho AI — chạy lại để app chia nhỏ."),
        ("503", "Máy chủ AI đang quá tải — chạy lại sau."),
        ("noaudioreceived",
         "Không tải được giọng đọc (mạng chập chờn) — chạy lại."),
        ("edge", "Không tải được giọng đọc (mạng chập chờn) — chạy lại."),
        ("winerror 32",
         "File đang bị chương trình khác mở — đóng trình phát rồi chạy lại."),
        ("being used by another process",
         "File đang bị chương trình khác mở — đóng trình phát rồi chạy lại."),
        ("winerror 5", "Không có quyền ghi vào thư mục đích."),
        ("permission", "Không có quyền ghi vào thư mục đích."),
        ("no space", "Ổ đĩa đã đầy."),
        ("errno 28", "Ổ đĩa đã đầy."),
        ("trùng thư mục",
         "Thư mục nguồn và thư mục đích TRÙNG nhau — chọn thư mục đích khác."),
        ("0 kib", "File video mới hỏng (rỗng) — video gốc giữ nguyên."),
        ("không hợp lệ", "File video mới không hợp lệ — video gốc giữ nguyên."),
        ("ffmpeg", "Lỗi ghép video (ffmpeg) — xem nhật ký."),
        ("timeout", "Quá lâu không xong — mạng hoặc máy đang quá tải."),
        ("connection", "Mất mạng khi gọi AI — chạy lại."),
    )
    for dau, loi in cap:
        if dau in s:
            return loi
    return t[:160]


def buoc_tu_tien_trinh(p: float, loi_nhan: str = "") -> tuple:
    """(nhãn trạng thái, số bước, tổng bước) theo tiến trình + lời nhắn THẬT.

    Vì sao đọc CẢ HAI: lời nhắn là sự thật rõ nhất (`thay_giong_video` đặt
    tên từng bước), nhưng lúc bộ tách giọng chạy nó bị lời nhắn con của Demucs
    thay chỗ -> lúc đó dựa vào KHOẢNG tiến trình (mỗi bước một khoảng cố định
    trong `thay_giong_video`). Đặt ở đây, không ở UI, để cổng test đo được
    thẳng hàm này.
    """
    m = (loi_nhan or "").lower()
    # THỨ TỰ NÀY LÀ MỘT PHÉP ĐO, ĐỪNG SẮP LẠI CHO "gọn": lời nhắn bước 5 là
    # *"Đọc bản dịch..."* — nó CHỨA chữ "dịch" nên nếu ("dịch", 4) đứng trước
    # thì bước ĐỌC hiện thành "Đang dịch" và bảng KHÔNG BAO GIỜ hiện "Đang
    # đọc" (cổng 57 mục 1 bắt được đúng lỗi này). Cụm DÀI/RIÊNG phải xét
    # trước cụm ngắn dùng chung chữ.
    khoa = (
        ("rút tiếng", 1), ("rut tieng", 1),
        ("tách giọng", 2), ("tach giong", 2), ("demucs", 2),
        ("chép lời", 3), ("chep loi", 3),
        # "đọc nhanh" PHẢI đứng TRƯỚC "đọc" — cùng luật đã ghi ở trên, lần này
        # ở chiều nguy hiểm hơn: bước 7 nằm SAU bước 6, gán nhầm về 5 thì
        # thanh tiến độ CHẠY NGƯỢC chứ không chỉ sai chữ.
        ("đọc nhanh", 7), ("doc nhanh", 7),
        ("đọc", 5), ("doc ban dich", 5),        # TRƯỚC "dịch" — xem trên
        ("rút gọn", 6), ("rut gon", 6),
        ("dịch", 4), ("dich ", 4),
        ("khớp thời gian", 8), ("khop thoi gian", 8),
        ("trộn tiếng", 9), ("tron tieng", 9),
        ("ghép tiếng", 9), ("ghep tieng", 9),
    )
    b = 0
    for dau, so in khoa:
        if dau in m:
            b = so
            break
    if not b:                       # lời nhắn lạ -> suy theo KHOẢNG tiến trình
        # Các mốc này lấy THẲNG từ `thay_giong_video` (0.02 · 0.06 · 0.32 ·
        # 0.44 · 0.62 · 0.74 · 0.79 · 0.80 · 0.91). Đổi mốc trong đó mà quên
        # bảng này thì bảng tiến độ sai IM LẶNG.
        moc = ((0.06, 1), (0.32, 2), (0.44, 3), (0.62, 4), (0.74, 5),
               (0.79, 6), (0.80, 7), (0.91, 8), (1.01, 9))
        b = len(TEN_BUOC)
        for tran, so in moc:
            if p < tran:
                b = so
                break
    return (TEN_BUOC[b - 1], b, len(TEN_BUOC))
