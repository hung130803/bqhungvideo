"""Explicit folder shortcuts; resolve IDs without changing the selected video."""
from pathlib import Path
import os
import re

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget)

from app.database.db import db
from app.ui.layout_tools import fit_dialog


def locations(project_id, video_id, library_root, pipeline_root='', *, include_recorded=True):
    project=db.query_one('SELECT name,export_dir,pipe_src FROM projects WHERE id=?',(project_id,))
    if not project:raise ValueError('Chọn kênh trước khi mở thư mục.')
    # Match the path naming used by StudioPage._export_video exactly.
    name=re.sub(r'[<>:"/\\|?*]', '_', project['name'] or 'Kenh').strip().strip('. ') or 'Kenh'
    override=(project['export_dir'] or '').strip()
    channel=Path(override) if override else Path(library_root)/'Đã xuất'/name
    result={'channel':channel,'video':None,'source':None,'pipeline':None,
            'recorded':[],'channel_name':project['name']}
    source_override=(project['pipe_src'] or '').strip() or override
    if source_override:result['pipeline']=Path(source_override)
    elif pipeline_root:result['pipeline']=Path(pipeline_root)/project['name']
    if video_id:
        video=db.query_one('SELECT src_path FROM videos WHERE id=? AND project_id=?',(video_id,project_id))
        if not video:raise ValueError('Video không thuộc kênh đang chọn hoặc đã bị xóa. Hãy chọn lại video.')
        if video['src_path']:
            from app.modules.m1_highlight import _safe_name
            source=Path(video['src_path'])
            result['source']=source.parent
            result['video']=channel if override else channel/(_safe_name(source.stem) or f'video_{video_id}')
        rows=db.query("SELECT export_path FROM clips WHERE video_id=? AND COALESCE(export_path,'')<>'' "
                      'ORDER BY id DESC',(video_id,))
    elif include_recorded:
        rows=db.query("SELECT c.export_path FROM clips c JOIN videos v ON v.id=c.video_id "
                      "WHERE v.project_id=? AND COALESCE(c.export_path,'')<>'' ORDER BY c.id DESC",
                      (project_id,))
    else:
        rows=[]
    for row in rows:
        path=Path(row['export_path']).parent
        if path not in result['recorded']:result['recorded'].append(path)
    return result


def open_directory(path, *, create=False):
    if path is None:raise ValueError('Chưa có đường dẫn cho mục này.')
    path=Path(path)
    if not path.is_absolute():raise ValueError(f'Đường dẫn chưa đầy đủ: {path}. Hãy chọn lại thư mục lưu.')
    if create:path.mkdir(parents=True,exist_ok=True)
    if not path.is_dir():
        raise FileNotFoundError(f'Thư mục không tồn tại hoặc ổ đĩa chưa kết nối: {path}')
    # A directory-only check prevents a stored path from launching an EXE.
    # Let failures reach the caller; do not claim Explorer opened on failure.
    os.startfile(str(path))
    return f'Đã mở: {path}'


def copy_path(path):
    if path is None:raise ValueError('Chưa có đường dẫn cho mục này.')
    QApplication.clipboard().setText(str(path))
    return f'Đã sao chép đường dẫn: {path}'


def show_locations(parent, data):
    dlg=QDialog(parent);dlg.setWindowTitle('Thư mục của kênh — '+data['channel_name'])
    root=QVBoxLayout(dlg)
    note=QLabel('Thư mục lưu hiện tại và nơi đã ghi file trước đây có thể khác nhau nếu bạn đổi tên kênh hoặc đổi nơi lưu. Mở thư mục không di chuyển file.')
    note.setWordWrap(True);root.addWidget(note)
    scroll=QScrollArea();scroll.setWidgetResizable(True)
    content=QWidget();items=QVBoxLayout(content);scroll.setWidget(content);root.addWidget(scroll,1)
    feedback=QLabel('');feedback.setWordWrap(True)
    feedback.setTextFormat(Qt.TextFormat.PlainText)

    def act(path,copy=False,create=False):
        try:feedback.setText(copy_path(path) if copy else open_directory(path,create=create))
        except Exception as error:feedback.setText('Không thực hiện được: '+str(error))

    rows=[('Kênh — nơi lưu Part hiện tại',data['channel'],True),
          ('Video — nơi lưu Part theo cấu hình',data['video'],False),
          ('Video gốc — thư mục nguồn',data['source'],False),
          ('Dây chuyền — thư mục lấy video',data['pipeline'],False)]
    known={p for _,p,_ in rows if p}
    rows += [('Part — đường dẫn đã ghi trước đây',p,False) for p in data['recorded'] if p not in known]
    for label,path,create in rows:
        heading=QLabel(label);items.addWidget(heading)
        line=QHBoxLayout();field=QLineEdit(str(path) if path else 'Chưa có / chưa chọn video')
        field.setReadOnly(True);field.setCursorPosition(0);field.setToolTip(field.text());line.addWidget(field,1)
        op=QPushButton('Mở');op.setEnabled(path is not None)
        op.clicked.connect(lambda _=False,p=path,c=create:act(p,create=c));line.addWidget(op)
        cp=QPushButton('Sao chép');cp.setEnabled(path is not None)
        cp.clicked.connect(lambda _=False,p=path:act(p,copy=True));line.addWidget(cp)
        items.addLayout(line)
    items.addStretch(1);root.addWidget(feedback)
    close=QPushButton('Đóng');close.clicked.connect(dlg.accept);root.addWidget(close)
    fit_dialog(dlg,900,560);dlg.exec()


def perform(parent, kind, project_id, video_id, library_root, pipeline_root=''):
    try:
        data=locations(project_id,video_id,library_root,pipeline_root)
        if kind=='details':
            show_locations(parent,data)
            return 'Đã xem các thư mục của kênh: '+data['channel_name']
        if kind=='copy':return copy_path(data['channel'])
        if kind=='video':
            # Existing exports remain findable after a rename/root change.
            candidates=[p for p in data['recorded'] if p.is_absolute() and p.is_dir()]
            if len(candidates)>1:
                show_locations(parent,data)
                return 'Part của video được ghi ở nhiều thư mục; chọn Mở ở đúng đường dẫn.'
            if candidates:return open_directory(candidates[0])
            if data['video'] is None:raise ValueError('Chọn video trước khi mở thư mục Part.')
            return open_directory(data['video'])
        if kind not in ('channel','source','pipeline'):raise ValueError('Thao tác thư mục không hợp lệ.')
        return open_directory(data[kind],create=kind=='channel')
    except Exception as error:
        return 'Không thực hiện được: '+str(error)
