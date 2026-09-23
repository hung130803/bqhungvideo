"""Channel navigation and explicit, isolated path editing for the batch view."""
import json
import re
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QDialog,
    QFileDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton,
    QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from app.database.db import db
from app.ui.appsettings import app_settings
from app.ui.folder_access import locations
from app.ui.theme import MUTED


def natural(value):
    return [int(s) if s.isdigit() else s.casefold() for s in re.split(r'(\d+)', value)]


def save_paths(pid, output, source, expected):
    """Validate first, then check freshness/busy state and update atomically."""
    output, source = output.strip(), source.strip()
    for value in (output, source):
        if value and (not Path(value).is_absolute() or not Path(value).is_dir()):
            raise ValueError('Chọn đường dẫn đầy đủ tới thư mục đang tồn tại: '+value)
    if db.corrupt_live:
        raise ValueError('Cơ sở dữ liệu đang lỗi; chưa thay đổi đường dẫn.')
    con = db.conn()
    con.execute('BEGIN IMMEDIATE')
    try:
        row = con.execute('SELECT export_dir,pipe_src FROM projects WHERE id=?', (pid,)).fetchone()
        if not row:
            raise ValueError('Kênh không còn tồn tại. Hãy làm mới danh sách.')
        if tuple((r or '').strip() for r in row) != tuple(expected):
            raise ValueError('Đường dẫn vừa được thay đổi ở nơi khác. Đóng và mở lại để kiểm tra.')
        active = con.execute("SELECT 1 FROM jobs WHERE project_id=? AND status IN ('pending','running') LIMIT 1", (pid,)).fetchone()
        tracked = con.execute("SELECT 1 FROM pipeline_files WHERE project_id=? AND status='taken' LIMIT 1", (pid,)).fetchone()
        if active or tracked:
            raise ValueError('Kênh còn việc đang chạy/chờ hoặc video Dây chuyền chưa hoàn tất. Đợi xử lý xong trước khi đổi đường dẫn.')
        con.execute('UPDATE projects SET export_dir=?,pipe_src=? WHERE id=?', (output, source, pid))
        con.commit()
    except Exception:
        con.rollback()
        raise


class ChannelPathsDialog(QDialog):
    def __init__(self, pid, parent=None):
        super().__init__(parent)
        self.pid = pid
        row = db.query_one('SELECT name,export_dir,pipe_src FROM projects WHERE id=?', (pid,))
        if not row:
            raise ValueError('Kênh không còn tồn tại.')
        self.expected = tuple((row[k] or '').strip() for k in ('export_dir','pipe_src'))
        self.setWindowTitle('Đường dẫn kênh — '+row['name'])
        self.resize(640, 340)
        layout = QVBoxLayout(self)
        note = QLabel('Thay đường dẫn áp dụng cho lần xử lý sau; file đã có giữ ở vị trí cũ. '
                      'Thư mục lưu riêng nhận Part trực tiếp. Nếu không đặt nguồn riêng, '
                      'Dây chuyền dùng thư mục lưu riêng hoặc thư mục gốc Dây chuyền theo cấu hình.')
        note.setWordWrap(True); layout.addWidget(note)
        self.output = QLineEdit(self.expected[0]); self.source = QLineEdit(self.expected[1])
        for label, edit, hint in (
            ('Thư mục lưu Part riêng', self.output, 'Để trống: Đã xuất / tên kênh / tên video'),
            ('Thư mục video nguồn Dây chuyền riêng', self.source, 'Để trống: dùng nguồn theo cấu hình hiện tại')):
            layout.addWidget(QLabel(label))
            edit.setPlaceholderText(hint)
            line = QHBoxLayout(); line.addWidget(edit, 1)
            browse = QPushButton('Chọn…')
            browse.clicked.connect(lambda _=False, e=edit: self.browse(e))
            clear = QPushButton('Mặc định'); clear.clicked.connect(lambda _=False, e=edit: e.clear())
            line.addWidget(browse); line.addWidget(clear); layout.addLayout(line)
        self.error = QLabel(); self.error.setWordWrap(True)
        self.error.setTextFormat(Qt.TextFormat.PlainText); layout.addWidget(self.error)
        layout.addStretch(1)
        line = QHBoxLayout(); line.addStretch(1)
        save = QPushButton('Lưu đường dẫn'); save.setProperty('primary', True); save.clicked.connect(self.save)
        cancel = QPushButton('Hủy'); cancel.clicked.connect(self.reject)
        line.addWidget(save); line.addWidget(cancel); layout.addLayout(line)

    def browse(self, edit):
        path = QFileDialog.getExistingDirectory(self, 'Chọn thư mục cho kênh', edit.text())
        if path: edit.setText(path)

    def save(self):
        try:
            save_paths(self.pid, self.output.text(), self.source.text(), self.expected)
        except Exception as error:
            self.error.setText(str(error)); return
        self.accept()


class BatchChannels(QWidget):
    selected = pyqtSignal(int)
    manage = pyqtSignal()
    add = pyqtSignal(str)
    edit = pyqtSignal(int)
    paths = pyqtSignal(int)
    open_folder = pyqtSignal(int, int, str)

    def __init__(self):
        super().__init__()
        self.settings = app_settings()
        self.pid = 0
        self.projects = []
        self._signature = None
        self._group = None
        self.setMinimumWidth(275)
        layout = QVBoxLayout(self); layout.setContentsMargins(0,0,8,0);layout.setSpacing(5)
        row = QHBoxLayout(); row.addWidget(QLabel('NHÓM ĐÃ LƯU'),1)
        manage = QPushButton('Quản lý'); manage.clicked.connect(self.manage.emit); row.addWidget(manage)
        layout.addLayout(row)
        self.group = QComboBox(); self.group.setMinimumContentsLength(10)
        self.group.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        layout.addWidget(self.group)
        self.search = QLineEdit(); self.search.setPlaceholderText('Tìm kênh trong nhóm…'); self.search.setClearButtonEnabled(True)
        layout.addWidget(self.search)
        self.order=QComboBox()
        self.order.addItem('Xếp kênh: tên A → Z','name')
        self.order.addItem('Xếp kênh: thư mục nguồn','path')
        self.order.setToolTip('STT là vị trí trong cách xếp đang chọn; không phải số thư mục kênh.')
        layout.addWidget(self.order)
        self.table = QTableWidget(0,3)
        self.table.setHorizontalHeaderLabels(['STT','Kênh','Hồ sơ'])
        self.table.horizontalHeaderItem(2).setToolTip('Số video từng nhập vào ứng dụng, gồm cả lịch sử; không phải số file hiện trong thư mục.')
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0,42)
        self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2,65)
        self.table.verticalHeader().hide(); self.table.verticalHeader().setDefaultSectionSize(46)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setMinimumHeight(100); layout.addWidget(self.table,1)
        self.count = QLabel(); self.count.setWordWrap(True); layout.addWidget(self.count)
        row = QHBoxLayout()
        self.add_btn = QPushButton('+ Kênh'); self.add_btn.clicked.connect(lambda: self.add.emit(self.group.currentData() or ''))
        self.edit_btn = QPushButton('Sửa tên / nhóm'); self.edit_btn.clicked.connect(lambda: self.edit.emit(self.pid))
        row.addWidget(self.add_btn); row.addWidget(self.edit_btn); layout.addLayout(row)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setMinimumHeight(140)
        scroll.setMaximumHeight(250)
        content = QWidget(); info = QVBoxLayout(content); info.setContentsMargins(8,8,8,8)
        self.title = QLabel('Chọn kênh'); self.title.setWordWrap(True); self.title.setTextFormat(Qt.TextFormat.PlainText)
        info.addWidget(self.title)
        self.output = QLineEdit(); self.source = QLineEdit()
        for text, field in (('Thư mục xuất hiện tại',self.output),('Nguồn Dây chuyền',self.source)):
            label = QLabel(text); label.setStyleSheet(f'color:{MUTED};'); info.addWidget(label)
            field.setReadOnly(True); info.addWidget(field)
        row = QHBoxLayout()
        self.open_btn = QPushButton('Mở nơi xuất'); self.open_btn.clicked.connect(lambda: self.open_folder.emit(self.pid,0,'channel'))
        self.open_btn.setToolTip('Nơi xuất hiện tại theo cấu hình. Part cũ có thể ở nơi khác; chọn video rồi Mở Part đã xuất.')
        self.copy_btn = QPushButton('Chép'); self.copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(self.output.text()))
        self.source_btn=QPushButton('Mở nguồn')
        self.source_btn.clicked.connect(lambda: self.open_folder.emit(self.pid,0,'pipeline'))
        row.addWidget(self.open_btn); row.addWidget(self.source_btn); row.addWidget(self.copy_btn); info.addLayout(row)
        self.paths_btn = QPushButton('Thêm / đổi đường dẫn…'); self.paths_btn.clicked.connect(lambda: self.paths.emit(self.pid))
        info.addWidget(self.paths_btn); scroll.setWidget(content); layout.addWidget(scroll)
        self.group.currentIndexChanged.connect(self._change_group)
        self.search.textChanged.connect(self.render)
        self.order.currentIndexChanged.connect(self.render)
        self.table.itemSelectionChanged.connect(self._choose)

    def refresh(self):
        projects = [dict(r) for r in db.query('SELECT p.*,COUNT(v.id) AS videos FROM projects p '
                    'LEFT JOIN videos v ON v.project_id=p.id GROUP BY p.id')]
        activity = {r['project_id']:dict(r) for r in db.query(
            "SELECT project_id,COUNT(DISTINCT CASE WHEN status='running' THEN video_id END) AS running,"
            "COUNT(DISTINCT CASE WHEN status='pending' THEN video_id END) AS waiting "
            "FROM jobs WHERE status IN ('running','pending') GROUP BY project_id")}
        for p in projects:
            p['running']=activity.get(p['id'],{}).get('running',0)
            p['waiting']=activity.get(p['id'],{}).get('waiting',0)
        try:
            extra = json.loads(self.settings.value('chan_groups_extra','[]') or '[]')
            extra = [g for g in extra if isinstance(g,str) and g.strip()] if isinstance(extra,list) else []
        except (ValueError,TypeError): extra = []
        groups = sorted({p['grp'] or '' for p in projects}|set(extra), key=natural)
        old = self.group.currentData() if self.group.count() else self.settings.value('batch_group',self.settings.value('chan_group',''))
        if groups != [self.group.itemData(i) for i in range(self.group.count())]:
            self.group.blockSignals(True); self.group.clear()
            for n,g in enumerate(groups,1): self.group.addItem(f'{n}. {g or "Chưa phân nhóm"}',g)
            self.group.setCurrentIndex(max(0,self.group.findData(old))); self.group.blockSignals(False)
        self.projects = projects
        self.render()

    def _change_group(self):
        self.search.blockSignals(True); self.search.clear(); self.search.blockSignals(False)
        self.render()

    def render(self, *_):
        # Import here to keep the accent folding shared without an import cycle.
        from app.ui.batch_page import folded
        group = self.group.currentData()
        changed = self._group != group
        self._group = group
        candidates = sorted([p for p in self.projects if (p['grp'] or '')==group], key=lambda p:(natural(p['name']),p['id']))
        if self.order.currentData()=='path':
            candidates.sort(key=lambda p:(natural(p['pipe_src'] or p['export_dir'] or ''),natural(p['name']),p['id']))
        query = folded(self.search.text().strip())
        rows = [(n,p) for n,p in enumerate(candidates,1) if query in folded(p['name'])]
        keep = self.pid
        if changed or not keep:
            try: keep = int(self.settings.value('batch_channel',0))
            except (ValueError,TypeError): keep = 0
        ids = [p['id'] for _,p in rows]
        selected = keep if keep in ids else (ids[0] if ids else 0)
        signature = [(n,p['id'],p['name'],p['videos'],p['export_dir'],p['pipe_src'],p['running'],p['waiting']) for n,p in rows]
        if signature != self._signature or self.pid != selected:
            self.table.blockSignals(True); self.table.setRowCount(len(rows))
            for row,(n,p) in enumerate(rows):
                for col,value in enumerate((str(n),p['name'],str(p['videos']))):
                    item = QTableWidgetItem(value); item.setToolTip(value)
                    item.setData(Qt.ItemDataRole.UserRole,p['id']); self.table.setItem(row,col,item)
                activity = f"{p['running']} chạy · {p['waiting']} chờ"
                self.table.item(row,1).setToolTip(p['name']+'\n'+activity+'\n'+(p['export_dir'] or 'Thư mục lưu mặc định'))
                if p['running'] or p['waiting']:
                    self.table.item(row,2).setText(str(p['videos'])+'\n'+(f"{p['running']} chạy" if p['running'] else f"{p['waiting']} chờ"))
                    self.table.item(row,2).setToolTip(activity+' (số video; một video có thể vừa chạy vừa có việc chờ)')
            if selected: self.table.selectRow(ids.index(selected))
            else: self.table.setCurrentCell(-1,-1); self.table.clearSelection()
            self.table.blockSignals(False); self._signature = signature
        self.count.setText(f'{len(rows)}/{len(candidates)} kênh · {sum(p["videos"] for p in candidates)} hồ sơ đã nhập trong nhóm'
            f"\n{sum(p['running'] for p in candidates)} video có việc chạy · {sum(p['waiting'] for p in candidates)} có việc chờ")
        self.add_btn.setEnabled(group is not None)
        self._set_selected(selected)

    def _choose(self):
        item = self.table.item(self.table.currentRow(),0)
        self._set_selected(int(item.data(Qt.ItemDataRole.UserRole)) if item else 0)

    def _set_selected(self, pid):
        changed = pid != self.pid
        self.pid = pid
        self.settings.setValue('batch_group',self.group.currentData() or '')
        if pid: self.settings.setValue('batch_channel',pid)
        p = next((p for p in self.projects if p['id']==pid),None)
        self.title.setText(p['name'] if p else 'Nhóm chưa có kênh' if not self.projects else 'Chưa chọn kênh')
        for b in (self.open_btn,self.source_btn,self.copy_btn,self.paths_btn,self.edit_btn): b.setEnabled(bool(p))
        output=source=''
        if p:
            from config import DATA_DIR
            # Resolve current configuration without scanning disks or creating folders.
            root = self.settings.value('lib_root','') or str(DATA_DIR/'KhoVideo')
            data = locations(pid,None,root,self.settings.value('pipe_root','') or '',include_recorded=False)
            output=str(data['channel'])
            source=str(data['pipeline']) if data['pipeline'] else ''
            self.source.setPlaceholderText('Chưa cấu hình nguồn')
        for field,value in ((self.output,output),(self.source,source)):
            if field.text()!=value:
                field.setText(value);field.setCursorPosition(0)
            field.setToolTip(value)
        if changed: self.selected.emit(pid)

    def select_project(self, pid):
        self.refresh()
        p = next((p for p in self.projects if p['id']==pid),None)
        if not p: return
        self.settings.setValue('batch_channel',pid)
        self.pid = pid
        self.search.clear()
        self.group.setCurrentIndex(self.group.findData(p['grp'] or ''))
        self._signature = None; self.render()
        self.selected.emit(pid)
