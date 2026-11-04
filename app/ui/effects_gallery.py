"""Editable effect pool for a saved template. Opens without network or GPU probing."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QLineEdit,QListWidget,QListWidgetItem,QPushButton
from app.core.hieu_ung import KHO,MUC_NHAN
from app.core.effects_config import parse,encode,PACKS,NEW_KEYS,category
from app.ui.theme import SP_2,SP_4,pad,set_role,set_variant

class EffectsGallery(QDialog):
    def __init__(self,parent=None,value='nhe'):
        super().__init__(parent);self.setWindowTitle('Kho hiệu ứng — chọn bộ cho mẫu');self.resize(780,700)
        self.value=value;level,keys=parse(value)
        outer=QVBoxLayout(self);pad(outer,SP_4,spacing=SP_2)
        intro=QLabel('Chọn những kiểu được phép dùng. App chọn điểm theo nhịp tiếng, chuyển động và chỗ ghép; mỗi clip tối đa 3 điểm, tổng thời gian hiệu ứng ≤ 10%. Không gọi thêm AI.')
        intro.setWordWrap(True);set_role(intro,'muted');outer.addWidget(intro)
        row=QHBoxLayout();row.addWidget(QLabel('Cường độ'))
        self.level=QComboBox()
        for key,label in MUC_NHAN.items():self.level.addItem(label,key)
        self.level.setCurrentIndex(max(0,self.level.findData(level)));row.addWidget(self.level,1);outer.addLayout(row)
        self.pack=QComboBox();self.pack.addItem('Chọn bộ phối sẵn…');self.pack.addItems(PACKS);self.pack.currentTextChanged.connect(self._pack);outer.addWidget(self.pack)
        row=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('Tìm: nháy, zoom, màu, mưa, glitch…');row.addWidget(self.search,1)
        self.group=QComboBox();self.group.addItem('Tất cả nhóm');self.group.addItems(sorted({category(k,h) for k,h in KHO.items()}));row.addWidget(self.group);outer.addLayout(row)
        self.items=QListWidget();self.items.setSpacing(2)
        selected=set(keys) if keys is not None else set(KHO)-NEW_KEYS
        for key,h in KHO.items():
            suffix=' · cần GPU Vulkan' if h.shader else (' · cần plugin' if h.module else '')
            item=QListWidgetItem(h.ten+suffix);item.setData(Qt.ItemDataRole.UserRole,key)
            item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if key in selected else Qt.CheckState.Unchecked)
            item.setToolTip(category(key,h)+' · '+(h.ghi_chu or 'Chỉ chọn ở điểm nhấn phù hợp; không lặp cùng kiểu trong clip.'))
            self.items.addItem(item)
        outer.addWidget(self.items,1)
        row=QHBoxLayout()
        for label,callback in [('Chọn nhóm đang hiện',lambda:self._mark(True)),('Bỏ nhóm đang hiện',lambda:self._mark(False))]:
            btn=QPushButton(label);btn.clicked.connect(callback);row.addWidget(btn)
        outer.addLayout(row)
        self.count=QLabel();set_role(self.count,'muted');outer.addWidget(self.count)
        note=QLabel('Tông màu chỉ bật khi bạn chọn. Lớp phủ mưa/tuyết/tim… cần ngữ cảnh phù hợp. Máy thiếu plugin/GPU sẽ bỏ kiểu đó. Chọn nhiều kiểu mở rộng lựa chọn, không tăng mật độ chèn.')
        note.setWordWrap(True);set_role(note,'hint');outer.addWidget(note)
        row=QHBoxLayout();row.addStretch();cancel=QPushButton('Hủy');set_variant(cancel,'ghost');cancel.clicked.connect(self.reject);row.addWidget(cancel)
        use=QPushButton('Dùng cho mẫu');use.setProperty('primary',True);use.clicked.connect(self._use);row.addWidget(use);outer.addLayout(row)
        self.items.itemChanged.connect(self._count);self.search.textChanged.connect(self._filter);self.group.currentTextChanged.connect(self._filter);self._count()
    def selected(self):
        return [self.items.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.items.count()) if self.items.item(i).checkState()==Qt.CheckState.Checked]
    def _count(self,*_):self.count.setText(f'Đã chọn {len(self.selected())}/{self.items.count()} kiểu. Chỉ được lưu vào mẫu khi bấm Lưu trong Chỉnh mẫu.')
    def _filter(self,*_):
        query=self.search.text().casefold().strip();group=self.group.currentText()
        for i in range(self.items.count()):
            item=self.items.item(i);key=item.data(Qt.ItemDataRole.UserRole)
            item.setHidden((query not in item.text().casefold() and query not in key) or (group!='Tất cả nhóm' and group!=category(key,KHO[key])))
    def _pack(self,name):
        if name not in PACKS or not hasattr(self,'items'):return
        for i in range(self.items.count()):
            item=self.items.item(i);item.setCheckState(Qt.CheckState.Checked if item.data(Qt.ItemDataRole.UserRole) in PACKS[name] else Qt.CheckState.Unchecked)
    def _mark(self,on):
        for i in range(self.items.count()):
            item=self.items.item(i)
            if not item.isHidden():item.setCheckState(Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)
    def _use(self):
        self.value=encode(self.level.currentData(),self.selected());self.accept()
