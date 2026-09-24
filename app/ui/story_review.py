"""Expose source evidence and narration instead of opaque AI quality scores."""
import json
from pathlib import Path
from PyQt6.QtCore import QUrl,Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QApplication,QLabel,QTableWidget,QTableWidgetItem,QHeaderView,QPlainTextEdit,QPushButton,QAbstractItemView,QMessageBox
from app.ui.layout_tools import fit_dialog


def show_story(parent,meta,clip_id=None):
    from app.ai.story_quality import approve_script,digest,is_approved
    revision=digest(meta);saved=False
    dlg=QDialog(parent);dlg.setWindowTitle('Kịch bản & căn cứ từ video nguồn')
    lay=QVBoxLayout(dlg)
    note=QLabel('Groq có thể nhận sai hình. Mở video nguồn để đối chiếu mốc thời gian; nhấp đúp ô Lời kể để sửa. Chỉ bấm Lưu & duyệt khi đã xem từng câu. Đóng cửa sổ không có nghĩa là duyệt.')
    note.setWordWrap(True);lay.addWidget(note)
    parts=meta['parts'] if clip_id is not None else meta.get('rendered_parts') or meta['parts']
    state=QLabel(('Đã duyệt' if is_approved(meta) else 'CHỜ DUYỆT')+' · Giữ nguyên lời đã duyệt. Câu quá dài sẽ yêu cầu bạn viết ngắn rồi duyệt lại.')
    state.setWordWrap(True);lay.addWidget(state)
    if (meta.get('review') or {}).get('approved') is False:
        warning=QLabel('AI chưa thống nhất được nội dung: '+str(meta['review'].get('issues','Cần đối chiếu lại nguồn.')))
        warning.setWordWrap(True);warning.setTextFormat(Qt.TextFormat.PlainText);lay.addWidget(warning)
    table=QTableWidget(len(parts),3);table.setHorizontalHeaderLabels(['Mốc nguồn','Vai','Lời kể'])
    table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.EditKeyPressed if clip_id is not None else QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
    for i,p in enumerate(parts):
        for j,value in enumerate((f"{p['start']:.1f}–{p['end']:.1f}s",'Giữ tiếng gốc' if p['mode']=='orig' else 'Thuyết minh',p['text'])):
            item=QTableWidgetItem(value)
            if j!=2 or p['mode']!='narrate':item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(i,j,item)
    table.resizeRowsToContents();lay.addWidget(table,1)
    evidence=QPlainTextEdit();evidence.setReadOnly(True);lay.addWidget(evidence,1)
    def selected():
        i=table.currentRow()
        if i<0:return
        p=parts[i]
        try:
            u=json.loads(p['evidence'])
            text='LỜI GỐC\n'+(u.get('transcript','') or '(Không có lời chép trong đoạn này)')
            for n,obs in enumerate(u.get('observations',[]),1):
                text+=f"\n\nHÌNH {n} · {obs.get('at','?')}s (mô tả của AI, cần xem lại nguồn)\n{obs.get('visible','')}\nChưa chắc: {obs.get('uncertain','')}"
        except (ValueError,KeyError):text=p.get('evidence','Chưa có căn cứ')
        evidence.setPlainText(text)
    table.itemSelectionChanged.connect(selected)
    if parts:table.selectRow(0)
    row=QHBoxLayout();lay.addLayout(row)
    source=(meta.get('source_signature') or [''])[0]
    open_source=QPushButton('Mở video nguồn');open_source.setEnabled(bool(source) and Path(source).is_file())
    open_source.clicked.connect(lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(source)));row.addWidget(open_source)
    copy=QPushButton('Chép kịch bản');copy.clicked.connect(lambda:QApplication.clipboard().setText('\n\n'.join(
        f"{p['start']:.1f}–{p['end']:.1f}s: {table.item(i,2).text() or '[Giữ tiếng gốc]'}" for i,p in enumerate(parts))));row.addWidget(copy)
    if clip_id is not None:
        approve=QPushButton('Lưu & duyệt');row.addWidget(approve)
        def save():
            nonlocal saved
            try:approve_script(clip_id,revision,[table.item(i,2).text() for i in range(len(parts))])
            except (RuntimeError,ValueError,OSError) as exc:
                QMessageBox.warning(dlg,'Chưa duyệt được',str(exc));return
            saved=True;dlg.accept()
        approve.clicked.connect(save)
    row.addStretch();close=QPushButton('Đóng');close.clicked.connect(dlg.accept);row.addWidget(close)
    fit_dialog(dlg,1000,650);dlg.exec()
    return saved
