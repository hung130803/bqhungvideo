"""Read-only on-disk inventory and recorded Part inspection, with background stat."""
import os
from pathlib import Path
import threading

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import (QAbstractItemView,QComboBox,QDialog,QHBoxLayout,QHeaderView,
    QLabel,QLineEdit,QPushButton,QTableWidget,QTableWidgetItem,QVBoxLayout)

from app.ui.batch_files import presence
from app.ui.layout_tools import fit_dialog


def path_key(path):
    return os.path.normcase(os.path.abspath(path))


def scan_inventory(folder, sources, exports):
    """List direct children only. Never import, delete, or enqueue media."""
    from app.core.pipeline import VIDEO_EXTS, is_tmp_file, _PART_RE
    rows=[]
    if not folder or not Path(folder).is_absolute():
        return [], 'Chưa có đường dẫn thư mục đầy đủ.'
    try:
        with os.scandir(folder) as entries:
            for entry in entries:
                if not entry.is_file(follow_symlinks=False):continue
                p=Path(entry.path)
                if p.suffix.lower() not in VIDEO_EXTS and not is_tmp_file(p.name):continue
                key=path_key(p)
                kind=('File tải dở' if is_tmp_file(p.name) else 'Part đã ghi trong ứng dụng' if key in exports
                      else 'Tên dạng Part — Dây chuyền bỏ qua' if _PART_RE.match(p.name)
                      else 'Video nguồn đã có hồ sơ' if key in sources else 'Video chưa có hồ sơ tại đường dẫn này')
                rows.append((str(p),kind,presence(str(p))))
        return sorted(rows,key=lambda r:Path(r[0]).name.casefold()), ''
    except OSError as error:
        return [], 'Không đọc được thư mục; kiểm tra đường dẫn, quyền và kết nối ổ đĩa: '+str(error)


class InventoryWorker(QObject):
    ready=pyqtSignal(int,object,str)

    def __init__(self,parent):
        super().__init__(parent)
        self.generation=0

    def start(self,folder,sources,exports,recorded=None):
        self.generation+=1;generation=self.generation
        def run():
            try:
                if recorded is None:rows,error=scan_inventory(folder,sources,exports)
                else:rows,error=[(p,'Part đã ghi xuất',presence(p)) for p in recorded],''
                self.ready.emit(generation,rows,error)
            except RuntimeError:pass  # Dialog already destroyed.
        threading.Thread(target=run,daemon=True).start()


class FileInventoryDialog(QDialog):
    def __init__(self,parent,data,sources=(),exports=(),recorded=None):
        super().__init__(parent)
        self.data=data;self.recorded=recorded
        self.sources={path_key(p) for p in sources if p};self.exports={path_key(p) for p in exports if p}
        self.rows=[]
        self.setWindowTitle(('Part của video — ' if recorded is not None else 'File trong thư mục — ')+data['channel_name'])
        layout=QVBoxLayout(self)
        note=QLabel('Đối chiếu từng đường dẫn Part đã ghi; file thiếu vẫn hiện để bạn kiểm tra.' if recorded is not None else
                    'Quét file trực tiếp trong thư mục đang chọn, không quét thư mục con. File mới chưa tự nhập hoặc chạy; dùng Chọn kênh & chạy để xử lý.')
        note.setWordWrap(True);layout.addWidget(note)
        line=QHBoxLayout();self.folders=QComboBox()
        seen=set()
        for label,path in [('Nguồn',data['pipeline']),('Nơi xuất hiện tại',data['channel'])]+[('Nơi xuất cũ',p) for p in data['recorded']]:
            if path and path_key(path) not in seen:
                seen.add(path_key(path));self.folders.addItem(label+' — '+str(path),str(path))
        self.folders.setMinimumContentsLength(20)
        self.folders.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.folders.setVisible(recorded is None);line.addWidget(self.folders,1)
        self.refresh_btn=QPushButton('Làm mới file');line.addWidget(self.refresh_btn);layout.addLayout(line)
        self.status=QLabel();self.status.setWordWrap(True);self.status.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(self.status)
        self.table=QTableWidget(0,3);self.table.setHorizontalHeaderLabels(['Tên file','Nhận diện','Hiện tại'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(1,255);self.table.setColumnWidth(2,160);layout.addWidget(self.table,1)
        self.path_field=QLineEdit();self.path_field.setReadOnly(True)
        self.path_field.setPlaceholderText('Chọn file để xem đường dẫn đầy đủ');layout.addWidget(self.path_field)
        actions=QHBoxLayout()
        self.open_btn=QPushButton('Mở thư mục chứa file');self.copy_btn=QPushButton('Chép đường dẫn file')
        self.open_btn.clicked.connect(self.open_selected);self.copy_btn.clicked.connect(self.copy_selected)
        actions.addWidget(self.open_btn);actions.addWidget(self.copy_btn);actions.addStretch(1)
        close=QPushButton('Đóng');close.clicked.connect(self.accept);actions.addWidget(close);layout.addLayout(actions)
        self.worker=InventoryWorker(self);self.worker.ready.connect(self.finished_scan)
        self.folders.currentIndexChanged.connect(self.refresh);self.refresh_btn.clicked.connect(self.refresh)
        self.table.itemSelectionChanged.connect(self.selection_changed)
        fit_dialog(self,1050,600);self.refresh()

    def refresh(self,*_):
        if not self.refresh_btn.isEnabled():return
        self.refresh_btn.setEnabled(False);self.folders.setEnabled(False)
        self.status.setText('Đang kiểm tra file trong nền…');self.rows=[];self.table.setRowCount(0)
        self.selection_changed()
        self.worker.start(self.folders.currentData(),self.sources,self.exports,self.recorded)

    def finished_scan(self,generation,rows,error):
        if generation!=self.worker.generation:return
        self.refresh_btn.setEnabled(True);self.folders.setEnabled(True)
        self.rows=rows;self.table.setRowCount(len(rows))
        labels={'present':'Còn file','missing':'Không tìm thấy','empty':'File 0 byte','invalid':'Không phải file','unknown':'Không kiểm tra được','unset':'Chưa có đường dẫn'}
        for i,(path,kind,status) in enumerate(rows):
            for j,value in enumerate((Path(path).name,kind,labels[status])):
                cell=QTableWidgetItem(value);cell.setToolTip(path if j==0 else value);self.table.setItem(i,j,cell)
        self.table.resizeRowsToContents()
        found=sum(r[2]=='present' for r in rows)
        self.status.setText(error or f'{len(rows)} file được liệt kê · {found} file còn và khác 0 byte · {len(rows)-found} cần kiểm tra. Chỉ đọc, không đổi dữ liệu.')
        self.selection_changed()

    def selected(self):
        row=self.table.currentRow()
        return self.rows[row] if 0<=row<len(self.rows) else None

    def selection_changed(self):
        row=self.selected();self.copy_btn.setEnabled(bool(row));self.open_btn.setEnabled(bool(row and row[2] in ('present','empty')))
        self.path_field.setText(row[0] if row else '');self.path_field.setCursorPosition(0)
        self.path_field.setToolTip(self.path_field.text())

    def open_selected(self):
        row=self.selected()
        if not row:return
        # Recheck after selection: do not open an empty folder for a vanished file.
        if presence(row[0]) not in ('present','empty'):
            self.status.setText('File không còn tại đường dẫn này. Bấm Làm mới file.');return
        from app.ui.folder_access import open_directory
        try:self.status.setText(open_directory(Path(row[0]).parent)+' · File: '+Path(row[0]).name)
        except Exception as error:self.status.setText(str(error))

    def copy_selected(self):
        from app.ui.folder_access import copy_path
        row=self.selected()
        if row:self.status.setText(copy_path(row[0]))
