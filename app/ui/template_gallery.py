"""Visual picker for locally prepared, editable channel templates."""
from PyQt6.QtCore import Qt, QSize, QRectF
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QIcon, QPainterPath
from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QListWidget,QListWidgetItem,QPushButton,QComboBox
from app import services
from app.ui.theme import ACCENT,SP_2,SP_4,pad,rgba,set_role,set_variant
from app.core.template_library import catalog,ensure_templates
from app.core.template_backgrounds import decode,image,fit_rect

def preview(layout,width=270,height=480):
    from tempfile import TemporaryDirectory
    from pathlib import Path
    from app.ui.editor import render_overlay_png
    theme,_=decode(layout.get('bg'))
    pm=QPixmap.fromImage(image(theme or 'paper',width,height))
    p=QPainter(pm);p.setRenderHint(QPainter.RenderHint.Antialiasing)
    cx,cy,sw=fit_rect(layout.get('video_rect',[.5,.49,.98]),16,9,width,height)
    w=sw*width;h=w*9/16;vx=cx*width-w/2;vy=cy*height-h/2
    frame=QPixmap(max(2,int(w)),max(2,int(h)));frame.fill(QColor('#94b6c2'))
    p.end();p=QPainter(frame);p.translate(-vx,-vy)
    hills=QPainterPath();hills.moveTo(vx,vy+h)
    hills.lineTo(vx,vy+h*.65);hills.lineTo(vx+w*.28,vy+h*.25)
    hills.lineTo(vx+w*.6,vy+h*.67);hills.lineTo(vx+w*.81,vy+h*.37)
    hills.lineTo(vx+w,vy+h*.59);hills.lineTo(vx+w,vy+h);hills.closeSubpath()
    p.fillPath(hills,QColor('#376b67'))
    p.setPen(QColor('white'));f=QFont('Segoe UI');f.setPixelSize(max(9,int(width*.041)));p.setFont(f)
    p.drawText(QRectF(vx,vy+h*.43,w,h*.3),Qt.AlignmentFlag.AlignCenter,'KHUNG VIDEO CỦA BẠN')
    p.end();p=QPainter(pm)
    from app.core.template_backgrounds import draw_foreground
    draw_foreground(p,QRectF(vx,vy,w,h),frame,layout.get('bg'))
    p.setFont(f)
    cap_y=float(layout.get('cap_ny',.66))*height
    rect=QRectF(width*.3,cap_y-height*.021,width*.4,height*.044)
    p.fillRect(rect,QColor('#edc83a'));p.setPen(QColor('#1d2430'))
    p.drawText(rect,Qt.AlignmentFlag.AlignCenter,'phụ đề tự động');p.end()
    with TemporaryDirectory(prefix='bq_gallery_') as folder:
        path=Path(folder)/'overlay.png'
        if render_overlay_png(layout.get('layers',[]),1,width,height,path,'Một phát hiện thú vị',video_px=(vx,vy,w,h)):
            p=QPainter(pm);p.drawPixmap(0,0,QPixmap(str(path)));p.end()
    return pm

class TemplateGallery(QDialog):
    def __init__(self,parent=None,current_name='',button_text='Dùng làm mẫu mặc định'):
        super().__init__(parent);self.selected_name='';self.setWindowTitle('Kho mẫu sẵn • chọn rồi dùng ngay')
        self.resize(940,740);self.setMinimumSize(660,520)
        if self.screen():
            size=self.screen().availableGeometry().size();self.resize(min(940,size.width()-50),min(740,size.height()-70))
        ensure_templates();self.entries=catalog()
        outer=QVBoxLayout(self);pad(outer,SP_4,spacing=SP_2)
        intro=QLabel('Mẫu đã phối nền, khung, chữ và phụ đề. Tạo tiêu đề/Part theo từng clip; không gọi thêm AI khi chọn mẫu.')
        intro.setWordWrap(True);set_role(intro,'muted');outer.addWidget(intro)
        self.category=QComboBox();self.category.addItem('Tất cả phong cách')
        self.category.addItems(sorted({e['category'] for e in self.entries}));outer.addWidget(self.category)
        self.grid=QListWidget();self.grid.setViewMode(QListWidget.ViewMode.IconMode)
        self.grid.setResizeMode(QListWidget.ResizeMode.Adjust);self.grid.setMovement(QListWidget.Movement.Static)
        self.grid.setIconSize(QSize(135,240));self.grid.setGridSize(QSize(204,294));self.grid.setWordWrap(True)
        self.grid.setSpacing(7);self.grid.setStyleSheet('QListWidget::item{padding:5px;margin:2px;border-radius:8px;} QListWidget::item:selected{background:'+rgba(ACCENT,.28)+';}')
        for entry in self.entries:
            layout=services.get_template(entry['name']) or entry['layout']
            item=QListWidgetItem(QIcon(preview(layout)),entry['name'])
            item.setData(Qt.ItemDataRole.UserRole,entry);item.setSizeHint(QSize(198,288))
            self.grid.addItem(item)
            if entry['name']==current_name:self.grid.setCurrentItem(item)
        outer.addWidget(self.grid,1)
        self.detail=QLabel();self.detail.setWordWrap(True);self.detail.setMinimumHeight(42);outer.addWidget(self.detail)
        note=QLabel('Kênh đã gán mẫu riêng vẫn dùng mẫu đó. Trong Dây chuyền, chọn cột Mẫu để gán từng kênh; bấm tiêu đề cột Mẫu để gán cả nhóm đang hiện. Chỉnh mẫu → Lưu mới để tạo bản riêng.')
        note.setWordWrap(True);set_role(note,'hint');outer.addWidget(note)
        row=QHBoxLayout();row.addStretch();cancel=QPushButton('Hủy');set_variant(cancel,'ghost');cancel.clicked.connect(self.reject);row.addWidget(cancel)
        self.use=QPushButton(button_text);self.use.setProperty('primary',True);self.use.clicked.connect(self._choose);row.addWidget(self.use);outer.addLayout(row)
        self.grid.currentItemChanged.connect(self._describe);self.grid.itemDoubleClicked.connect(lambda _:self._choose())
        self.category.currentTextChanged.connect(self._filter)
        if self.grid.currentRow()<0:self.grid.setCurrentRow(0)
        self._describe()

    def _describe(self,*_):
        item=self.grid.currentItem();self.use.setEnabled(item is not None and not item.isHidden())
        if item:
            entry=item.data(Qt.ItemDataRole.UserRole);layout=services.get_template(entry['name']) or entry['layout']
            self.detail.setText(entry['description']+' Nền: '+('chuyển động nhẹ.' if decode(layout.get('bg'))[1] else 'tĩnh.'))

    def _filter(self,text):
        first=None
        for i in range(self.grid.count()):
            item=self.grid.item(i);show=text=='Tất cả phong cách' or item.data(Qt.ItemDataRole.UserRole)['category']==text
            item.setHidden(not show)
            if show and first is None:first=item
        self.grid.setCurrentItem(first);self._describe()

    def _choose(self):
        item=self.grid.currentItem()
        if item is not None and not item.isHidden():
            self.selected_name=item.data(Qt.ItemDataRole.UserRole)['name'];self.accept()
