"""Theo dõi hàng loạt theo video; mọi thao tác vẫn đi qua worker hiện có."""
import unicodedata

from PyQt6.QtCore import Qt,QTimer,pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QAbstractItemView,QComboBox,QDialog,QHBoxLayout,QHeaderView,
    QLabel,QLineEdit,QMenu,QMessageBox,QPlainTextEdit,QPushButton,QTableWidget,QTableWidgetItem,
    QVBoxLayout,QWidget,QSplitter)

from app.services_batch import snapshot
from app.ui.batch_files import FileInspector, fingerprint, file_labels, file_warning
from app.ui.batch_channels import natural
from app.ui.batch_visibility import hidden, set_hidden
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
        self._refreshing=False
        self.records=[]
        self.total=0
        self.page=0
        self._visible_ids=[]
        self._rendered=None
        self._files={}
        self._scan_key=None
        self._scan_generation=0
        self.inspector=FileInspector(self)
        self.inspector.result.connect(self._file_result)
        self.inspector.finished.connect(self._file_finished)
        self.file_timer=QTimer(self);self.file_timer.setSingleShot(True)
        self.file_timer.timeout.connect(self.render)
        root=QVBoxLayout(self)
        root.setContentsMargins(8,12,8,8);root.setSpacing(5)
        title=QLabel('Dây chuyền & lịch sử')
        title.setStyleSheet('font-size:22px;font-weight:700;')
        top=QHBoxLayout();top.addWidget(title,1)
        config=QPushButton('Chọn kênh && chạy…')
        self.config_btn=config
        config.setToolTip('Quét video mới trong thư mục nguồn, chọn các kênh của nhóm rồi chạy Dây chuyền.')
        config.setProperty('primary',True)
        config.clicked.connect(self.configure_pipeline.emit)
        self.inventory_btn=QPushButton('File trong thư mục…')
        self.inventory_btn.clicked.connect(lambda:self.open_folder.emit(self.channels.pid,0,'inventory'))
        top.addWidget(self.inventory_btn);top.addWidget(config);root.addLayout(top)
        note=QLabel('Bảng là hồ sơ video đã nhập, gồm cả lịch sử; không phải danh sách file trong thư mục. '
                    'Video mới trong thư mục: bấm Chọn kênh & chạy để quét và nhận.')
        note.setWordWrap(True);note.setStyleSheet(f'color:{MUTED};')
        root.addWidget(note)
        from app.ui.batch_channels import BatchChannels
        self.channels=BatchChannels()
        self.group=self.channels.group
        self.channels.selected.connect(self._channel_changed)
        self.channels.open_folder.connect(self.open_folder.emit)
        body=QSplitter(Qt.Orientation.Horizontal)
        body.addWidget(self.channels)
        right=QWidget();content=QVBoxLayout(right);content.setContentsMargins(8,0,0,0);content.setSpacing(5)
        body.addWidget(right);body.setChildrenCollapsible(False)
        body.setStretchFactor(0,0);body.setStretchFactor(1,1);body.setSizes([300,850])
        root.addWidget(body,1)
        self.channel_title=QLabel('Chọn nhóm và kênh bên trái')
        self.channel_title.setWordWrap(True);self.channel_title.setTextFormat(Qt.TextFormat.PlainText)
        self.channel_title.setStyleSheet('font-size:16px;font-weight:700;')
        content.addWidget(self.channel_title)
        self.summary=QLabel();self.summary.setWordWrap(True)
        content.addWidget(self.summary)
        views=QHBoxLayout()
        self.scope=QComboBox()
        for label,value in [('Cần xử lý','work'),('Cần kiểm tra file','attention'),('Lịch sử đã xuất','history'),('Tất cả hồ sơ chưa ẩn','all'),('Hồ sơ đã ẩn','hidden')]:
            self.scope.addItem(label,value)
        views.addWidget(self.scope)
        self.order=QComboBox()
        for label,value in [('Ưu tiên xử lý','priority'),('Tên video A → Z','name'),('Mới nhập trước','new'),('Cũ nhập trước','old')]:
            self.order.addItem(label,value)
        views.addWidget(self.order)
        self.file_filter=QComboBox()
        for label,value in [('Mọi tình trạng file',''),('Gốc còn file','present'),('Gốc không tìm thấy','missing'),('Chưa rõ file gốc','unknown')]:
            self.file_filter.addItem(label,value)
        views.addWidget(self.file_filter)
        self.check_btn=QPushButton('Kiểm tra file')
        self.check_btn.clicked.connect(lambda:self.refresh(force_files=True))
        views.addWidget(self.check_btn);views.addStretch(1);content.addLayout(views)
        self.file_status=QLabel('Kiểm tra đường dẫn gốc và Part trong nền; không thay đổi file.')
        self.file_status.setWordWrap(True);self.file_status.setStyleSheet(f'color:{MUTED};')
        content.addWidget(self.file_status)
        row=QHBoxLayout()
        self.search=QLineEdit();self.search.setPlaceholderText('Tìm video trong kênh…')
        self.search.setClearButtonEnabled(True);row.addWidget(self.search,1)
        self.filter=QComboBox()
        for label,value in [('Tất cả trạng thái',''),('Đang chạy','running'),('Đang chờ','pending'),
                            ('Có lỗi','failed'),('Đã hủy','canceled'),('Chưa xuất đủ','ready'),
                            ('Đã xuất đủ','done'),('Chưa có clip','idle')]:
            self.filter.addItem(label,value)
        row.addWidget(self.filter)
        self.refresh_btn=QPushButton('Làm mới')
        self.refresh_btn.setToolTip('Cập nhật tiến trình và kiểm tra lại file gốc/Part trong nền.')
        self.refresh_btn.clicked.connect(lambda:self.refresh(force_files=True));row.addWidget(self.refresh_btn)
        self.clear_btn=QPushButton('Bỏ lọc')
        self.clear_btn.setToolTip('Xem tất cả hồ sơ của kênh, bỏ tìm kiếm và các bộ lọc.')
        self.clear_btn.clicked.connect(self.clear_filters);row.addWidget(self.clear_btn)
        content.addLayout(row)
        self.table=QTableWidget(0,6)
        self.table.setHorizontalHeaderLabels(['STT','Video','Xử lý đã ghi','Part','File gốc hiện tại','Chi tiết'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(54)
        header=self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for col,width in enumerate((42,200,150,105,180,280)):
            self.table.setColumnWidth(col,width)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setMinimumHeight(160)
        self.table.itemDoubleClicked.connect(lambda _item:self.open_selected())
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.folder_menu)
        content.addWidget(self.table,1)
        self.empty=QLabel();self.empty.setWordWrap(True);content.addWidget(self.empty)
        self.feedback=QLabel('Chọn một video để xem, thử lại hoặc hủy đúng video đó.')
        self.feedback.setWordWrap(True);content.addWidget(self.feedback)
        actions=QHBoxLayout()
        self.open_btn=QPushButton('Video && clip');self.open_btn.setProperty('primary',True)
        self.open_btn.clicked.connect(self.open_selected);actions.addWidget(self.open_btn)
        self.folder_btn=QPushButton('Mở Part đã xuất')
        self.folder_btn.setToolTip('Mở nơi đã ghi xuất Part của video này, kể cả khi nơi xuất hiện tại đã đổi.')
        self.folder_btn.clicked.connect(lambda:self.folder_selected('video'));actions.addWidget(self.folder_btn)
        self.detail_btn=QPushButton('Xem chi tiết');self.detail_btn.clicked.connect(self.details)
        actions.addWidget(self.detail_btn)
        self.retry_btn=QPushButton('Thử lại')
        self.retry_btn.setToolTip('Thử lại các việc lỗi/đã hủy của video đang chọn');self.retry_btn.clicked.connect(self.retry_selected)
        actions.addWidget(self.retry_btn)
        self.cancel_btn=QPushButton('Hủy video này');self.cancel_btn.setProperty('danger',True)
        self.cancel_btn.clicked.connect(self.cancel_selected);actions.addWidget(self.cancel_btn)
        self.history_btn=QPushButton('Hồ sơ ▾')
        history_menu=QMenu(self.history_btn)
        self.hide_action=history_menu.addAction('Ẩn hồ sơ đang chọn…',lambda:self.change_visibility(True))
        self.restore_action=history_menu.addAction('Hiện lại hồ sơ đang chọn',lambda:self.change_visibility(False))
        self.history_btn.setMenu(history_menu);actions.addWidget(self.history_btn)
        actions.addStretch(1);content.addLayout(actions)
        pages=QHBoxLayout();self.page_label=QLabel();pages.addWidget(self.page_label,1)
        self.previous=QPushButton('Trước');self.previous.clicked.connect(lambda:self.change_page(-1))
        self.next=QPushButton('Sau');self.next.clicked.connect(lambda:self.change_page(1))
        pages.addWidget(self.previous);pages.addWidget(self.next);content.addLayout(pages)
        self.scope.currentIndexChanged.connect(self._scope_changed)
        self.order.currentIndexChanged.connect(self.apply_filters)
        self.file_filter.currentIndexChanged.connect(self.apply_filters)
        self.search.textChanged.connect(self.apply_filters)
        self.filter.currentIndexChanged.connect(self._status_changed)
        self.timer=QTimer(self);self.timer.setInterval(2500);self.timer.timeout.connect(self.refresh)
        self._selection_changed()

    def showEvent(self,event):
        super().showEvent(event)
        self.refresh(force_files=True);self.timer.start()

    def hideEvent(self,event):
        self.timer.stop();super().hideEvent(event)

    def _channel_changed(self, *_):
        self.page=0
        self.feedback.setText('Chọn một video để xem, thử lại hoặc hủy đúng video đó.')
        self._rendered=None
        self.table.clearSelection();self.table.setCurrentCell(-1,-1)
        self.search.blockSignals(True);self.search.clear();self.search.blockSignals(False)
        for combo in (self.file_filter,self.filter):
            combo.blockSignals(True);combo.setCurrentIndex(0);combo.blockSignals(False)
        if not self._refreshing:self.refresh()

    def refresh(self, force_files=False):
        if self._refreshing:return
        self._refreshing=True
        try:
            self.channels.refresh()
            pid=self.channels.pid
            self.inventory_btn.setEnabled(bool(pid))
            self.records,self.total=snapshot(pid) if pid else ([],0)
            self.check_files(force=force_files)
            p=next((p for p in self.channels.projects if p['id']==pid),None)
            self.channel_title.setText(p['name'] if p else 'Chọn hoặc thêm kênh trong nhóm')
            counts={s:sum(r['state']==s for r in self.records) for s in ('running','pending','failed','ready','done','idle','canceled')}
            self.summary.setText(f"{self.total} hồ sơ đã nhập · {counts['running']} chạy · {counts['pending']} chờ · "
                f"{counts['failed']} lỗi · {counts['ready']} chưa xuất đủ · {counts['done']} lịch sử đã xuất · "
                f"{counts['idle']} chưa có clip · {counts['canceled']} hủy")
            self.render()
        except Exception as error:
            self.records=[];self.total=0;self._rendered=None;self.render()
            self.feedback.setText('Không đọc được tiến trình: '+str(error))
        finally:
            self._refreshing=False

    def check_files(self, force=False):
        key=(self.channels.pid,tuple((r['id'],fingerprint(r)) for r in self.records))
        if not force and key==self._scan_key:return
        self._scan_key=key
        ids={r['id'] for r in self.records}
        self._files={vid:value for vid,value in self._files.items() if vid in ids}
        pending=[r for r in self.records if force or self._files.get(r['id'],{}).get('key')!=fingerprint(r)]
        for record in pending:self._files.pop(record['id'],None)
        self._scan_generation=self.inspector.request(pending)
        self.check_btn.setEnabled(bool(self.records))
        self.file_status.setText(f'Đang kiểm tra {len(pending)} hồ sơ trong nền… Không thay đổi file.' if pending
                                 else 'Kết quả kiểm tra theo đường dẫn đã lưu. Bấm Kiểm tra file sau khi di chuyển/xóa file.')

    def _file_result(self, generation, vid, result):
        if generation!=self._scan_generation:return
        record=next((r for r in self.records if r['id']==vid),None)
        if record is None or result['key']!=fingerprint(record):return
        self._files[vid]=result
        if not self.file_timer.isActive():self.file_timer.start(120)

    def _file_finished(self,generation):
        if generation!=self._scan_generation:return
        values=[self._files[r['id']] for r in self.records if r['id'] in self._files]
        present=sum(v['source']=='present' for v in values)
        missing=sum(v['source']=='missing' for v in values)
        other=len(values)-present-missing
        self.file_status.setText(f'Đã kiểm tra: {present} gốc còn file · {missing} không thấy tại đường dẫn cũ · {other} cần kiểm tra. '
                                 'Bấm Làm mới để kiểm tra lại.')
        latest=max((value['checked_at'] for value in values),default='—')
        self.file_status.setText(f'Kiểm tra lúc {latest} · '+self.file_status.text())
        self.render()

    def _matches_file(self,record,status):
        if not status:return True
        value=self._files.get(record['id'])
        known=value is not None and value['key']==fingerprint(record)
        if status=='unknown':return not known or value['source'] not in ('present','missing')
        return known and value['source']==status

    def apply_filters(self,*_):
        self.page=0;self.render()

    def clear_filters(self):
        self.search.blockSignals(True);self.search.clear();self.search.blockSignals(False)
        for combo in (self.filter,self.file_filter):
            combo.blockSignals(True);combo.setCurrentIndex(0);combo.blockSignals(False)
        self.scope.blockSignals(True);self.scope.setCurrentIndex(self.scope.findData('all'));self.scope.blockSignals(False)
        self.apply_filters()

    def _scope_changed(self,*_):
        self.filter.blockSignals(True);self.filter.setCurrentIndex(0);self.filter.blockSignals(False)
        self.apply_filters()

    def _status_changed(self,*_):
        status=self.filter.currentData()
        scope=self.scope.currentData()
        if status and scope in ('work','history'):
            self.scope.blockSignals(True)
            self.scope.setCurrentIndex(self.scope.findData('history' if status=='done' else 'work'))
            self.scope.blockSignals(False)
        self.apply_filters()

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
        status=self.filter.currentData()
        scope=self.scope.currentData()
        file_status=self.file_filter.currentData()
        warnings={r['id']:file_warning(r,self._files.get(r['id'])) for r in self.records}
        attention=sum(bool(value) for value in warnings.values())
        self.scope.setItemText(self.scope.findData('attention'),f'Cần kiểm tra file ({attention})')
        hidden_ids={r['id'] for r in self.records if hidden(r)}
        filtered=[r for r in self.records if ((r['id'] in hidden_ids) if scope=='hidden' else (r['id'] not in hidden_ids))
                  and (not status or r['state']==status)
                  and (not query or query in folded(r['channel']+' '+r['video']))
                  and (scope in ('all','hidden') or (scope=='history' and r['state']=='done')
                       or (scope=='attention' and bool(warnings[r['id']]))
                       or (scope=='work' and (r['state']!='done' or bool(warnings[r['id']]))))
                  and self._matches_file(r,file_status)]
        order=self.order.currentData()
        if order=='name':filtered.sort(key=lambda r:(natural(folded(r['video'])),r['id']))
        elif order in ('new','old'):filtered.sort(key=lambda r:(r['imported_at'],r['id']),reverse=order=='new')
        else:
            rank={'running':0,'pending':1,'failed':2,'ready':3,'idle':4,'canceled':5,'done':6}
            filtered.sort(key=lambda r:(rank.get(r['state'],9),-r['last_job'],-r['id']))
        self.page=min(self.page,max(0,(len(filtered)-1)//self.PAGE_SIZE))
        start=self.page*self.PAGE_SIZE;rows=filtered[start:start+self.PAGE_SIZE]
        signature=(start,[(r['id'],r['stage'],r['parts'],r['source'],r['detail'],r['video'],r['path'],self._files.get(r['id'])) for r in rows])
        if signature!=self._rendered:
            self.table.blockSignals(True)
            self.table.setUpdatesEnabled(False)
            self.table.setRowCount(len(rows))
            self._visible_ids=[r['id'] for r in rows]
            for row,r in enumerate(rows):
                source,parts,check_note=file_labels(r,self._files.get(r['id']))
                stage='Đã ghi xuất đủ' if r['state']=='done' else r['stage']
                warning=warnings[r['id']]
                if warning and r['state']=='done':stage='Đã xuất · cần kiểm tra'
                detail=warning or r['detail']+(' · Lịch sử; file có thể đã di chuyển.' if r['state']=='done' else '')
                values=(str(start+row+1),r['video'],stage,parts,source,detail)
                for col,value in enumerate(values):
                    item=self.table.item(row,col)
                    if item is None:item=QTableWidgetItem();self.table.setItem(row,col,item)
                    if item.text()!=value:item.setText(value)
                    item.setToolTip((check_note+'\n'+r['path']+'\nDọn gốc đã ghi: '+r['source']) if col in (3,4) else (value if col!=1 else r['path']+'\nNhập: '+r['imported_at']))
                    if col==2:item.setForeground(QColor(WARN if warning and r['state']=='done' else {'running':ACCENT,'failed':DANGER,'done':SUCCESS,'pending':WARN}.get(r['state'],MUTED)))
                    elif col in (3,4,5):item.setForeground(QColor(WARN if warning else MUTED))
            if selected_id in self._visible_ids:self.table.selectRow(self._visible_ids.index(selected_id))
            else:self.table.clearSelection();self.table.setCurrentCell(-1,-1)
            self.table.setUpdatesEnabled(True);self.table.blockSignals(False)
            self._rendered=signature
        bound=f" · Đang lấy {len(self.records)}/{self.total} video gần nhất/đang chạy" if self.total>len(self.records) else ''
        self.page_label.setText(f"{len(filtered)}/{self.total} hồ sơ · Hiện {start+1 if rows else 0}–{start+len(rows)}"+bound)
        self.empty.setVisible(not rows)
        filters=[self.scope.currentText()]
        if status:filters.append(self.filter.currentText())
        if file_status:filters.append(self.file_filter.currentText())
        if query:filters.append('Tìm: '+self.search.text().strip())
        self.empty.setText('Không có hồ sơ khớp: '+' · '.join(filters)+'. Bấm Bỏ lọc để xem tất cả. '
                           'Nhận video mới trong thư mục: Chọn kênh & chạy.')
        self.clear_btn.setEnabled(bool(query or status or file_status or scope!='all'))
        self.previous.setEnabled(self.page>0);self.next.setEnabled(start+len(rows)<len(filtered))
        self._selection_changed()

    def _selection_changed(self):
        r=self.selected()
        self.open_btn.setEnabled(bool(r));self.detail_btn.setEnabled(bool(r))
        self.folder_btn.setEnabled(bool(r and r.get('export_paths')))
        self.folder_btn.setToolTip('Mở nơi đã ghi xuất Part của video này.' if r and r.get('export_paths')
                                   else 'Video này chưa có đường dẫn Part đã xuất. Nơi xuất hiện tại nằm bên trái.')
        self.hide_action.setEnabled(bool(r and not r['job_ids'] and not hidden(r)))
        self.restore_action.setEnabled(bool(r and hidden(r)))
        self.cancel_btn.setEnabled(bool(r and r['job_ids']))
        self.retry_btn.setEnabled(bool(r and r['retry_ids']))

    def change_visibility(self,value):
        r=self.selected()
        if not r:return
        vid=r['id']
        if value and QMessageBox.question(self,'Ẩn hồ sơ cũ',
                'Ẩn hồ sơ “'+r['video']+'” khỏi danh sách thường dùng?\n'
                'Không xóa video, Part hoặc lịch sử chống trùng. Xem lại ở Hồ sơ đã ẩn.',
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        self.refresh()
        r=next((row for row in self.records if row['id']==vid),None)
        if not r:return
        try:
            set_hidden(r,value);self.render()
            self.feedback.setText('Đã ẩn hồ sơ. Chọn Hồ sơ đã ẩn để hiện lại.' if value else 'Đã hiện lại hồ sơ; chọn Tất cả hồ sơ chưa ẩn để xem.')
        except ValueError as error:self.feedback.setText(str(error))

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
        source,parts,check_note=file_labels(r,self._files.get(r['id']))
        lines=[r['channel'],'Nhập vào ứng dụng: '+r['imported_at'],r['path'],
               f"Lịch sử xử lý: {r['stage']} · Part {r['parts']}",
               'Dọn gốc đã ghi: '+r['source'],r['note'],'File hiện tại: '+source,check_note,
               'Các Part đã ghi đường dẫn:']
        result=self._files.get(r['id'])
        if result and result['key']==fingerprint(r):
            labels={'present':'Còn file','missing':'Không tìm thấy','unknown':'Không kiểm tra được',
                    'empty':'0 byte','invalid':'Không phải file','unset':'Chưa có đường dẫn'}
            lines.extend(labels.get(status,status)+' — '+path for path,status in result['parts'])
        else:lines.extend(r['export_paths'])
        lines.append('')
        for j in r['jobs'][:100]:
            lines.append(f"#{j['id']} · {j['type']} · {j['status']}\n{j['message'] or ''}\n{j['error'] or ''}\n")
        text.setPlainText('\n'.join(lines));lay.addWidget(text,1)
        close=QPushButton('Đóng');close.clicked.connect(dlg.accept);lay.addWidget(close)
        dlg.exec()
