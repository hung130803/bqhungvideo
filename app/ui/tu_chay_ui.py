# -*- coding: utf-8 -*-
"""TỰ CHẠY DÂY CHUYỀN — phần nối giao diện (INTEGRATION.md mục 5, 11, 12).

Thuộc MainWindow (KHÔNG treo vào `StudioPage._poll_tick`: nó dừng hẳn khi mở
hộp chọn file và khi DB vỡ). Hai nhịp QTimer riêng:

  15 s — `nhip()`: chỉ đọc RAM, quyết định có chạy không (tu_chay.LichTuChay)
         rồi gọi ĐÚNG `StudioPage._bot_chay_day_chuyen(nhóm đã lưu,
         tu_dong=True)` — hàm của nút ▶ / bot. Lượt tự chạy KHÔNG nhảy màn hình.
  60 s — `nhip_60()`: dựng + ghi file TRẠNG THÁI BẬN (dựng ở luồng giao diện
         -> app treo thì file cũ đi, đúng mục 12), rồi ở LUỒNG NỀN (_chay_nen):
         đo ổ đĩa từng ổ chứa thư mục kênh + đọc phiếu tải + ghi phiếu cắt.

Không hộp thoại, không gọi mạng trên luồng giao diện; Telegram gửi qua
`tele_bot._bot._viec` (luồng nền của bot). Công tắc mặc định TẮT; tắt = app
chạy y như trước 04/11/2026.
"""
from __future__ import annotations

import os
import threading

from PyQt6.QtCore import QObject, QTimer

from app.core import phieu_dot as PD
from app.core import tu_chay as TC


#: lượt nền (đo ổ + phiếu) chạy quá chừng này giây thì coi là treo, cho đo lại.
NEN_TOI_DA_GIAY = 300


class TuChayUI(QObject):
    def __init__(self, parent, studio, state, dong_ho=None):
        super().__init__(parent)
        self.studio = studio
        self.state = state
        self._dong_ho = dong_ho or TC.bay_gio
        self.lich = TC.LichTuChay()
        self._mo_app = True
        self.o_dia = None                 # (ok, lời) của lần đo gần nhất
        self._nen_dang = False
        self._bo_doc = PD.BoDoc()
        self._da_dua_bao: set = set()     # dot_id đã đưa bot trong phiên này
        self._da_bao_key = False
        self._ban_loi_da_ghi = False
        self.so_ghi_ban = 0
        self.lan_nen = 0
        self._t15 = self._t60 = None
        self._nen_tu = 0.0

    # ------------------------------------------------------------ nhịp --
    def bat_dau(self) -> None:
        self._t15 = QTimer(self)
        self._t15.timeout.connect(self.nhip)
        self._t15.start(15_000)
        self._t60 = QTimer(self)
        self._t60.timeout.connect(self.nhip_60)
        self._t60.start(60_000)
        QTimer.singleShot(20_000, self.nhip_60)

    def cau_hinh(self) -> TC.CauHinh:
        from app.ui.appsettings import app_settings
        return TC.doc_cau_hinh(app_settings())

    def tinh_trang(self) -> TC.TinhTrang:
        S = self.studio
        try:
            from app.ai import llm as _llm
            co_key = bool(_llm.is_configured())
        except Exception:  # noqa: BLE001
            co_key = True
        try:
            from app.database.db import db
            db_hong = bool(getattr(db, "corrupt_live", False))
        except Exception:  # noqa: BLE001
            db_hong = False
        pool = getattr(self.state, "pool", None)
        try:
            tam = bool(pool is not None and pool.dang_tam_dung())
        except Exception:  # noqa: BLE001
            tam = False
        return TC.TinhTrang(
            modal_busy=bool(getattr(S, "_modal_busy", False)),
            dang_quet=S._pipe_dang_quet_n() > 0,
            dang_nhan=int(S._bot_dang_nhan() or 0),
            tam_dung=tam, co_key=co_key, db_hong=db_hong, o_dia=self.o_dia)

    def nhip(self, now: float | None = None) -> str:
        """1 nhịp quyết định. Trả việc đã làm (test đọc). Không bao giờ ném."""
        try:
            return self._nhip(self._dong_ho() if now is None else now)
        except Exception as e:  # noqa: BLE001 - tự chạy là phụ, không làm sập app
            try:
                self.studio._pipe_log(f"⚠ Tự chạy: lỗi nhịp — {e}")
            except Exception:  # noqa: BLE001
                pass
            return "loi"

    def _nhip(self, now: float) -> str:
        cfg = self.cau_hinh()
        self.lich.dong_bo(cfg, now, luc_mo_app=self._mo_app)
        self._mo_app = False
        if not cfg.bat:
            return "tat"
        tt = self.tinh_trang()
        viec, ly = self.lich.quyet_dinh(cfg, tt, now)
        if tt.co_key:
            self._da_bao_key = False
        if viec == "chay":
            kq = self.studio._bot_chay_day_chuyen(cfg.nhom, tu_dong=True) or {}
            self.lich.da_chay(cfg, now)
            if not kq.get("ok") and self.lich.nen_noi("kq:" + str(kq.get("ly_do")), now):
                self.studio._pipe_log(f"⏸ Tự chạy: không chạy được — {kq.get('ly_do')}")
            return "chay"
        if viec == "bo" and ly != "ngoai_gio":
            loi = TC.LOI_NOI.get(ly, ly)
            if ly == "o_day" and self.o_dia:
                loi += f": {self.o_dia[1]}"
            if self.lich.nen_noi(ly, now):
                self.studio._pipe_log(f"⏸ Tự chạy: không chạy lượt mới — {loi}")
                if ly == "o_day":
                    self.tele(f"💾 <b>Tự chạy dây chuyền DỪNG</b> — {PD._h(loi)}. "
                              "Dọn ổ rồi app tự chạy lại ở nhịp sau.")
            if ly == "khong_key" and not self._da_bao_key:
                self._da_bao_key = True
                self.tele("🔴 <b>Tự chạy dây chuyền KHÔNG chạy</b> — chưa có key AI "
                          "(Cài đặt AI). Thêm key là nhịp sau tự chạy.")
        if viec == "hoan" and ly == "cho_do_o" and self.lich.nen_noi(ly, now):
            # #5 phiên điều phối: ổ mạng chết -> đo ổ không bao giờ xong -> mọi
            # nhịp hoãn IM LẶNG. Nói ra 1 lần/giờ.
            self.studio._pipe_log("⏸ Tự chạy: đang HOÃN — chưa đo xong dung lượng "
                                  "ổ chứa thư mục kênh (ổ mạng chậm/chưa cắm?)")
        return viec

    # -------------------------------------------------- 60 s: bận + phiếu --
    def nhip_60(self, now: float | None = None) -> None:
        try:
            self._nhip_60(self._dong_ho() if now is None else now)
        except Exception as e:  # noqa: BLE001
            try:
                self.studio._pipe_log(f"⚠ Tự chạy: lỗi nhịp 60s — {e}")
            except Exception:  # noqa: BLE001
                pass

    def _nhip_60(self, now: float) -> None:
        # Trạng thái bận ghi LUÔN khi app chạy (kể cả Tự chạy TẮT) để PCBot biết
        # app bận cả khi anh Hùng bấm cắt tay. Hộp cát test / chưa cài PCBot
        # (không có thư mục exchange) -> im lặng bỏ qua.
        self.ghi_ban(now)
        cfg = self.cau_hinh()
        if not cfg.bat:
            return
        if self._nen_dang:
            if now - self._nen_tu < NEN_TOI_DA_GIAY:
                return                   # lượt nền trước chưa xong (ổ mạng chậm)
            # lượt nền treo quá lâu (ổ mạng chết giữa chừng): bỏ chờ nó, đo lại
            if self.lich.nen_noi("nen_treo", now):
                self.studio._pipe_log("⚠ Tự chạy: đo ổ / đọc phiếu treo quá "
                                      f"{NEN_TOI_DA_GIAY // 60} phút — đo lại")
        self._nen_dang = True
        self._nen_tu = now
        S = self.studio
        root = S._pipe_root()
        goc = PD.thu_muc_phieu(cfg.thu_muc)
        bo_doc = self._bo_doc

        def viec():
            ra = {"o": TC.kiem_o_dia(TC.thu_muc_kenh_bat(root),
                                     cfg.o_video_gb, cfg.o_c_gb),
                  "phieu": None, "goc": goc}
            if goc is not None and (goc / "dot").is_dir():
                ra["phieu"] = PD.cap_nhat_tat_ca(goc, bo_doc, PD.ngu_canh_db(root), now)
                PD.don_phieu_cu(goc / "cat", now)
            return ra
        S._chay_nen(viec, self._nen_xong, "bq-tu-chay")

    def _nen_xong(self, kq) -> None:
        self._nen_dang = False
        self.lan_nen += 1
        ok, val = kq
        now = self._dong_ho()
        if not ok:
            if self.lich.nen_noi("nen_loi", now):
                self.studio._pipe_log(f"⚠ Tự chạy: đo ổ / đọc phiếu lỗi — {val}")
            return
        self.o_dia = val["o"]
        ra, goc = val.get("phieu"), val.get("goc")
        if not ra:
            return
        for dot, vid, ts in ra["xong_moi"]:
            self.lich.them_kich(dot, vid, ts, now)
        for s in ra["bao"]:
            self.studio._pipe_log("⚠ Phiếu đợt: " + s)
            self.tele("⚠ <b>Phiếu đợt</b>: " + PD._h(s))
        if ra.get("loi_ghi") and self.lich.nen_noi("ghi_phieu", now):
            self.studio._pipe_log("⚠ " + ra["loi_ghi"])
        for su in ra["su_kien"]:
            if su[0] == "mat_file":
                t = (f"MẤT FILE: kênh «{su[1]}» — phiếu tải ghi xong '{su[2]}' "
                     f"nhưng sau {PD.MAT_FILE_PHUT} phút không thấy file trong thư "
                     "mục và không có trong sổ")
                self.studio._pipe_log("⚠ " + t)
                self.tele(f"⚠ <b>MẤT FILE</b>: kênh «{PD._h(su[1])}» — phiếu tải ghi "
                          f"xong '{PD._h(su[2])}' nhưng sau {PD.MAT_FILE_PHUT} phút "
                          "không thấy file trong thư mục và không có trong sổ")
        self._bao_kck(ra.get("kck") or [], now)
        for dot, text in ra["bao_cao"]:
            if dot in self._da_dua_bao:
                continue
            self._da_dua_bao.add(dot)
            self.studio._pipe_log("📦 " + text.replace("<b>", "").replace("</b>", ""))
            self._dua_bao_cao(goc, dot, text)

    def _bao_kck(self, ds: list, now: float) -> None:
        """#18: thư mục trong phiếu không có kênh cắt -> báo MỖI NGÀY 1 lần."""
        if not ds:
            return
        from datetime import datetime
        from app.ui.appsettings import app_settings
        hom = datetime.fromtimestamp(now).strftime("%Y-%m-%d")
        s = app_settings()
        if str(s.value(TC.KHOA + "kck_ngay", "") or "") == hom:
            return
        s.setValue(TC.KHOA + "kck_ngay", hom)
        ten = ", ".join(sorted(set(str(x) for x in ds))[:6])
        t = (f"{len(set(ds))} thư mục trong phiếu tải KHÔNG có kênh cắt nào: {ten} "
             "— tạo kênh / sửa thư mục kênh (video ở đó sẽ không được cắt)")
        self.studio._pipe_log("⚠ " + t)
        self.tele("⚠ <b>Không có kênh cắt</b>: " + PD._h(t))

    def _dua_bao_cao(self, goc, dot: str, text: str) -> None:
        """#28: báo cáo nhóm đi chung tin "HẾT hàng chờ" của bot (không báo
        trùng). Không có bot -> chỉ ghi nhật ký + đánh dấu đã báo."""
        def danh_dau():
            try:
                PD.danh_dau_da_bao(goc, dot)
            except Exception:  # noqa: BLE001
                pass
        try:
            from app.core import tele_bot as TB
            if TB._bot is not None:
                TB.them_bao_cao_nhom(text, danh_dau)
                return
        except Exception:  # noqa: BLE001
            pass
        threading.Thread(target=danh_dau, daemon=True, name="bq-danh-dau").start()

    def tele(self, text: str) -> None:
        try:
            from app.core import tele_bot as TB
            b = TB._bot
            if b is not None:
                b._viec.submit(b.bao_tat_ca, text)
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------- trạng thái bận --
    def noi_dung_ban(self, now: float, dang_thoat: bool = False) -> dict:
        try:
            from app import services
            c = services.queue_counts() or {}
            dang_lam = int(c.get("analyzing", 0) or 0) + int(c.get("exporting", 0) or 0)
            cho = int(c.get("waiting", 0) or 0)
        except Exception:  # noqa: BLE001
            cho = dang_lam = 0
        from app.version import __version__
        S = self.studio
        tt = self.tinh_trang()
        ly = "tam_dung" if tt.tam_dung else ("o_day" if self.o_dia and not self.o_dia[0]
                                             else None)
        return PD.noi_dung_ban(cho, dang_lam, int(S._bot_dang_nhan() or 0),
                               S._pipe_dang_quet_n() > 0, os.getpid(), __version__,
                               ly_do=ly, now=now, dang_thoat=dang_thoat)

    def ghi_ban(self, now: float, dang_thoat: bool = False, dong_bo: bool = False) -> bool:
        """Dựng nội dung ở LUỒNG GIAO DIỆN (app treo -> không ai ghi -> file
        cũ đi, PCBot biết). Ghi bằng 1 luồng ngắn do chính nhịp này đẻ ra —
        không có vòng nền nào tự ghi hộ. `dong_bo` = lần cuối lúc thoát êm."""
        d = PD.thu_muc_exchange()
        if d is None:
            return False
        if not d.is_dir():
            return False                 # chưa cài PCBot -> im lặng (mục 12)
        nd = self.noi_dung_ban(now, dang_thoat)
        f = d / PD.TEN_FILE_BAN

        def ghi():
            try:
                PD.ghi_nguyen_tu(f, nd, thu_lai=2 if dong_bo else 5)
                self.so_ghi_ban += 1
            except OSError as e:
                if not self._ban_loi_da_ghi:
                    self._ban_loi_da_ghi = True
                    # chỉ đặt cờ ở luồng nền; nhật ký ghi ở nhịp sau (luồng GD)
                    self._ban_loi_cho = str(e)
        if dong_bo:
            ghi()
        else:
            threading.Thread(target=ghi, daemon=True, name="bq-ghi-ban").start()
        loi = getattr(self, "_ban_loi_cho", None)
        if loi:
            self._ban_loi_cho = None
            self.studio._pipe_log(f"ℹ Trạng thái bận: không ghi được ({loi}) — bỏ qua")
        return True

    def thoat(self) -> None:
        """closeEvent: ghi lần cuối `ban=false` (mục 12)."""
        try:
            self.ghi_ban(self._dong_ho(), dang_thoat=True, dong_bo=True)
        except Exception:  # noqa: BLE001
            pass


# --------------------------------------------------------- hộp cài đặt --
def mo_hop(studio, exec_: bool = True):
    """Hộp "Tự chạy dây chuyền" (menu ⋮ của hộp Dây chuyền). Nhãn CHỮ, không
    emoji. Bật ô KHÔNG chạy gì ngay: chỉ lưu khi bấm Lưu, và nhịp đầu tiên
    rơi vào bây giờ + N phút."""
    from PyQt6.QtCore import QTime
    from PyQt6.QtWidgets import (QCheckBox, QDialog, QFileDialog, QFormLayout,
                                 QHBoxLayout, QLabel, QLineEdit, QPushButton,
                                 QTimeEdit, QVBoxLayout)
    from app.ui.appsettings import app_settings
    from app.ui.wheelguard import NoWheelComboBox, NoWheelSpinBox

    s = app_settings()
    cfg = TC.doc_cau_hinh(s)
    dlg = QDialog(studio)
    dlg.setWindowTitle("Tự chạy dây chuyền")
    lay = QVBoxLayout(dlg)
    gt = QLabel("Tự chạy gọi đúng nút Chạy dây chuyền theo nhịp trong khung giờ. "
                "Mặc định TẮT. Bật xong lượt đầu chạy sau đúng số phút của nhịp "
                "(không chạy ngay). Lượt tự chạy không nhảy màn hình.")
    gt.setWordWrap(True)
    lay.addWidget(gt)
    f = QFormLayout()
    cb_bat = QCheckBox("Bật Tự chạy dây chuyền")
    cb_bat.setChecked(cfg.bat)
    f.addRow(cb_bat)

    def _te(phut):
        t = QTimeEdit()
        t.setDisplayFormat("HH:mm")
        t.setTime(QTime(min(23, phut // 60), phut % 60))
        return t
    te_tu, te_den = _te(cfg.tu), _te(min(cfg.den, 23 * 60 + 59))
    hb = QHBoxLayout()
    hb.addWidget(te_tu)
    hb.addWidget(QLabel("đến"))
    hb.addWidget(te_den)
    f.addRow("Khung giờ:", hb)
    sp = NoWheelSpinBox()
    sp.setRange(1, 240)
    sp.setSuffix(" phút")
    sp.setValue(cfg.phut)
    f.addRow("Nhịp chạy:", sp)
    cb_nhom = NoWheelComboBox()
    cb_nhom.addItem("Tất cả nhóm", "__ALL__")
    try:
        from app.database.db import db
        ds = [r["g"] for r in db.query(
            "SELECT DISTINCT COALESCE(grp,'') g FROM projects ORDER BY g")]
    except Exception:  # noqa: BLE001
        ds = []
    try:
        ds += [g for g in studio._extra_groups() if g not in ds]
    except Exception:  # noqa: BLE001
        pass
    for g in ds:
        cb_nhom.addItem(g or "Chưa phân nhóm", g)
    i = cb_nhom.findData(cfg.nhom) if cfg.nhom != "" else cb_nhom.findData("")
    if i < 0 and cfg.nhom != "__ALL__":
        cb_nhom.addItem(f"{cfg.nhom} (không còn kênh)", cfg.nhom)
        i = cb_nhom.count() - 1
    cb_nhom.setCurrentIndex(max(0, i))
    f.addRow("Nhóm:", cb_nhom)
    ed = QLineEdit(cfg.thu_muc)
    ed.setPlaceholderText(PD.THU_MUC_MAC_DINH)
    b_chon = QPushButton("Chọn thư mục")
    hb2 = QHBoxLayout()
    hb2.addWidget(ed, 1)
    hb2.addWidget(b_chon)
    f.addRow("Thư mục phiếu đợt:", hb2)

    def _chon():
        d = studio._busy_dialog(QFileDialog.getExistingDirectory, dlg,
                                "Thư mục phiếu đợt", ed.text() or PD.THU_MUC_MAC_DINH)
        if d:
            ed.setText(d)
    b_chon.clicked.connect(_chon)
    sp_v = NoWheelSpinBox()
    sp_v.setRange(1, 2000)
    sp_v.setSuffix(" GB")
    sp_v.setValue(int(cfg.o_video_gb))
    f.addRow("Dừng khi ổ chứa video còn dưới:", sp_v)
    sp_c = NoWheelSpinBox()
    sp_c.setRange(1, 2000)
    sp_c.setSuffix(" GB")
    sp_c.setValue(int(cfg.o_c_gb))
    f.addRow("Dừng khi ổ C còn dưới:", sp_c)
    lay.addLayout(f)
    tc = getattr(studio.window(), "_tu_chay", None)
    tt = QLabel()
    tt.setWordWrap(True)
    if tc is not None:
        o = tc.o_dia
        tt.setText(f"Lượt tự chạy: {tc.lich.lan_chay} · lần cuối "
                   f"{TC.gio_hien(tc.lich.lan_cuoi)} · lượt kế {TC.gio_hien(tc.lich.hen)}"
                   + ("" if o is None else (" · ổ đĩa ổn" if o[0] else f" · {o[1]}")))
    else:
        tt.setText("Chưa có lượt tự chạy nào trong phiên này.")
    lay.addWidget(tt)
    hb3 = QHBoxLayout()
    hb3.addStretch(1)
    b_luu = QPushButton("Lưu")
    b_dong = QPushButton("Đóng")
    hb3.addWidget(b_luu)
    hb3.addWidget(b_dong)
    lay.addLayout(hb3)

    def _luu():
        s.setValue(TC.KHOA + "bat", bool(cb_bat.isChecked()))
        s.setValue(TC.KHOA + "tu", te_tu.time().toString("HH:mm"))
        s.setValue(TC.KHOA + "den", te_den.time().toString("HH:mm"))
        s.setValue(TC.KHOA + "phut", int(sp.value()))
        _g = cb_nhom.currentData()
        s.setValue(TC.KHOA + "nhom", TC.NHOM_CHUA if _g == "" else _g)
        s.setValue(TC.KHOA + "thu_muc", ed.text().strip())
        s.setValue(TC.KHOA + "o_video_gb", int(sp_v.value()))
        s.setValue(TC.KHOA + "o_c_gb", int(sp_c.value()))
        s.sync()
        try:
            studio._pipe_log(
                "Tự chạy: " + ("BẬT" if cb_bat.isChecked() else "TẮT")
                + f" · {te_tu.time().toString('HH:mm')}–{te_den.time().toString('HH:mm')}"
                + f" · nhịp {sp.value()} phút · nhóm «{cb_nhom.currentText()}»")
        except Exception:  # noqa: BLE001
            pass
        dlg.accept()
    b_luu.clicked.connect(_luu)
    b_dong.clicked.connect(dlg.reject)
    dlg._luu = _luu                 # test gọi thẳng
    dlg._o = {"bat": cb_bat, "tu": te_tu, "den": te_den, "phut": sp,
              "nhom": cb_nhom, "thu_muc": ed, "o_video": sp_v, "o_c": sp_c}
    studio._tu_chay_dlg = dlg
    if exec_:
        dlg.exec()
    return dlg
