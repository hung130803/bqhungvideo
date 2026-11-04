# -*- coding: utf-8 -*-
"""TỰ CHẠY DÂY CHUYỀN — bộ quyết định "nhịp này có chạy không" (INTEGRATION.md
mục 5, sửa 04/11/2026). Hàm THUẦN + đồng hồ truyền vào để test.

Tự chạy KHÔNG viết lại nghiệp vụ: tới nhịp thì main_window gọi ĐÚNG hàm mà nút
▶ / bot Telegram đang gọi (`StudioPage._bot_chay_day_chuyen(nhóm đã lưu)`).
File này chỉ quyết định KHI NÀO.

Luật (mỗi luật một ca test trong `_test_tu_chay.py`):
  - Công tắc mặc định TẮT. Bật ô KHÔNG chạy gì ngay: nhịp đầu tiên rơi vào
    `bây giờ + N phút` (test smoke bấm mọi ô tích).
  - Ngoài khung giờ -> không chạy lượt mới (job đang chạy vẫn làm nốt).
  - Lượt trước còn ĐANG QUÉT hoặc còn file trong HÀNG NHẬN -> BỎ nhịp.
  - Đang mở hộp chọn file hệ thống (`_modal_busy`) -> HOÃN tới khi hộp đóng.
  - Hàng job tạm dừng / thiếu key AI / ổ đầy / DB vỡ -> không chạy + nói lý do
    (không nói lặp mỗi nhịp).
  - Kích thêm 1 lượt 45 giây sau mốc `xong_luc` của video trong phiếu đợt tải,
    khử trùng theo (dot_id, id video).
"""
from __future__ import annotations

import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime

PHUT_MAC_DINH = 10
TU_MAC_DINH = "06:00"
DEN_MAC_DINH = "22:00"
O_VIDEO_GB = 30.0
O_C_GB = 10.0
#: kích theo phiếu: chờ chừng này giây sau `xong_luc` (luật đứng yên 30 s +
#: quan sát 10 s của pipeline, cộng 5 s biên).
KICH_SAU_GIAY = 45
#: mở app lúc đang bật Tự chạy -> lượt đầu sau chừng này giây (để hồi phục
#: dây chuyền chạy xong trước — hồi phục bắt đầu ở giây thứ 4).
LUOT_DAU_GIAY = 120
#: xong_luc cũ hơn chừng này thì KHÔNG kích (mở lại app không bắn dồn).
KICH_BO_CU_GIAY = 600
#: lý do không chạy được nói lại tối đa 1 lần / chừng này giây (V6).
NOI_LAI_GIAY = 3600
#: thời hạn đo dung lượng 1 ổ (ổ mạng chết -> bỏ qua ổ đó, không treo cả lượt).
DO_O_HAN_GIAY = 30

KHOA = "pipe_auto_"     # tiền tố QSettings
#: QSettings .ini có thể đọc chuỗi rỗng thành None -> lưu nhóm rỗng bằng mã này
#: (không thì "Chưa phân nhóm" bị đọc lại thành TẤT CẢ nhóm).
NHOM_CHUA = "__CHUA_PHAN_NHOM__"


def doc_gio(s, mac_dinh: str) -> int:
    """"06:30" -> 390 (phút trong ngày). Sai dạng -> mặc định."""
    for v in (s, mac_dinh):
        try:
            h, m = str(v).strip().split(":")[:2]
            h, m = int(h), int(m)
            if 0 <= h <= 24 and 0 <= m < 60:
                return min(24 * 60, h * 60 + m)
        except (ValueError, AttributeError):
            continue
    return 0


def trong_khung(now: float, tu: int, den: int) -> bool:
    """Giờ máy `now` có nằm trong [tu, den) không. tu > den = khung qua nửa
    đêm (vd 22:00-06:00). tu == den = cả ngày."""
    d = datetime.fromtimestamp(now)
    m = d.hour * 60 + d.minute
    if tu == den:
        return True
    if tu < den:
        return tu <= m < den
    return m >= tu or m < den


@dataclass
class CauHinh:
    bat: bool = False
    tu: int = 6 * 60
    den: int = 22 * 60
    phut: int = PHUT_MAC_DINH
    nhom: object = "__ALL__"
    thu_muc: str = ""
    o_video_gb: float = O_VIDEO_GB
    o_c_gb: float = O_C_GB


def doc_cau_hinh(s) -> CauHinh:
    """Đọc từ QSettings (đối tượng có .value). Thiếu khoá -> mặc định TẮT."""
    def v(k, d, kieu=None):
        try:
            if kieu is None:
                return s.value(KHOA + k, d)
            return s.value(KHOA + k, d, type=kieu)
        except Exception:  # noqa: BLE001
            return d
    nhom = v("nhom", "__ALL__")
    if nhom is None or str(nhom) == "":
        nhom = "__ALL__"
    if str(nhom) == NHOM_CHUA:
        nhom = ""                    # nhóm "Chưa phân nhóm" (grp rỗng)
    try:
        phut = max(1, min(240, int(v("phut", PHUT_MAC_DINH))))
    except (TypeError, ValueError):
        phut = PHUT_MAC_DINH
    try:
        ov = float(v("o_video_gb", O_VIDEO_GB))
        oc = float(v("o_c_gb", O_C_GB))
    except (TypeError, ValueError):
        ov, oc = O_VIDEO_GB, O_C_GB
    return CauHinh(bat=bool(v("bat", False, bool)),
                   tu=doc_gio(v("tu", TU_MAC_DINH), TU_MAC_DINH),
                   den=doc_gio(v("den", DEN_MAC_DINH), DEN_MAC_DINH),
                   phut=phut, nhom=str(nhom), thu_muc=str(v("thu_muc", "") or ""),
                   o_video_gb=ov, o_c_gb=oc)


@dataclass
class TinhTrang:
    """Ảnh chụp trạng thái app lúc tới nhịp (main_window điền, chỉ đọc RAM)."""
    modal_busy: bool = False
    dang_quet: bool = False
    dang_nhan: int = 0
    tam_dung: bool = False
    co_key: bool = True
    db_hong: bool = False
    #: None = chưa đo xong lần nào; (True, "") ổn; (False, "lý do") đầy.
    o_dia: tuple | None = (True, "")


@dataclass
class LichTuChay:
    """Sổ nhịp của Tự chạy (sống trong RAM của MainWindow)."""
    hen: float | None = None          # nhịp thường kế tiếp (epoch)
    kich: dict = field(default_factory=dict)   # (dot_id, id) -> giờ bắn
    da_kich: set = field(default_factory=set)
    da_noi: dict = field(default_factory=dict)  # lý do -> lúc nói gần nhất
    lan_chay: int = 0
    lan_cuoi: float | None = None
    dang_bat: bool = False

    # -- bật/tắt --
    def dong_bo(self, cfg: CauHinh, now: float, luc_mo_app: bool = False) -> None:
        """Gọi mỗi nhịp với cấu hình mới đọc. Vừa BẬT -> hẹn nhịp đầu sau N
        phút (KHÔNG chạy ngay). Mở app lúc đã bật sẵn -> sau LUOT_DAU_GIAY."""
        if cfg.bat and not self.dang_bat:
            cho = LUOT_DAU_GIAY if luc_mo_app else cfg.phut * 60
            self.hen = now + cho
        if not cfg.bat:
            self.hen = None
            self.kich.clear()
        self.dang_bat = cfg.bat

    def them_kich(self, dot_id: str, vid: str, xong_ts: float, now: float) -> bool:
        """Phiếu tải ghi `xong` -> hẹn 1 lượt ở xong_ts + 45 s. Khử trùng theo
        (dot_id, id). xong_ts quá cũ (mở lại app) -> bỏ, nhịp thường lo."""
        k = (str(dot_id), str(vid))
        if k in self.da_kich:
            return False
        self.da_kich.add(k)
        if now - xong_ts > KICH_BO_CU_GIAY:
            return False
        self.kich[k] = xong_ts + KICH_SAU_GIAY
        return True

    def _toi_kich(self, now: float) -> bool:
        return any(t <= now for t in self.kich.values())

    def nen_noi(self, ly_do: str, now: float) -> bool:
        """Lý do không chạy được: chỉ nói lại sau NOI_LAI_GIAY (V6)."""
        t = self.da_noi.get(ly_do)
        if t is not None and now - t < NOI_LAI_GIAY:
            return False
        self.da_noi[ly_do] = now
        return True

    def quyet_dinh(self, cfg: CauHinh, tt: TinhTrang, now: float) -> tuple[str, str]:
        """-> (việc, lý do). việc: "cho" (chưa tới nhịp / tắt) · "chay" ·
        "bo" (tới nhịp mà không chạy được — bỏ nhịp này) · "hoan" (thử lại
        nhịp kế, không bỏ)."""
        if not cfg.bat:
            return "cho", "tat"
        toi_thuong = self.hen is not None and now >= self.hen
        toi_kich = self._toi_kich(now)
        if not (toi_thuong or toi_kich):
            return "cho", ""
        if not trong_khung(now, cfg.tu, cfg.den):
            # ngoài giờ: kích theo phiếu bỏ luôn (nhịp thường đầu khung lo),
            # nhịp thường dời sang lượt sau.
            self.kich.clear()
            self.hen = now + cfg.phut * 60
            return "bo", "ngoai_gio"
        if tt.modal_busy:
            return "hoan", "modal"
        ly_do = ""
        if tt.dang_quet or tt.dang_nhan > 0:
            ly_do = "dang_nhan"
        elif tt.db_hong:
            ly_do = "db_hong"
        elif tt.tam_dung:
            ly_do = "tam_dung"
        elif not tt.co_key:
            ly_do = "khong_key"
        elif tt.o_dia is None:
            return "hoan", "cho_do_o"
        elif not tt.o_dia[0]:
            ly_do = "o_day"
        if ly_do:
            if toi_thuong:
                self.hen = now + cfg.phut * 60
            if ly_do != "dang_nhan":
                self.kich.clear()      # còn lỗi thì lượt kích cũng không chạy được
            return "bo", ly_do
        return "chay", "kich" if (toi_kich and not toi_thuong) else "nhip"

    def da_chay(self, cfg: CauHinh, now: float) -> None:
        self.lan_chay += 1
        self.lan_cuoi = now
        self.hen = now + cfg.phut * 60
        for k in [k for k, t in self.kich.items() if t <= now]:
            self.kich.pop(k, None)


LOI_NOI = {
    "ngoai_gio": "ngoài khung giờ tự chạy",
    "dang_nhan": "lượt trước còn đang quét/nhận file — bỏ nhịp này",
    "db_hong": "cơ sở dữ liệu báo hỏng — khởi động lại app để tự chữa",
    "tam_dung": "hàng việc đang TẠM DỪNG (bot: /chaytiep)",
    "khong_key": "chưa có key AI (Cài đặt AI)",
    "o_day": "ổ đĩa sắp đầy",
}


# --------------------------------------------------------------- ổ đĩa --
def _o_cua(p) -> str:
    s = str(p or "").strip().replace("/", "\\")
    if len(s) >= 2 and s[1] == ":":
        return s[0].upper() + ":\\"
    if s.startswith("\\\\"):
        phan = [x for x in s.split("\\") if x]
        if len(phan) >= 2:
            return "\\\\" + phan[0] + "\\" + phan[1] + "\\"
    return ""


def _co_han(fn, o, han: float):
    """Gọi fn(o) ở luồng phụ, chờ tối đa `han` giây (ổ mạng chết có thể treo
    shutil.disk_usage hàng phút). Quá hạn -> ném TimeoutError."""
    import threading
    hop: dict = {}

    def chay():
        try:
            hop["v"] = fn(o)
        except BaseException as e:  # noqa: BLE001
            hop["e"] = e
    t = threading.Thread(target=chay, daemon=True, name="bq-do-o")
    t.start()
    t.join(han)
    if t.is_alive():
        raise TimeoutError(f"đo ổ {o} quá {han:.0f} giây")
    if "e" in hop:
        raise hop["e"]
    return hop["v"]


def kiem_o_dia(thu_muc_kenh, o_video_gb: float = O_VIDEO_GB,
               o_c_gb: float = O_C_GB, dung_luong=None,
               han: float = DO_O_HAN_GIAY) -> tuple[bool, str]:
    """#20: kiểm TỪNG ổ chứa thư mục kênh (ngưỡng o_video_gb) + ổ C (o_c_gb).
    Gọi ở LUỒNG NỀN (ổ mạng chết có thể treo cả chục giây). Ổ không đọc được
    (chưa cắm) không tính là đầy — quét kênh tự bỏ qua kênh đó."""
    du = dung_luong or (lambda o: shutil.disk_usage(o).free / 1e9)
    nguong: dict[str, float] = {}
    for d in thu_muc_kenh or []:
        o = _o_cua(d)
        if o:
            nguong[o] = max(nguong.get(o, 0.0), float(o_video_gb))
    nguong["C:\\"] = max(nguong.get("C:\\", 0.0), float(o_c_gb))
    thieu = []
    for o, ng in sorted(nguong.items()):
        try:
            con = float(_co_han(du, o, han))
        except Exception:  # noqa: BLE001 - ổ chưa cắm / quá hạn: không tính là đầy
            continue
        if con < ng:
            thieu.append(f"ổ {o.rstrip(chr(92))} còn {con:.1f} GB (cần ≥ {ng:.0f} GB)")
    return (not thieu), "; ".join(thieu)


def thu_muc_kenh_bat(root: str) -> list[str]:
    """Thư mục của mọi kênh đang BẬT dây chuyền (LUỒNG NỀN)."""
    from app.core import pipeline as P
    from app.database.db import db
    ra = []
    for r in db.query("SELECT name, pipe_src, export_dir FROM projects "
                      "WHERE pipe_on=1 AND pipe_hidden=0"):
        try:
            ra.append(str(P.resolve_src_dir(root, r["name"], (r["pipe_src"] or "").strip()
                                            or (r["export_dir"] or "").strip())))
        except Exception:  # noqa: BLE001
            continue
    return ra


def gio_hien(ts: float | None) -> str:
    if not ts:
        return "—"
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S %d/%m")


def bay_gio() -> float:
    return time.time()
