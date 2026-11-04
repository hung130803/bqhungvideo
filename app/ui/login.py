"""Màn ĐĂNG NHẬP (hiện trước khi vào app) + màn ADMIN quản lý tài khoản.

Tài khoản nằm trên Supabase (tập trung). Admin tạo/khoá/xoá tài khoản cho team.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.core import auth
from app.ui.appsettings import app_settings
from app.ui.theme import (
    H_HERO, SP_2, SP_3, SP_4, SP_5, SP_6, pad, set_role, set_size, set_tone,
    set_variant,
)

#: kiểu ghi chú -> vai màu QSS (theme.QLabel[tone=...]); không setStyleSheet
_NOTE_TONE = {"err": "danger", "ok": "success", "info": "muted"}


def _wait(on: bool):
    if on:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    else:
        QApplication.restoreOverrideCursor()


def _dpapi(data: bytes, protect: bool):
    """Mã hóa/giải mã bằng Windows DPAPI (khóa theo tài khoản Windows).
    Trả bytes, hoặc None nếu không dùng được (non-Windows/lỗi)."""
    try:
        import ctypes
        from ctypes import wintypes

        class _Blob(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD),
                        ("pbData", ctypes.POINTER(ctypes.c_char))]

        buf = ctypes.create_string_buffer(data, len(data))
        blob_in = _Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
        blob_out = _Blob()
        fn = (ctypes.windll.crypt32.CryptProtectData if protect
              else ctypes.windll.crypt32.CryptUnprotectData)
        if not fn(ctypes.byref(blob_in), None, None, None, None, 0,
                  ctypes.byref(blob_out)):
            return None
        try:
            return ctypes.string_at(blob_out.pbData, blob_out.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    except Exception:  # noqa: BLE001
        return None


#: số giây đếm ngược trước khi tự đăng nhập
TU_DANG_NHAP_GIAY = 5


def tu_dang_nhap_bat() -> bool:
    """Tắt bằng env BQ_TU_DANG_NHAP=0 (gỡ rối / máy dùng chung)."""
    import os
    return (os.environ.get("BQ_TU_DANG_NHAP", "1").strip() or "1") != "0"


def _ghi_log(dong: str):
    """Ghi logs/dang_nhap_<ngày>.log — người ở xa (qua điện thoại) không thấy
    màn hình, nên lý do bot không lên phải đọc được ở đây. KHÔNG ghi mật khẩu."""
    try:
        from datetime import datetime
        from config import LOGS_DIR
        with open(LOGS_DIR / f"dang_nhap_{datetime.now():%Y%m%d}.log", "a",
                  encoding="utf-8") as f:
            f.write(f"[{datetime.now():%H:%M:%S}] {dong}\n")
    except Exception:  # noqa: BLE001
        pass


class ServerConfigDialog(QDialog):
    """Nhập địa chỉ Supabase + anon key (admin làm 1 lần nếu app chưa nướng sẵn)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cấu hình máy chủ tài khoản (Supabase)")
        self.resize(560, 240)
        from app.auth_config import supabase_key, supabase_url
        v = QVBoxLayout(self); pad(v, SP_4, spacing=SP_3)
        v.addWidget(QLabel(
            "Dán 2 thứ lấy từ Supabase → Project Settings → API:\n"
            "• Project URL  (vd https://abcd.supabase.co)\n"
            "• anon public key  (chuỗi eyJ...)"))
        form = QFormLayout()
        self.url = QLineEdit(supabase_url())
        self.key = QLineEdit(supabase_key())
        self.url.setPlaceholderText("https://xxxx.supabase.co")
        self.key.setPlaceholderText("anon public key")
        form.addRow("Project URL:", self.url)
        form.addRow("anon key:", self.key)
        v.addLayout(form)
        row = QHBoxLayout(); row.addStretch(1)
        save = QPushButton("Lưu"); save.setProperty("primary", True)
        save.clicked.connect(self._save)
        cancel = QPushButton("Đóng"); set_variant(cancel, "ghost")
        cancel.clicked.connect(self.reject)
        row.addWidget(cancel); row.addWidget(save)
        v.addLayout(row)

    def _save(self):
        from app.auth_config import set_config
        if not self.url.text().strip() or not self.key.text().strip():
            QMessageBox.information(self, "Thiếu", "Nhập đủ URL và anon key.")
            return
        set_config(self.url.text(), self.key.text())
        self.accept()


class LoginDialog(QDialog):
    """Đăng nhập trước khi vào app. accept() chỉ khi đăng nhập THÀNH CÔNG."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.user = None
        self.role = None
        self.password = None
        self._s = app_settings()
        self.setWindowTitle("BQ Hung Video — Đăng nhập")
        self.setModal(True)
        self.resize(420, 300)
        # nền/ô nhập/chữ lấy từ QSS chung (theme.py) — không stylesheet riêng
        v = QVBoxLayout(self); pad(v, SP_6, SP_5, SP_6, SP_5, spacing=SP_3)
        brand = QLabel("BQ Hung Video")
        set_role(brand, "display"); set_tone(brand, "accent")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = QLabel("Đăng nhập để sử dụng")
        set_tone(sub, "muted")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(brand); v.addWidget(sub); v.addSpacing(SP_2)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Tên đăng nhập")
        self.password = QLineEdit()
        self.password.setPlaceholderText("Mật khẩu")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        for w in (self.username, self.password):
            w.setMinimumHeight(H_HERO)
        v.addWidget(self.username); v.addWidget(self.password)

        # GHI NHỚ mật khẩu: lần sau tự điền sẵn -> chỉ bấm Đăng nhập
        self.remember = QCheckBox("Ghi nhớ mật khẩu (lần sau khỏi gõ)")
        set_tone(self.remember, "muted")
        v.addWidget(self.remember)
        saved_u = self._s.value("save_user", "") or self._s.value("last_user", "") or ""
        saved_p = self._dec(self._s.value("save_pass", "") or "")
        self.username.setText(saved_u)
        if saved_p:
            self.password.setText(saved_p)
            self.remember.setChecked(True)

        self.note = QLabel(""); self.note.setWordWrap(True)
        set_role(self.note, "muted")
        v.addWidget(self.note)

        self.btn = QPushButton("Đăng nhập"); self.btn.setProperty("primary", True)
        self.btn.setMinimumHeight(H_HERO); self.btn.setDefault(True)
        set_size(self.btn, "hero")
        self.btn.clicked.connect(self._do_login)
        v.addWidget(self.btn)

        row = QHBoxLayout()
        cfg = QPushButton("Cấu hình máy chủ"); cfg.setProperty("ghost", True)
        cfg.setToolTip("Admin nhập địa chỉ Supabase (1 lần) nếu app chưa có sẵn.")
        cfg.clicked.connect(self._config)
        quit_b = QPushButton("Thoát"); quit_b.setProperty("ghost", True)
        quit_b.clicked.connect(self.reject)
        row.addWidget(cfg); row.addStretch(1); row.addWidget(quit_b)
        v.addLayout(row)

        self.username.returnPressed.connect(self.password.setFocus)
        self.password.returnPressed.connect(self._do_login)

        # TỰ ĐĂNG NHẬP khi đã ghi nhớ mật khẩu: máy bật lên (app tự mở cùng
        # Windows) thì không ai ngồi bấm nút -> bot Telegram chỉ lên SAU khi
        # đăng nhập, nên đứng ở màn này là điện thoại không điều khiển được.
        # Có đếm ngược + nút Huỷ để vẫn đổi được tài khoản; gõ vào ô = huỷ.
        from PyQt6.QtCore import QTimer
        self._tu_dong = False          # lượt đang chạy là tự động?
        self._con_lai = 0
        self._lan_thu = 0
        self._dem = QTimer(self); self._dem.setInterval(1000)
        self._dem.timeout.connect(self._dem_nhip)
        self.huy_tu = QPushButton("Huỷ tự đăng nhập")
        self.huy_tu.setProperty("ghost", True)
        self.huy_tu.clicked.connect(self._huy_tu_dong)
        self.huy_tu.setVisible(False)
        v.insertWidget(v.indexOf(self.btn) + 1, self.huy_tu)
        for w in (self.username, self.password):
            w.textEdited.connect(self._huy_tu_dong)
        if saved_p and saved_u and tu_dang_nhap_bat():
            self._bat_dem(TU_DANG_NHAP_GIAY)
        # lệnh /moapp từ điện thoại (bot gác cổng) khi app đang đứng ở màn này
        self._soi_co = QTimer(self); self._soi_co.setInterval(2000)
        self._soi_co.timeout.connect(self._xem_co_tu_xa)
        self._soi_co.start()

    def _set_note(self, kind, text):
        set_tone(self.note, _NOTE_TONE.get(kind, "muted"))
        self.note.setText(text)

    def _config(self):
        ServerConfigDialog(self).exec()

    # ---- tự đăng nhập ----
    def _bat_dem(self, giay: int):
        self._tu_dong = True
        self._con_lai = max(1, int(giay))
        self.huy_tu.setVisible(True)
        self._dem_nhip(dau=True)
        self._dem.start()

    def _dem_nhip(self, dau=False):
        if not dau:
            self._con_lai -= 1
        if self._con_lai <= 0:
            self._dem.stop()
            self._do_login(tu_dong=True)
            return
        lan = f" (thử lại lần {self._lan_thu + 1})" if self._lan_thu else ""
        self._set_note("info", f"Tự đăng nhập sau {self._con_lai} giây{lan}... "
                               "Bấm 'Huỷ tự đăng nhập' nếu muốn đổi tài khoản.")

    def done(self, r):
        # main.py GIỮ đối tượng này suốt đời app (đọc .user/.password), và
        # đăng nhập xong `self.password` thành CHUỖI -> phải tắt 2 bộ đếm, không
        # thì cờ /moapp sau này gọi `.text()` trên chuỗi = lỗi trong slot Qt =
        # SẬP CẢ APP (cổng 98 bắt được).
        for t in (getattr(self, "_dem", None), getattr(self, "_soi_co", None)):
            if t is not None:
                t.stop()
        super().done(r)

    def _xem_co_tu_xa(self):
        if not isinstance(self.password, QLineEdit):
            return
        try:
            from app.core import tele_gac
            if tele_gac.co_dong_app_moi():
                # điện thoại bấm ⛔ Đóng app lúc app đứng ở màn đăng nhập
                _ghi_log("lệnh đóng app từ xa (Telegram /dongapp)")
                self._dem.stop()
                self.reject()
                return
            co = tele_gac.file_co_dang_nhap()
            if not co.exists():
                return
            co.unlink()
        except Exception:  # noqa: BLE001
            return
        if not self.btn.isEnabled():
            return                        # đang đăng nhập rồi
        if not (self.username.text().strip() and self.password.text()):
            self._set_note("err", "Điện thoại bấm đăng nhập nhưng chưa có mật khẩu "
                                  "ghi nhớ — nhập tay 1 lần + tick 'Ghi nhớ'.")
            _ghi_log("lệnh đăng nhập từ xa: KHÔNG có mật khẩu ghi nhớ")
            return
        _ghi_log("lệnh đăng nhập từ xa (Telegram /moapp)")
        self._lan_thu = 0
        self._bat_dem(1)

    def _huy_tu_dong(self, *_):
        if not self._tu_dong and not self._dem.isActive():
            return
        self._tu_dong = False
        self._dem.stop()
        self.huy_tu.setVisible(False)
        self._set_note("info", "Đã huỷ tự đăng nhập.")
        _ghi_log("huỷ tự đăng nhập (người dùng)")

    def _do_login(self, tu_dong=False):
        if not tu_dong:                 # bấm tay = thôi đếm ngược
            self._dem.stop()
            self._tu_dong = False
            self.huy_tu.setVisible(False)
        u = self.username.text().strip()
        p = self.password.text()
        if not u or not p:
            self._set_note("err", "Nhập tên đăng nhập và mật khẩu.")
            return
        from app.auth_config import is_configured
        if not is_configured():
            self._set_note("err", "Chưa cấu hình máy chủ. Bấm 'Cấu hình máy chủ'.")
            return
        self.btn.setEnabled(False); self._set_note("info", "Đang đăng nhập...")
        # Gọi Supabase ở THREAD NỀN: gọi đồng bộ trên UI thread sẽ treo cứng
        # màn đăng nhập ~20s khi mất mạng (không bấm được gì, tưởng app đơ).
        import threading
        out: list = []

        def bg():
            try:
                out.append(("ok", auth.login(u, p)))
            except auth.AuthError as e:
                out.append(("err", str(e)))
            except Exception as e:  # noqa: BLE001
                out.append(("err", f"Lỗi kết nối: {e}"))

        threading.Thread(target=bg, daemon=True).start()
        from PyQt6.QtCore import QTimer
        timer = QTimer(self)

        def poll():
            if not out:
                return
            timer.stop()
            self.btn.setEnabled(True)
            kind, res = out[0]
            tu = tu_dong and self._tu_dong   # bị huỷ giữa lượt thì thôi
            if kind == "err":
                self._set_note("err", str(res))
                if tu:
                    # mất mạng lúc vừa bật máy là chuyện thường -> THỬ LẠI,
                    # giãn dần 15s -> 30s -> 60s (không bỏ cuộc: bỏ cuộc là
                    # bot không bao giờ lên mà không ai ở máy để biết).
                    self._lan_thu += 1
                    cho = min(60, 15 * (2 ** min(self._lan_thu - 1, 2)))
                    _ghi_log(f"lỗi kết nối lần {self._lan_thu}: {res} -> thử lại sau {cho}s")
                    self._bat_dem(cho)
                return
            if not res:
                self._set_note("err",
                               "Sai tên đăng nhập/mật khẩu, hoặc tài khoản bị khoá.")
                if tu:
                    # SAI mật khẩu thì KHÔNG thử lại (thử lặp là tự khoá tài khoản)
                    self._tu_dong = False; self.huy_tu.setVisible(False)
                    _ghi_log("SAI mật khẩu/tài khoản bị khoá -> dừng tự đăng nhập")
                return
            if tu:
                _ghi_log(f"tự đăng nhập THÀNH CÔNG ({res['username']})"
                         + (f" sau {self._lan_thu} lần lỗi" if self._lan_thu else ""))
            self.user = res["username"]; self.role = res["role"]
            self._s.setValue("last_user", self.user)
            self._s.setValue("save_user", self.user)
            if self.remember.isChecked():        # GHI NHỚ mật khẩu cho lần sau
                encrypted = self._enc(p)
                if encrypted:
                    self._s.setValue("save_pass", encrypted)
                else:
                    self._s.remove("save_pass")
                    QMessageBox.warning(self, 'Không lưu mật khẩu',
                                        'Windows không mã hóa được mật khẩu. '
                                        'Bạn vẫn đăng nhập được; lần sau cần nhập lại mật khẩu.')
            else:
                self._s.remove("save_pass")
            self.password = p                     # trả mật khẩu cho main/admin
            self.accept()

        timer.timeout.connect(poll)
        timer.start(150)

    @staticmethod
    def _enc(s: str) -> str:
        """Mã hóa mật khẩu bằng DPAPI Windows — base64 thuần tương đương
        plaintext, ai đọc Registry cũng lấy được tài khoản."""
        import base64
        raw = (s or "").encode("utf-8")
        enc = _dpapi(raw, protect=True)
        if enc is not None:
            return "dpapi:" + base64.b64encode(enc).decode("ascii")
        return ""  # Không hạ xuống base64 thuần khi mã hóa hệ điều hành lỗi.

    @staticmethod
    def _dec(s: str) -> str:
        import base64
        s = s or ""
        try:
            if s.startswith("dpapi:"):
                dec = _dpapi(base64.b64decode(s[6:].encode("ascii")),
                             protect=False)
                return dec.decode("utf-8") if dec is not None else ""
            # tương thích bản cũ (base64 thuần): vẫn đọc được; lần đăng nhập
            # sau sẽ tự lưu lại dạng DPAPI
            return base64.b64decode(s.encode("ascii")).decode("utf-8")
        except Exception:  # noqa: BLE001
            return ""


class AdminUsersDialog(QDialog):
    """ADMIN: tạo / đặt lại mật khẩu / khoá / xoá tài khoản team."""

    def __init__(self, admin_user, admin_pass, parent=None):
        super().__init__(parent)
        self._admin = admin_user
        self._apass = admin_pass
        self.setWindowTitle("Quản lý tài khoản (Admin)")
        self.resize(720, 480)
        v = QVBoxLayout(self); pad(v, SP_4, spacing=SP_3)
        top = QHBoxLayout()
        top.addWidget(QLabel(f"<b>Admin:</b> {admin_user}"))
        top.addStretch(1)
        add = QPushButton("+ Thêm / Đặt lại tài khoản"); add.setProperty("primary", True)
        add.clicked.connect(self._add)
        refresh = QPushButton("Tải lại"); refresh.setProperty("ghost", True)
        refresh.clicked.connect(self._load)
        top.addWidget(add); top.addWidget(refresh)
        v.addLayout(top)

        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(
            ["Tên đăng nhập", "Quyền", "Trạng thái", "Tạo lúc", "Thao tác"])
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.setColumnWidth(0, 180); self.tbl.setColumnWidth(3, 150)
        self.tbl.verticalHeader().setVisible(False)
        v.addWidget(self.tbl, 1)

        self.note = QLabel(""); set_role(self.note, "muted"); self.note.setWordWrap(True)
        v.addWidget(self.note)
        close = QPushButton("Đóng"); close.setProperty("ghost", True)
        close.clicked.connect(self.accept)
        v.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
        self._load()

    def _msg(self, kind, text):
        set_tone(self.note, _NOTE_TONE.get(kind, "muted"))
        self.note.setText(text)

    def _load(self):
        _wait(True)
        try:
            users = auth.admin_list_users(self._admin, self._apass)
        except auth.AuthError as e:
            _wait(False); self._msg("err", str(e)); return
        finally:
            _wait(False)
        self.tbl.setRowCount(0)
        for usr in users:
            r = self.tbl.rowCount(); self.tbl.insertRow(r)
            self.tbl.setItem(r, 0, QTableWidgetItem(usr.get("username", "")))
            self.tbl.setItem(r, 1, QTableWidgetItem(usr.get("role", "")))
            act = usr.get("active", True)
            self.tbl.setItem(r, 2, QTableWidgetItem("Đang mở" if act else "ĐÃ KHOÁ"))
            self.tbl.setItem(r, 3, QTableWidgetItem(
                str(usr.get("created_at", ""))[:16].replace("T", " ")))
            self.tbl.setCellWidget(r, 4, self._actions(usr))
        self._msg("ok", f"Có {len(users)} tài khoản.")

    def _actions(self, usr):
        w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(2, 2, 2, 2); h.setSpacing(4)
        # nút trong ô bảng: cỡ GỌN (padding 3px) — cỡ thường 7px bị cụt theo chiều cao dòng
        uname = usr.get("username", ""); is_admin = usr.get("role") == "admin"
        active = usr.get("active", True)
        lock = QPushButton("Mở khoá" if not active else "Khoá")
        lock.setProperty("ghost", True)
        lock.setEnabled(not is_admin)       # không khoá admin (tự khoá mình
        lock.setToolTip("" if not is_admin  # là mất quyền quản lý vĩnh viễn)
                        else "Không thể khoá/xoá tài khoản admin.")
        lock.clicked.connect(lambda _, n=uname, a=active: self._toggle(n, not a))
        h.addWidget(lock)
        rs = QPushButton("Đổi MK"); rs.setProperty("ghost", True)
        rs.clicked.connect(lambda _, n=uname: self._reset_pass(n))
        h.addWidget(rs)
        dl = QPushButton("Xoá"); dl.setProperty("danger", True)
        dl.setEnabled(not is_admin)         # không xoá admin
        dl.clicked.connect(lambda _, n=uname: self._delete(n))
        h.addWidget(dl)
        for b in (lock, rs, dl):
            set_size(b, "compact")
        self.tbl.verticalHeader().setMinimumSectionSize(34)
        self.tbl.verticalHeader().setDefaultSectionSize(34)
        return w

    def _add(self):
        dlg = QDialog(self); dlg.setWindowTitle("Thêm / Đặt lại tài khoản")
        dlg.resize(380, 230)
        v = QVBoxLayout(dlg); pad(v, SP_4, spacing=SP_3); form = QFormLayout()
        form.setHorizontalSpacing(SP_3); form.setVerticalSpacing(SP_2)
        u = QLineEdit(); p = QLineEdit()
        role = QComboBox(); role.addItem("Người dùng", "user"); role.addItem("Admin", "admin")
        form.addRow("Tên đăng nhập:", u)
        form.addRow("Mật khẩu:", p)
        form.addRow("Quyền:", role)
        v.addLayout(form)
        hint = QLabel("Nếu tên đã tồn tại → sẽ ĐẶT LẠI mật khẩu/quyền cho tên đó.")
        hint.setWordWrap(True); set_role(hint, "hint")
        v.addWidget(hint)
        row = QHBoxLayout(); row.addStretch(1)
        ok = QPushButton("Lưu"); ok.setProperty("primary", True)
        ok.clicked.connect(dlg.accept)
        cancel = QPushButton("Huỷ"); set_variant(cancel, "ghost"); cancel.clicked.connect(dlg.reject)
        row.addWidget(cancel); row.addWidget(ok); v.addLayout(row)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        un, pw = u.text().strip(), p.text()
        if not un or not pw:
            self._msg("err", "Nhập đủ tên và mật khẩu."); return
        self._call(lambda: auth.admin_upsert_user(
            self._admin, self._apass, un, pw, role.currentData()),
            f"Đã lưu tài khoản '{un}'.")

    def _reset_pass(self, uname):
        pw, ok = QInputDialog.getText(self, "Đổi mật khẩu",
                                      f"Mật khẩu mới cho '{uname}':")
        if not ok or not pw.strip():
            return
        # giữ nguyên quyền hiện tại: lấy role từ bảng
        role = "user"
        for r in range(self.tbl.rowCount()):
            if self.tbl.item(r, 0) and self.tbl.item(r, 0).text() == uname:
                role = self.tbl.item(r, 1).text() or "user"
        self._call(lambda: auth.admin_upsert_user(
            self._admin, self._apass, uname, pw.strip(), role),
            f"Đã đổi mật khẩu '{uname}'.")

    def _toggle(self, uname, active):
        self._call(lambda: auth.admin_set_active(
            self._admin, self._apass, uname, active),
            f"Đã {'mở' if active else 'khoá'} '{uname}'.")

    def _delete(self, uname):
        if QMessageBox.question(self, "Xoá tài khoản",
                                f"Xoá hẳn tài khoản '{uname}'?") \
                != QMessageBox.StandardButton.Yes:
            return
        self._call(lambda: auth.admin_delete_user(
            self._admin, self._apass, uname), f"Đã xoá '{uname}'.")

    def _call(self, fn, ok_msg):
        _wait(True)
        try:
            res = fn()
        except auth.AuthError as e:
            _wait(False); self._msg("err", str(e)); return
        finally:
            _wait(False)
        if res == "NOT_ADMIN":
            self._msg("err", "Tài khoản admin không hợp lệ."); return
        self._msg("ok", ok_msg)
        self._load()
