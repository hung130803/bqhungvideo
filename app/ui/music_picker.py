"""Browse and preview bundled music without network or changes to saved jobs."""
from PyQt6.QtCore import QUrl,Qt
from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QLineEdit,QListWidget,QListWidgetItem,QPushButton,QMessageBox
from app.core import music_library as lib
from app.ui.layout_tools import fit_dialog

class MusicPicker(QDialog):
    def __init__(self,parent=None,current='',allow_auto=True):
        super().__init__(parent);self.setWindowTitle('Kho nhạc nền · chọn và nghe thử')
        self.selection=current;self._allow_auto=allow_auto
        from PyQt6.QtMultimedia import QMediaPlayer,QAudioOutput
        self.player=QMediaPlayer(self);self.audio=QAudioOutput(self);self.audio.setVolume(.4);self.player.setAudioOutput(self.audio)
        layout=QVBoxLayout(self)
        intro=QLabel('Chọn theo cảm xúc, nghe thử rồi áp dụng. Tự chọn theo phong cách dùng nhóm đã gán sẵn; không tự suy đoán cảm xúc người trong video.');intro.setWordWrap(True);layout.addWidget(intro)
        self.mode=QComboBox();self.mode.addItem('Chọn bài cụ thể','fixed');self.mode.addItem('Theo nhạc của mẫu xuất','');self.mode.addItem('Tắt nhạc nền',lib.PREFIX+'off')
        if allow_auto:
            self.mode.addItem('AI chọn theo nội dung từng Part · nghe duyệt trước khi xuất',lib.PREFIX+'auto:story')
            self.mode.addItem('Tự chọn theo phong cách dựng · đổi bài giữa các Part',lib.PREFIX+'auto:style')
            for key,label in lib.MOODS.items():self.mode.addItem('Tự chọn · '+label,lib.PREFIX+'auto:'+key)
        self.mode.setCurrentIndex(max(0,self.mode.findData(current if current=='' or current==lib.PREFIX+'off' or current.startswith(lib.PREFIX+'auto:') else 'fixed')))
        layout.addWidget(self.mode)
        bar=QHBoxLayout();layout.addLayout(bar);self.mood=QComboBox();self.mood.addItem('Tất cả cảm xúc','')
        for key,label in lib.MOODS.items():self.mood.addItem(label,key)
        bar.addWidget(self.mood);self.search=QLineEdit();self.search.setPlaceholderText('Tìm bài / tác giả…');bar.addWidget(self.search,1)
        self.items=QListWidget();layout.addWidget(self.items,1)
        self.info=QLabel('');self.info.setWordWrap(True);layout.addWidget(self.info)
        self.mood.currentIndexChanged.connect(self.fill);self.search.textChanged.connect(self.fill)
        self.items.currentItemChanged.connect(self.selected)
        self.player.errorOccurred.connect(lambda _code,message:self.info.setText('Không nghe thử được: '+message))
        row=QHBoxLayout();layout.addLayout(row)
        for label,fn in [('Nghe thử',self.preview),('Dừng',self.player.stop),('Dùng lựa chọn',self.apply),('Hủy',self.reject)]:
            b=QPushButton(label);b.clicked.connect(fn);row.addWidget(b)
        self.finished.connect(lambda _:self.player.stop());self.fill();fit_dialog(self,720,560)

    def fill(self,*_):
        selected=self.items.currentItem();want=selected.data(Qt.ItemDataRole.UserRole) if selected else self.selection
        self.items.clear();mood=self.mood.currentData();query=self.search.text().strip().casefold()
        for t in lib.catalog():
            if mood and t['mood']!=mood:continue
            if query and query not in (t['title']+' '+t['author']+' '+lib.MOODS[t['mood']]).casefold():continue
            item=QListWidgetItem(f"{t['title']} · {lib.MOODS[t['mood']]} · {t['duration']:.0f}s")
            item.setData(Qt.ItemDataRole.UserRole,lib.PREFIX+t['id']);self.items.addItem(item)
        for i in range(self.items.count()):
            if self.items.item(i).data(Qt.ItemDataRole.UserRole)==want:self.items.setCurrentRow(i);break

    def selected(self,item,*_):
        if not item:return
        self.mode.setCurrentIndex(0)
        ref=item.data(Qt.ItemDataRole.UserRole);self.info.setText(lib.describe(ref))
        if ref.startswith(lib.PREFIX) and ref not in (lib.PREFIX+'off',) and not ref.startswith(lib.PREFIX+'auto:'):
            t=lib.track(ref[len(lib.PREFIX):]);self.info.setText(lib.describe(ref)+'\nNguồn: '+t['source'])

    def preview(self):
        item=self.items.currentItem()
        if not item:return
        ref=item.data(Qt.ItemDataRole.UserRole)
        if not ref or ref==lib.PREFIX+'off' or ref.startswith(lib.PREFIX+'auto:'):
            self.info.setText('Chọn một bài cụ thể trong danh sách để nghe thử.');return
        try:path=lib.resolve(ref)
        except (ValueError,OSError) as exc:self.info.setText(str(exc));return
        self.player.setSource(QUrl.fromLocalFile(path));self.player.play()

    def apply(self):
        item=self.items.currentItem()
        if self.mode.currentData()=='fixed':
            if not item:return
            ref=item.data(Qt.ItemDataRole.UserRole)
        else:ref=self.mode.currentData()
        try:
            if ref.startswith(lib.PREFIX) and not ref.startswith(lib.PREFIX+'auto:'):lib.resolve(ref)
        except (ValueError,OSError) as exc:QMessageBox.warning(self,'Chưa chọn được nhạc',str(exc));return
        self.selection=ref;self.accept()
