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
from app.ui.theme import ACCENT, BORDER, DANGER, MUTED, SUCCESS, TEXT


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


class ServerConfigDialog(QDialog):
    """Nhập địa chỉ Supabase + anon key (admin làm 1 lần nếu app chưa nướng sẵn)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cấu hình máy chủ tài khoản (Supabase)")
        self.resize(560, 240)
        from app.auth_config import supabase_key, supabase_url
        v = QVBoxLayout(self)
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
        cancel = QPushButton("Đóng"); cancel.clicked.connect(self.reject)
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
        self._s = QSettings("AIContentStudio", "studio")
        self.setWindowTitle("BQ Hung Video — Đăng nhập")
        self.setModal(True)
        self.resize(420, 300)
        self.setStyleSheet(f"QDialog{{background:#11131A;}} QLabel{{color:{TEXT};}}")

        v = QVBoxLayout(self); v.setContentsMargins(28, 24, 28, 22); v.setSpacing(10)
        brand = QLabel("BQ Hung Video")
        brand.setStyleSheet(f"color:{ACCENT}; font-size:22px; font-weight:800;")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = QLabel("Đăng nhập để sử dụng")
        sub.setStyleSheet(f"color:{MUTED}; font-size:13px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(brand); v.addWidget(sub); v.addSpacing(8)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Tên đăng nhập")
        self.password = QLineEdit()
        self.password.setPlaceholderText("Mật khẩu")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        for w in (self.username, self.password):
            w.setMinimumHeight(38)
            w.setStyleSheet(
                f"QLineEdit{{background:#1B1E27; border:1px solid {BORDER}; "
                f"border-radius:8px; padding:6px 10px; color:{TEXT};}}")
        v.addWidget(self.username); v.addWidget(self.password)

        # GHI NHỚ mật khẩu: lần sau tự điền sẵn -> chỉ bấm Đăng nhập
        self.remember = QCheckBox("Ghi nhớ mật khẩu (lần sau khỏi gõ)")
        self.remember.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        v.addWidget(self.remember)
        saved_u = self._s.value("save_user", "") or self._s.value("last_user", "") or ""
        saved_p = self._dec(self._s.value("save_pass", "") or "")
        self.username.setText(saved_u)
        if saved_p:
            self.password.setText(saved_p)
            self.remember.setChecked(True)

        self.note = QLabel(""); self.note.setWordWrap(True)
        self.note.setStyleSheet("font-size:12px;")
        v.addWidget(self.note)

        self.btn = QPushButton("Đăng nhập"); self.btn.setProperty("primary", True)
        self.btn.setMinimumHeight(40); self.btn.setDefault(True)
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

    def _set_note(self, kind, text):
        col = {"err": DANGER, "ok": SUCCESS, "info": MUTED}.get(kind, MUTED)
        self.note.setStyleSheet(f"color:{col}; font-size:12px;")
        self.note.setText(text)

    def _config(self):
        ServerConfigDialog(self).exec()

    def _do_login(self):
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
        QApplication.processEvents()
        _wait(True)
        try:
            res = auth.login(u, p)
        except auth.AuthError as e:
            _wait(False); self.btn.setEnabled(True)
            self._set_note("err", str(e)); return
        finally:
            _wait(False)
        self.btn.setEnabled(True)
        if not res:
            self._set_note("err", "Sai tên đăng nhập/mật khẩu, hoặc tài khoản bị khoá.")
            return
        self.user = res["username"]; self.role = res["role"]
        self._s.setValue("last_user", self.user)
        self._s.setValue("save_user", self.user)
        if self.remember.isChecked():            # GHI NHỚ mật khẩu cho lần sau
            self._s.setValue("save_pass", self._enc(p))
        else:
            self._s.remove("save_pass")
        self.password = p                         # trả mật khẩu cho main/admin
        self.accept()

    @staticmethod
    def _enc(s: str) -> str:
        """Mã hóa mật khẩu bằng DPAPI Windows — base64 thuần tương đương
        plaintext, ai đọc Registry cũng lấy được tài khoản."""
        import base64
        raw = (s or "").encode("utf-8")
        enc = _dpapi(raw, protect=True)
        if enc is not None:
            return "dpapi:" + base64.b64encode(enc).decode("ascii")
        try:  # nền tảng không có DPAPI -> đành base64 như cũ
            return base64.b64encode(raw).decode("ascii")
        except Exception:  # noqa: BLE001
            return ""

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
        v = QVBoxLayout(self)
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

        self.note = QLabel(""); self.note.setStyleSheet("font-size:12px;")
        v.addWidget(self.note)
        close = QPushButton("Đóng"); close.setProperty("ghost", True)
        close.clicked.connect(self.accept)
        v.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
        self._load()

    def _msg(self, kind, text):
        col = {"err": DANGER, "ok": SUCCESS}.get(kind, MUTED)
        self.note.setStyleSheet(f"color:{col}; font-size:12px;")
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
        uname = usr.get("username", ""); is_admin = usr.get("role") == "admin"
        active = usr.get("active", True)
        lock = QPushButton("Mở khoá" if not active else "Khoá")
        lock.setProperty("ghost", True)
        lock.clicked.connect(lambda _, n=uname, a=active: self._toggle(n, not a))
        h.addWidget(lock)
        rs = QPushButton("Đổi MK"); rs.setProperty("ghost", True)
        rs.clicked.connect(lambda _, n=uname: self._reset_pass(n))
        h.addWidget(rs)
        dl = QPushButton("Xoá"); dl.setProperty("danger", True)
        dl.setEnabled(not is_admin)         # không xoá admin
        dl.clicked.connect(lambda _, n=uname: self._delete(n))
        h.addWidget(dl)
        return w

    def _add(self):
        dlg = QDialog(self); dlg.setWindowTitle("Thêm / Đặt lại tài khoản")
        dlg.resize(380, 230)
        v = QVBoxLayout(dlg); form = QFormLayout()
        u = QLineEdit(); p = QLineEdit()
        role = QComboBox(); role.addItem("Người dùng", "user"); role.addItem("Admin", "admin")
        form.addRow("Tên đăng nhập:", u)
        form.addRow("Mật khẩu:", p)
        form.addRow("Quyền:", role)
        v.addLayout(form)
        hint = QLabel("Nếu tên đã tồn tại → sẽ ĐẶT LẠI mật khẩu/quyền cho tên đó.")
        hint.setWordWrap(True); hint.setStyleSheet(f"color:{MUTED}; font-size:11px;")
        v.addWidget(hint)
        row = QHBoxLayout(); row.addStretch(1)
        ok = QPushButton("Lưu"); ok.setProperty("primary", True)
        ok.clicked.connect(dlg.accept)
        cancel = QPushButton("Huỷ"); cancel.clicked.connect(dlg.reject)
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
