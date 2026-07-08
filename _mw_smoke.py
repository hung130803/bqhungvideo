# -*- coding: utf-8 -*-
"""Smoke MainWindow offscreen voi DB gia (artifact test, se xoa)."""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
TMP = tempfile.mkdtemp(prefix="mw_smoke_")
os.environ["BQ_DB_PATH"] = os.path.join(TMP, "test.db")
sys.path.insert(0, r"D:\claude\ai-content-studio")

from PyQt6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])
from app.ui.theme import apply_theme  # noqa: E402
apply_theme(app)
from app.ui.state import AppState  # noqa: E402
from app.ui.main_window import MainWindow  # noqa: E402

state = AppState()
mw = MainWindow(state)
mw.show()
app.processEvents()
mw.resize(1240, 840)
app.processEvents()
mw.grab().save(r"D:\claude\ai-content-studio\_mw_smoke.png")
mw.close()
app.processEvents()
print("MainWindow smoke: OK")
