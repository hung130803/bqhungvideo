"""Hệ thiết kế (theme.py) + chuyển động (anim.py) + hàng đợi không restyle mỗi nhịp."""
import os
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
AREA = Path(tempfile.mkdtemp(prefix='bq_design_'))
for k, v in dict(BQ_DATA_DIR=str(AREA), BQ_DB_PATH=str(AREA/'test.db'),
                 BQ_QSETTINGS_INI=str(AREA/'settings.ini'),
                 QT_QPA_PLATFORM='offscreen', BQ_BO_MANG='1').items():
    os.environ.setdefault(k, v)
sys.path.insert(0, str(ROOT))
import _test_guard  # noqa: F401,E402
from PyQt6.QtCore import QtMsgType, qInstallMessageHandler  # noqa: E402
from PyQt6.QtWidgets import (QApplication, QLabel, QProgressBar,  # noqa: E402
                             QPushButton, QWidget)

APP = QApplication.instance() or QApplication([])
from app.ui import anim, theme  # noqa: E402


def _pump(ms):
    end = time.perf_counter() + ms / 1000
    while time.perf_counter() < end:
        APP.processEvents()


class Tokens(unittest.TestCase):
    def test_legacy_names_and_scales(self):
        for name in ('WINDOW', 'BASE', 'ELEV', 'SURFACE', 'SURFACE_HOVER', 'BORDER',
                     'TEXT', 'MUTED', 'ACCENT', 'ACCENT_HOVER', 'SUCCESS', 'DANGER',
                     'WARN', 'PURPLE', 'QSS'):
            self.assertTrue(hasattr(theme, name), name)
        self.assertEqual(theme.SPACE, (4, 8, 12, 16, 24, 32))
        self.assertEqual(theme.RADIUS, (6, 10, 14))
        self.assertEqual(theme.FONT, (11, 12, 13, 15, 18, 24))
        self.assertEqual((theme.H_COMPACT, theme.H_DEFAULT, theme.H_HERO), (26, 32, 40))

    def test_no_universal_rules_and_qss_parses(self):
        qss = theme.QSS
        self.assertNotIn('* {', qss)
        self.assertNotIn('QMainWindow, QWidget {', qss)
        self.assertNotIn('pt;', qss)               # một đơn vị: px
        bad = []

        def handler(kind, _ctx, msg):
            if 'style' in msg.lower() or 'parse' in msg.lower():
                bad.append(msg)
        old = qInstallMessageHandler(handler)
        try:
            APP.setStyleSheet(qss)
            w = QPushButton('x'); w.show(); APP.processEvents(); w.close()
        finally:
            qInstallMessageHandler(old)
        self.assertEqual(bad, [])

    def test_apply_theme_sets_px_font_and_dark_palette(self):
        theme.apply_theme(APP)
        self.assertEqual(APP.font().pixelSize(), theme.FS_MD)
        from PyQt6.QtGui import QPalette
        self.assertEqual(APP.palette().color(QPalette.ColorRole.Window).name().upper(),
                         theme.WINDOW.upper())


class Helpers(unittest.TestCase):
    def setUp(self):
        theme.apply_theme(APP)

    def test_set_role_repolishes_only_on_change(self):
        lb = QLabel('Tiêu đề'); lb.show(); APP.processEvents()
        self.assertTrue(theme.set_role(lb, 'title'))
        self.assertFalse(theme.set_role(lb, 'title'))   # không đổi -> không polish
        APP.processEvents()
        self.assertEqual(lb.font().pixelSize(), theme.FS_LG)
        self.assertTrue(theme.set_role(lb, None))
        self.assertIsNone(lb.property('role'))
        lb.close()

    def test_set_variant_keeps_legacy_props(self):
        b = QPushButton('Xóa')
        theme.set_variant(b, 'danger')
        self.assertTrue(b.property('danger'))
        self.assertEqual(b.property('variant'), 'danger')
        theme.set_variant(b, 'ghost')
        self.assertFalse(bool(b.property('danger')))
        self.assertTrue(b.property('ghost'))
        self.assertFalse(theme.set_variant(b, 'ghost'))

    def test_set_size_uses_density_property(self):
        # 'size' là Q_PROPERTY QSize của QWidget -> setProperty('size','compact') bị từ chối
        b = QPushButton('Hủy')
        theme.set_size(b, 'compact')
        self.assertEqual(b.property('density'), 'compact')
        b.show(); APP.processEvents()
        compact_h = b.sizeHint().height()
        theme.set_size(b, None); APP.processEvents()
        self.assertLess(compact_h, b.sizeHint().height())
        self.assertLessEqual(compact_h, theme.H_COMPACT)
        b.close()

    def test_pad_card_section_fit_width(self):
        fr, lay = theme.card()
        self.assertEqual(fr.objectName(), 'card')
        m = lay.contentsMargins()
        self.assertEqual((m.left(), m.top()), (theme.SP_4, theme.SP_4))
        theme.pad(lay, 16, 12, spacing=8)
        m = lay.contentsMargins()
        self.assertEqual((m.left(), m.top(), m.right(), m.bottom()), (16, 12, 16, 12))
        self.assertEqual(theme.section('nhóm').text(), 'NHÓM')
        lb = QLabel('x')
        w = theme.fit_width(lb, 'Chữ rất dài không được cụt', minimum=20)
        self.assertGreaterEqual(lb.width(), lb.fontMetrics().horizontalAdvance('Chữ rất dài không được cụt'))
        self.assertEqual(lb.maximumWidth(), w)


class Animations(unittest.TestCase):
    def setUp(self):
        theme.apply_theme(APP)
        self.win = QWidget(); self.win.resize(600, 400)

    def tearDown(self):
        self.win.close(); self.win.deleteLater(); APP.processEvents()

    def test_smooth_bar_value_is_target_immediately(self):
        bar = anim.SmoothProgressBar(self.win); bar.setRange(0, 100); bar.resize(200, 10)
        self.win.show(); APP.processEvents()
        bar.setValue(10); _pump(400)
        bar.setValue(80)
        self.assertEqual(bar.value(), 80)            # code/test đọc lại: đúng ngay
        self.assertLess(bar.displayed_value(), 80)   # phần vẽ còn đang trôi
        _pump(500)
        self.assertEqual(bar.displayed_value(), 80)
        bar.setValue(5)                              # giảm -> nhảy thẳng
        self.assertEqual(bar.displayed_value(), 5)

    def test_smooth_bar_hidden_jumps_and_delete_mid_animation(self):
        bar = anim.SmoothProgressBar(); bar.setRange(0, 100)
        bar.setValue(70)                             # không hiện -> không animate
        self.assertEqual(bar.displayed_value(), 70)
        self.win.show()
        b2 = anim.SmoothProgressBar(self.win); b2.setRange(0, 100); b2.show(); APP.processEvents()
        b2.setValue(1); b2.setValue(90)
        b2.deleteLater(); _pump(400)                 # huỷ giữa chừng: không sập
        self.assertIsInstance(b2, QProgressBar)

    def test_toast_non_blocking_and_auto_dismiss(self):
        self.assertIsNone(anim.toast(None, 'x'))
        self.win.show(); APP.processEvents()
        t = anim.toast(self.win, 'Đã lưu mẫu', kind='success', ms=150)
        self.assertTrue(t.isVisible())
        self.assertEqual(t.property('kind'), 'success')
        r = t.geometry()
        self.assertTrue(self.win.rect().contains(r))  # nằm TRONG cửa sổ
        for i in range(6):
            anim.toast(self.win, f'Thông báo {i}', ms=0)
        self.assertLessEqual(len(self.win._bq_toasts.items), anim._ToastHost.MAX)
        _pump(700)
        with self.assertRaises(RuntimeError):         # tự tắt + tự huỷ
            t.objectName()

    def test_fade_cover_is_cheap_and_self_cleaning(self):
        anim.fade_in(self.win, theme.WINDOW)          # chưa hiện -> không làm gì
        self.assertIsNone(getattr(self.win, '_bq_fade', None))
        self.win.show(); APP.processEvents()
        anim.fade_in(self.win, theme.WINDOW)
        anim.fade_in(self.win, theme.WINDOW)          # gọi dồn: thay lớp cũ, không sập
        cov = self.win._bq_fade
        self.win.resize(700, 450); APP.processEvents()
        self.assertEqual(cov.geometry(), self.win.rect())
        _pump(450)
        with self.assertRaises(RuntimeError):
            cov.objectName()


class QueueNoRestyle(unittest.TestCase):
    """Nhịp hàng đợi KHÔNG được gọi setStyleSheet (restyle cả cây con)."""

    def test_refresh_uses_properties_not_stylesheets(self):
        theme.apply_theme(APP)
        from app import services
        from app.database.db import db
        from app.ui.queue_panel import QueuePanel
        pid = services.create_project('Kênh thiết kế')
        vid = db.insert('INSERT INTO videos(project_id,src_path) VALUES(?,?)', (pid, str(AREA/'a.mp4')))
        ids = {}
        for st, kind in (('running', 'auto'), ('running', 'm1_export_clip'), ('failed', 'auto'),
                         ('done', 'm1_export_clip'), ('pending', 'auto')):
            ids[(st, kind)] = db.insert(
                'INSERT INTO jobs(type,project_id,video_id,status,progress,message,error,payload) '
                'VALUES(?,?,?,?,?,?,?,?)', (kind, pid, vid, st, .4, 'Đang chạy', 'Lỗi thử' if st == 'failed' else None, '{"part_no":1}'))
        panel = QueuePanel(types.SimpleNamespace(pool=Mock()))
        panel.timer.stop(); panel.resize(1100, 500); panel.show(); APP.processEvents()
        panel.refresh(); APP.processEvents()
        rows = panel._rows
        self.assertEqual(rows[ids[('running', 'auto')]]['bar'].property('phase'), 'analyze')
        self.assertEqual(rows[ids[('running', 'm1_export_clip')]]['bar'].property('phase'), 'export')
        self.assertEqual(rows[ids[('failed', 'auto')]]['bar'].property('phase'), 'failed')
        self.assertEqual(rows[ids[('done', 'm1_export_clip')]]['bar'].property('phase'), 'done')
        self.assertTrue(rows[ids[('failed', 'auto')]]['st'].property('link'))
        self.assertEqual(rows[ids[('done', 'm1_export_clip')]]['name'].property('tone'), 'muted')
        self.assertTrue(rows[ids[('failed', 'auto')]]['btn'].property('ghost'))
        self.assertTrue(rows[ids[('running', 'auto')]]['btn'].property('danger'))
        # Gián điệp theo TỪNG widget (không vá lớp QWidget: vá rồi trả lại lớp sip
        # làm hỏng các test chạy sau trong cùng tiến trình pytest).
        calls = []
        spied = [panel] + panel.findChildren(QWidget)
        for w in spied:
            w.setStyleSheet = (lambda o: lambda s: (calls.append(s), o(s))[1])(w.setStyleSheet)
        try:
            for i in range(20):
                db.execute("UPDATE jobs SET progress=? WHERE status='running'", (i / 25,))
                panel.refresh()
        finally:
            for w in spied:
                del w.setStyleSheet
        self.assertEqual(calls, [])
        # trạng thái đổi: running -> failed -> nút đổi variant + đúng repolish
        db.execute("UPDATE jobs SET status='failed',error='x' WHERE id=?", (ids[('running', 'auto')],))
        panel.refresh()
        row = rows[ids[('running', 'auto')]]
        self.assertTrue(row['btn'].property('ghost'))
        self.assertFalse(bool(row['btn'].property('danger')))
        self.assertEqual(row['bar'].property('phase'), 'failed')
        panel.close(); panel.deleteLater(); APP.processEvents()
        db.execute('DELETE FROM jobs WHERE project_id=?', (pid,))


if __name__ == '__main__':
    unittest.main()
