"""Theo dõi hàng loạt theo video; mọi thao tác vẫn đi qua worker hiện có."""
import unicodedata

from PyQt6.QtCore import Qt,QTimer,pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QAbstractItemView,QComboBox,QDialog,QHBoxLayout,QHeaderView,
    QLabel,QLineEdit,QMenu,QMessageBox,QPlainTextEdit,QPushButton,QTableWidget,QTableWidgetItem,
    QVBoxLayout,QWidget)

from app.services_batch import snapshot
from app.ui.theme import ACCENT,DANGER,MUTED,SUCCESS,WARN


def folded(text):
    text=unicodedata.normalize('NFD',text.lower().replace('đ','d'))
    return ''.join(c for c in text if unicodedata.category(c)!='Mn')


class BatchPage(QWidget):
    open_video=pyqtSignal(int,int)
    open_folder=pyqtSignal(int,int,str)
    configure_pipeline=pyqtSignal()
    PAGE_SIZE=100

    def __init__(self,state):
        super().__init__()
        self.state=state
        self.records=[]
        self.total=0
        self.page=0
        self._visible_ids=[]
        self._rendered=None
        root=QVBoxLayout(self)
        root.setContentsMargins(8,16,8,12)
        title=QLabel('Theo dõi hàng loạt')
        title.setStyleSheet('font-size:22px;font-weight:700;')
        top=QHBoxLayout();top.addWidget(title,1)
        config=QPushButton('Cấu hình && chạy Dây chuyền')
        config.setProperty('primary',True)
        config.clicked.connect(self.configure_pipeline.emit)
        top.addWidget(config);root.addLayout(top)
        note=QLabel('Mỗi dòng là một video. Phân tích, xuất Part và dọn gốc là các bước riêng. '
                    'Bảng dùng trạng thái đã ghi trong ứng dụng; không quét lại file trên ổ đĩa.')
        note.setWordWrap(True);note.setStyleSheet(f'color:{MUTED};')
        root.addWidget(note)
        self.summary=QLabel();self.summary.setWordWrap(True)
        root.addWidget(self.summary)
        row=QHBoxLayout()
        self.search=QLineEdit();self.search.setPlaceholderText('Tìm kênh hoặc video… (có thể gõ không dấu)')
        self.search.setClearButtonEnabled(True);row.addWidget(self.search,1)
        self.group=QComboBox();self.group.addItem('Tất cả nhóm','')
        row.addWidget(self.group)
        self.filter=QComboBox()
        for label,value in [('Tất cả trạng thái',''),('Đang chạy','running'),('Đang chờ','pending'),
                            ('Có lỗi','failed'),('Đã hủy','canceled'),('Chưa xuất đủ','ready'),
                            ('Đã xuất đủ','done'),('Chưa có clip','idle')]:
            self.filter.addItem(label,value)
        row.addWidget(self.filter)
        refresh=QPushButton('Làm mới');refresh.clicked.connect(self.refresh);row.addWidget(refresh)
        root.addLayout(row)
        self.table=QTableWidget(0,6)
        self.table.setHorizontalHeaderLabels(['Kênh / Nhóm','Video','Bước hiện tại','Part','Video gốc','Chi tiết'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(42)
        header=self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(5,QHeaderView.ResizeMode.Stretch)
        for col,width in enumerate((180,230,175,60,170)):
            self.table.setColumnWidth(col,width)
        self.table.setMinimumHeight(160)
        self.table.itemDoubleClicked.connect(lambda _item:self.open_selected())
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.folder_menu)
        root.addWidget(self.table,1)
        self.feedback=QLabel('Chọn một video để xem, thử lại hoặc hủy đúng video đó.')
        self.feedback.setWordWrap(True);root.addWidget(self.feedback)
        actions=QHBoxLayout()
        self.open_btn=QPushButton('Mở video && clip');self.open_btn.setProperty('primary',True)
        self.open_btn.clicked.connect(self.open_selected);actions.addWidget(self.open_btn)
        self.folder_btn=QPushButton('Mở thư mục kênh')
        self.folder_btn.setToolTip('Mở thư mục kênh của dòng đang chọn. Chuột phải trên dòng để mở nguồn, Part hoặc sao chép đường dẫn.')
        self.folder_btn.clicked.connect(lambda:self.folder_selected('channel'));actions.addWidget(self.folder_btn)
        self.detail_btn=QPushButton('Xem chi tiết');self.detail_btn.clicked.connect(self.details)
        actions.addWidget(self.detail_btn)
        self.retry_btn=QPushButton('Thử lại việc lỗi/đã hủy');self.retry_btn.clicked.connect(self.retry_selected)
        actions.addWidget(self.retry_btn)
        self.cancel_btn=QPushButton('Hủy việc của video này');self.cancel_btn.setProperty('danger',True)
        self.cancel_btn.clicked.connect(self.cancel_selected);actions.addWidget(self.cancel_btn)
        actions.addStretch(1);root.addLayout(actions)
        pages=QHBoxLayout();self.page_label=QLabel();pages.addWidget(self.page_label,1)
        self.previous=QPushButton('Trước');self.previous.clicked.connect(lambda:self.change_page(-1))
        self.next=QPushButton('Sau');self.next.clicked.connect(lambda:self.change_page(1))
        pages.addWidget(self.previous);pages.addWidget(self.next);root.addLayout(pages)
        self.search.textChanged.connect(self.apply_filters)
        self.group.currentIndexChanged.connect(self.apply_filters)
        self.filter.currentIndexChanged.connect(self.apply_filters)
        self.timer=QTimer(self);self.timer.setInterval(2500);self.timer.timeout.connect(self.refresh)
        self._selection_changed()

    def showEvent(self,event):
        super().showEvent(event)
        self.refresh();self.timer.start()

    def hideEvent(self,event):
        self.timer.stop();super().hideEvent(event)

    def refresh(self):
        try:
            self.records,self.total=snapshot()
        except Exception as error:
            self.feedback.setText('Không đọc được tiến trình: '+str(error))
            return
        groups=sorted({r['group'] for r in self.records})
        existing=[self.group.itemData(i) for i in range(1,self.group.count())]
        if existing!=groups:
            selected=self.group.currentData()
            self.group.blockSignals(True)
            self.group.clear();self.group.addItem('Tất cả nhóm','')
            for g in groups:self.group.addItem(g,g)
            self.group.setCurrentIndex(max(0,self.group.findData(selected)))
            self.group.blockSignals(False)
        counts={s:sum(r['state']==s for r in self.records) for s in ('running','pending','failed','ready','done')}
        self.summary.setText(f"{counts['running']} video chạy  ·  {counts['pending']} chờ  ·  "
            f"{counts['failed']} có lỗi  ·  {counts['ready']} chưa xuất đủ  ·  {counts['done']} đã xuất đủ")
        self.render()

    def apply_filters(self,*_):
        self.page=0;self.render()

    def change_page(self,delta):
        self.page=max(0,self.page+delta);self.render()

    def selected(self):
        row=self.table.currentRow()
        if 0<=row<len(self._visible_ids):
            vid=self._visible_ids[row]
            return next((r for r in self.records if r['id']==vid),None)
        return None

    def render(self):
        selected=self.selected()
        selected_id=selected['id'] if selected else None
        query=folded(self.search.text().strip())
        group,status=self.group.currentData(),self.filter.currentData()
        filtered=[r for r in self.records if (not group or r['group']==group)
                  and (not status or r['state']==status)
                  and (not query or query in folded(r['channel']+' '+r['video']))]
        self.page=min(self.page,max(0,(len(filtered)-1)//self.PAGE_SIZE))
        start=self.page*self.PAGE_SIZE;rows=filtered[start:start+self.PAGE_SIZE]
        signature=[(r['id'],r['stage'],r['parts'],r['source'],r['detail'],r['channel'],r['group'],r['video'],r['path']) for r in rows]
        if signature!=self._rendered:
            self.table.blockSignals(True)
            self.table.setUpdatesEnabled(False)
            self.table.setRowCount(len(rows))
            self._visible_ids=[r['id'] for r in rows]
            for row,r in enumerate(rows):
                values=(r['channel']+' / '+r['group'],r['video'],r['stage'],r['parts'],r['source'],r['detail'])
                for col,value in enumerate(values):
                    item=self.table.item(row,col)
                    if item is None:item=QTableWidgetItem();self.table.setItem(row,col,item)
                    if item.text()!=value:item.setText(value)
                    item.setToolTip(value if col!=1 else r['path'])
                    if col==2:item.setForeground(QColor({'running':ACCENT,'failed':DANGER,'done':SUCCESS,'pending':WARN}.get(r['state'],MUTED)))
            if selected_id in self._visible_ids:self.table.selectRow(self._visible_ids.index(selected_id))
            else:self.table.clearSelection();self.table.setCurrentCell(-1,-1)
            self.table.setUpdatesEnabled(True);self.table.blockSignals(False)
            self._rendered=signature
        bound=f" · Đang lấy {len(self.records)}/{self.total} video gần nhất/đang chạy" if self.total>len(self.records) else ''
        self.page_label.setText(f"{len(filtered)} video khớp · Hiện {start+1 if rows else 0}–{start+len(rows)}"+bound)
        self.previous.setEnabled(self.page>0);self.next.setEnabled(start+len(rows)<len(filtered))
        self._selection_changed()

    def _selection_changed(self):
        r=self.selected()
        self.open_btn.setEnabled(bool(r));self.detail_btn.setEnabled(bool(r))
        self.folder_btn.setEnabled(bool(r))
        self.cancel_btn.setEnabled(bool(r and r['job_ids']))
        self.retry_btn.setEnabled(bool(r and r['retry_ids']))

    def open_selected(self):
        r=self.selected()
        if r:self.open_video.emit(r['pid'],r['id'])

    def folder_selected(self,kind):
        r=self.selected()
        if r:self.open_folder.emit(r['pid'],r['id'],kind)

    def folder_menu(self,pos):
        row=self.table.rowAt(pos.y())
        if row<0:return
        self.table.selectRow(row)
        menu=QMenu(self)
        for title,kind in [('Mở thư mục kênh','channel'),('Mở thư mục Part của video','video'),
                           ('Mở thư mục video gốc','source'),('Sao chép đường dẫn thư mục kênh','copy'),
                           ('Xem tất cả đường dẫn…','details')]:
            menu.addAction(title,lambda _=False,k=kind:self.folder_selected(k))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def cancel_selected(self):
        r=self.selected()
        if not r:return
        if QMessageBox.question(self,'Hủy xử lý video',f"Hủy {len(r['job_ids'])} việc đang chạy/chờ của “{r['video']}”? "
                'Các video khác tiếp tục chạy.',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        # Refresh this video's IDs after the confirmation; a job may have
        # finished or a new job may have started while the dialog was open.
        vid=r['id'];self.refresh()
        r=next((item for item in self.records if item['id']==vid),None)
        if not r:return
        for jid in r['job_ids']:self.state.pool.cancel(jid)
        self.feedback.setText('Đã gửi yêu cầu hủy các việc của video đã chọn.')
        self.refresh()

    def retry_selected(self):
        r=self.selected()
        if not r:return
        vid=r['id'];self.refresh()
        r=next((item for item in self.records if item['id']==vid),None)
        if not r or not r['retry_ids']:return
        for jid in r['retry_ids']:self.state.pool.retry(jid)
        self.feedback.setText('Đã yêu cầu thử lại các việc lỗi/đã hủy của video đã chọn.')
        self.refresh()

    def details(self):
        r=self.selected()
        if not r:return
        dlg=QDialog(self);dlg.setWindowTitle('Chi tiết: '+r['video']);dlg.resize(820,540)
        lay=QVBoxLayout(dlg);text=QPlainTextEdit();text.setReadOnly(True)
        lines=[r['channel'],r['path'],f"{r['stage']} · Part {r['parts']} · {r['source']}",r['note'],'']
        for j in r['jobs'][:100]:
            lines.append(f"#{j['id']} · {j['type']} · {j['status']}\n{j['message'] or ''}\n{j['error'] or ''}\n")
        text.setPlainText('\n'.join(lines));lay.addWidget(text,1)
        close=QPushButton('Đóng');close.clicked.connect(dlg.accept);lay.addWidget(close)
        dlg.exec()
