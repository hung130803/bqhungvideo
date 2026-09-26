"""Edit and preview reviewed accents without re-running AI."""
from copy import deepcopy
from pathlib import Path
import tempfile
import uuid
from PyQt6.QtCore import Qt,QThread,pyqtSignal,QUrl
from PyQt6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QComboBox,
    QDoubleSpinBox,QPushButton,QLineEdit,QCheckBox,QListWidget,QMessageBox,QScrollArea,QWidget)
from app.core.editorial import STYLES,KINDS,SOUNDS,validate,propose
from app.ui.layout_tools import fit_dialog


class Preview(QThread):
    result=pyqtSignal(str,str)
    def __init__(self,source,parts,plan,event,folder,parent):
        super().__init__(parent);self.args=(source,deepcopy(parts),deepcopy(plan),event,folder)
    def run(self):
        try:
            from app.core.ffmpeg_utils import export_canvas_clip,probe
            source,parts,plan,index,folder=self.args
            if index is None:
                part=parts[0];a=part['start'];b=min(part['end'],a+6.)
                subset=dict(plan,events=[])
            else:
                event=deepcopy(plan['events'][index]);part=parts[event['part']]
                lead=max(1.,event['duration'] if event['kind']=='replay' else 1.)
                a=max(part['start'],part['start']+event['offset']-lead)
                b=min(part['end'],part['start']+event['offset']+event['duration']+1.)
                event['offset']=part['start']+event['offset']-a;event['part']=0
                subset=dict(plan,events=[event])
            clip_parts=[dict(part,start=a,end=b)]
            path=Path(folder)/('preview_'+uuid.uuid4().hex+'.mp4');logs=[]
            export_canvas_clip(source,path,[(a,b)],(.5,.5,.94),bg='black',out_w=360,out_h=640,
                encoder='libx264',fx_fade=False,fx_whoosh=True,hieu_ung='tat',fit_src=True,
                edit_plan=subset,edit_parts=clip_parts,edit_log=logs)
            note=' · '.join(e.get('tracking_note','') for e in logs if e.get('tracking_note'))
            self.result.emit(str(path),note or f'Xem thử {probe(path).duration:.1f}s · tiếng gốc, khung thử; chưa có giọng AI/nhạc/phụ đề của mẫu.')
        except Exception as exc:self.result.emit('',str(exc))


class SourceFrame(QThread):
    result=pyqtSignal(str,str)
    def __init__(self,source,at,folder,parent):
        super().__init__(parent);self.source=source;self.at=at;self.folder=folder
    def run(self):
        try:
            from app.core.ffmpeg_utils import extract_frame
            path=Path(self.folder)/('source_'+uuid.uuid4().hex+'.jpg')
            if not extract_frame(self.source,self.at,path):raise RuntimeError('Không lấy được hình nguồn tại mốc này.')
            self.result.emit(str(path),'')
        except Exception as exc:self.result.emit('',str(exc))


class TargetImage(QLabel):
    def __init__(self,pixmap,parent=None):
        super().__init__(parent);self.picture=pixmap;self.point=(.5,.5);self.setMinimumSize(320,240)
    def image_rect(self):
        from PyQt6.QtCore import QRectF
        size=self.picture.size();size.scale(self.size(),Qt.AspectRatioMode.KeepAspectRatio)
        return QRectF((self.width()-size.width())/2,(self.height()-size.height())/2,size.width(),size.height())
    def paintEvent(self,event):
        from PyQt6.QtGui import QPainter,QPen,QColor
        from PyQt6.QtCore import QPointF
        painter=QPainter(self);rect=self.image_rect();painter.drawPixmap(rect.toRect(),self.picture)
        x=rect.left()+self.point[0]*rect.width();y=rect.top()+self.point[1]*rect.height()
        painter.setPen(QPen(QColor('#FFD34E'),2));painter.drawEllipse(QPointF(x,y),12,12)
        painter.drawLine(QPointF(x-20,y),QPointF(x+20,y));painter.drawLine(QPointF(x,y-20),QPointF(x,y+20))
    def mousePressEvent(self,event):
        rect=self.image_rect()
        if not rect.contains(event.position()):return
        self.point=(max(.1,min(.9,(event.position().x()-rect.left())/rect.width())),
                    max(.1,min(.9,(event.position().y()-rect.top())/rect.height())))
        self.update()


class EditorialDialog(QDialog):
    def __init__(self,parent,source,parts,plan=None):
        super().__init__(parent);self.setWindowTitle('Dựng hình & âm thanh · duyệt theo từng cảnh')
        self.parts=deepcopy(parts);self.source=source;self.plan=deepcopy(plan) if plan else dict(version=1,style='clean',events=[],music_arc=True)
        self.row=-1;self.loading=False;self.worker=None;self.temp=tempfile.TemporaryDirectory(prefix='bq_edit_preview_',ignore_cleanup_errors=True)
        outer=QVBoxLayout(self)
        note=QLabel('Hiệu ứng là lựa chọn biên tập, không chứng minh lời kể đúng. Chữ nhấn trong phần mở đầu thay tiêu đề hook của mẫu để tránh chồng chữ. Xem thử dùng tiếng gốc và khung thử. Lưu ở đây chưa duyệt; cần Lưu & duyệt trong cửa sổ Kịch bản.')
        note.setWordWrap(True);outer.addWidget(note)
        self.enabled=QCheckBox('Dùng bộ dựng này thay điểm nhấn/tiếng động tự động của mẫu');self.enabled.setChecked(self.plan.get('enabled',True));outer.addWidget(self.enabled)
        bar=QHBoxLayout();outer.addLayout(bar);self.style=QComboBox()
        for k,v in STYLES.items():self.style.addItem(v,k)
        self.style.setCurrentIndex(max(0,self.style.findData(self.plan['style'])));bar.addWidget(self.style)
        suggest=QPushButton('Gợi ý lại theo lời / điểm nhấn');bar.addWidget(suggest);suggest.clicked.connect(self.suggest)
        self.arc=QCheckBox('Nhạc theo diễn biến');self.arc.setChecked(self.plan.get('music_arc',True));bar.addWidget(self.arc)
        self.transitions=QCheckBox('Chuyển cảnh theo bộ dựng');self.transitions.setChecked(self.plan.get('transitions',True));outer.addWidget(self.transitions)
        from app.core.report_layout import LAYOUTS
        layout_row=QHBoxLayout();outer.addLayout(layout_row);self.layout_choice=QComboBox()
        for key,label in LAYOUTS.items():self.layout_choice.addItem(label,key)
        self.layout_choice.setCurrentIndex(max(0,self.layout_choice.findData(self.plan.get('layout','template'))));layout_row.addWidget(self.layout_choice)
        self.report_title=QLineEdit(self.plan.get('report_title',''));self.report_title.setMaxLength(140);self.report_title.setPlaceholderText('Tiêu đề phóng sự · chỉ dùng thông tin đã kiểm tra');layout_row.addWidget(self.report_title,1)
        layout_note=QLabel('Mẫu phóng sự dùng khung dọc, giữ trọn hình; thay lớp chữ/phụ đề của mẫu bằng thẻ lời kể theo cảnh. Zoom/lia dùng tọa độ khung xuất; mũi tên bám vật cần chọn đích.');layout_note.setWordWrap(True);outer.addWidget(layout_note)
        body=QHBoxLayout();outer.addLayout(body,1)
        left=QVBoxLayout();body.addLayout(left,1);self.items=QListWidget();left.addWidget(self.items)
        row=QHBoxLayout();left.addLayout(row)
        add=QPushButton('+ Điểm nhấn');delete=QPushButton('Bỏ điểm');row.addWidget(add);row.addWidget(delete)
        add.clicked.connect(self.add);delete.clicked.connect(self.delete)
        pane=QWidget();form=QFormLayout(pane);scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(pane);body.addWidget(scroll,2)
        self.scene=QComboBox()
        for i,p in enumerate(parts):self.scene.addItem(f"Cảnh {i+1} · {p['start']:.1f}–{p['end']:.1f}s",i)
        form.addRow('Cảnh nguồn',self.scene)
        self.kind=QComboBox()
        for k,v in KINDS.items():self.kind.addItem(v,k)
        form.addRow('Hiệu ứng',self.kind)
        self.offset=self.spin(0,600,1);form.addRow('Sau đầu cảnh (giây)',self.offset)
        self.duration=self.spin(.2,4,1.2);form.addRow('Hiện trong (giây)',self.duration)
        self.text=QLineEdit();self.text.setMaxLength(72);form.addRow('Chữ nhấn',self.text)
        self.x=self.spin(5,95,50);self.y=self.spin(5,95,22);self.size=self.spin(8,45,18)
        form.addRow('Ngang (% khung)',self.x);form.addRow('Dọc (% khung)',self.y);form.addRow('Cỡ (% chiều ngang)',self.size)
        self.zoom_end=self.spin(100,135,112);self.end_x=self.spin(5,95,50);self.end_y=self.spin(5,95,50)
        form.addRow('Keyframe: zoom cực đại (%)',self.zoom_end);form.addRow('Keyframe: đích ngang (%)',self.end_x);form.addRow('Keyframe: đích dọc (%)',self.end_y)
        self.track=QCheckBox('Bám chi tiết · chỉ mũi tên / khoanh');form.addRow(self.track)
        self.tx=self.spin(10,90,50);self.ty=self.spin(10,90,50)
        form.addRow('Tâm vật ngang (% nguồn)',self.tx);form.addRow('Tâm vật dọc (% nguồn)',self.ty)
        target=QPushButton('Chọn vật trên hình nguồn…');target.clicked.connect(self.pick_target);form.addRow(target)
        warning=QLabel('Bám vật so khớp ảnh trong cửa sổ ngắn, tự ẩn khi mất dấu. Tâm vật tính trên nguồn chưa cắt/lật. Không hỗ trợ cắt viền, metadata xoay hoặc tỉ lệ điểm ảnh đặc biệt. Luôn xem thử; không tự nhận diện người/vật.')
        warning.setWordWrap(True);form.addRow(warning)
        self.sound=QComboBox()
        for name in SOUNDS:self.sound.addItem('Không tiếng nhấn' if name=='none' else name,name)
        form.addRow('Nhóm âm thanh',self.sound)
        self.variant=QComboBox();form.addRow('Tiếng cụ thể',self.variant)
        self.gain=self.spin(0,100,70);form.addRow('Mức tiếng nhấn (%)',self.gain)
        self.reason=QLineEdit();self.reason.setMaxLength(240);form.addRow('Lý do dùng',self.reason)
        hear=QPushButton('Nghe tiếng đang chọn');hear.clicked.connect(self.hear);form.addRow(hear)
        from PyQt6.QtMultimedia import QMediaPlayer,QAudioOutput
        from PyQt6.QtMultimediaWidgets import QVideoWidget
        self.video_surface=QVideoWidget();self.video_surface.setMinimumSize(180,220);left.addWidget(self.video_surface,1)
        self.player=QMediaPlayer(self);self.audio=QAudioOutput(self);self.player.setAudioOutput(self.audio);self.player.setVideoOutput(self.video_surface)
        self.info=QLabel('Chọn điểm nhấn rồi bấm Xem thử.');self.info.setWordWrap(True);outer.addWidget(self.info)
        self.player.errorOccurred.connect(lambda code,msg:self.info.setText('Không phát được: '+msg))
        buttons=QHBoxLayout();outer.addLayout(buttons)
        self.preview_button=QPushButton('Xem thử điểm nhấn');self.preview_button.clicked.connect(self.preview);buttons.addWidget(self.preview_button)
        again=QPushButton('Phát lại bản thử');again.clicked.connect(lambda:(self.player.setPosition(0),self.player.play()));buttons.addWidget(again)
        save=QPushButton('Lưu chỉnh sửa');save.clicked.connect(self.save);buttons.addWidget(save)
        close=QPushButton('Hủy');close.clicked.connect(self.reject);buttons.addWidget(close)
        self.items.currentRowChanged.connect(self.select);self.sound.currentIndexChanged.connect(self.fill_sounds)
        self.refresh();fit_dialog(self,1050,760)

    @staticmethod
    def spin(lo,hi,value):
        item=QDoubleSpinBox();item.setRange(lo,hi);item.setDecimals(2);item.setValue(value);return item

    def fill_sounds(self):
        from app.core.ffmpeg_utils import _sfx_library
        self.variant.clear();self.variant.addItem('Tự chọn trong nhóm','')
        for path in _sfx_library().get(self.sound.currentData(),[]):self.variant.addItem(Path(path).stem,Path(path).name)

    def store_row(self):
        if self.row<0:return
        self.plan['events'][self.row]=dict(part=self.scene.currentData(),kind=self.kind.currentData(),
            offset=self.offset.value(),duration=self.duration.value(),text=self.text.text(),
            x=self.x.value()/100,y=self.y.value()/100,size=self.size.value()/100,
            zoom_end=self.zoom_end.value()/100,end_x=self.end_x.value()/100,end_y=self.end_y.value()/100,
            track=self.track.isChecked(),target_x=self.tx.value()/100,target_y=self.ty.value()/100,
            sound=self.sound.currentData(),sound_file=self.variant.currentData() or '',sound_gain=self.gain.value()/100,reason=self.reason.text())
        e=self.plan['events'][self.row]
        self.items.item(self.row).setText(f"Cảnh {e['part']+1} · +{e['offset']:.1f}s · {KINDS[e['kind']]}")

    def select(self,index):
        if self.loading:return
        self.store_row();self.row=index
        if index<0:return
        e=self.plan['events'][index]
        self.scene.setCurrentIndex(e['part']);self.kind.setCurrentIndex(max(0,self.kind.findData(e['kind'])))
        for field,key,default,mult in [(self.offset,'offset',0,1),(self.duration,'duration',1.2,1),
            (self.x,'x',.5,100),(self.y,'y',.22,100),(self.size,'size',.18,100),
            (self.zoom_end,'zoom_end',1.12,100),(self.end_x,'end_x',.5,100),(self.end_y,'end_y',.5,100),
            (self.tx,'target_x',.5,100),(self.ty,'target_y',.5,100),(self.gain,'sound_gain',.7,100)]:field.setValue(e.get(key,default)*mult)
        self.text.setText(e.get('text',''));self.reason.setText(e.get('reason',''));self.track.setChecked(e.get('track',False))
        self.sound.setCurrentIndex(max(0,self.sound.findData(e.get('sound','none'))));self.fill_sounds()
        selected=e.get('sound_file','')
        index=self.variant.findData(selected)
        if selected and index<0:
            # Keep the saved choice: reopening must not silently switch to a
            # random sound when an asset is missing on this machine.
            self.variant.addItem('Thiếu file: '+selected,selected)
            index=self.variant.count()-1
        self.variant.setCurrentIndex(max(0,index))

    def refresh(self,index=0):
        self.loading=True;self.row=-1;self.items.clear()
        for e in self.plan['events']:self.items.addItem(f"Cảnh {e['part']+1} · +{e['offset']:.1f}s · {KINDS[e['kind']]}")
        self.loading=False
        if self.items.count():self.items.setCurrentRow(min(index,self.items.count()-1))

    def add(self):
        self.store_row()
        if len(self.plan['events'])>=12:return self.error('Tối đa 12 điểm nhấn mỗi Part.')
        self.plan['events'].append(dict(part=self.scene.currentIndex(),kind='arrow',offset=0.,duration=1.))
        self.refresh(len(self.plan['events'])-1)

    def delete(self):
        if self.row>=0:del self.plan['events'][self.row];self.refresh()

    def suggest(self):
        if self.plan['events'] and QMessageBox.question(self,'Thay các điểm nhấn?', 'Tạo lại sẽ thay các điểm nhấn đang chỉnh trong cửa sổ này.')!=QMessageBox.StandardButton.Yes:return
        self.plan=propose(self.parts,self.style.currentData());self.plan.update(layout=self.layout_choice.currentData(),report_title=self.report_title.text());self.refresh()

    def checked(self):
        self.store_row();self.plan['style']=self.style.currentData();self.plan['music_arc']=self.arc.isChecked()
        self.plan['layout']=self.layout_choice.currentData();self.plan['report_title']=self.report_title.text()
        self.plan['enabled']=self.enabled.isChecked()
        self.plan['transitions']=self.transitions.isChecked()
        return validate(self.plan,self.parts)

    def error(self,message):QMessageBox.warning(self,'Chưa áp dụng được',str(message))

    def hear(self):
        from app.core.ffmpeg_utils import _assets_sfx_dir
        name=self.variant.currentData()
        if not name:return self.error('Chọn một tiếng cụ thể để nghe thử.')
        self.player.stop();self.audio.setVolume(self.gain.value()/100)
        self.player.setSource(QUrl.fromLocalFile(str(_assets_sfx_dir()/self.sound.currentData()/name)));self.player.play()

    def preview(self):
        if self.row<0 and self.layout_choice.currentData()=='template':return
        if not self.enabled.isChecked():return self.error('Bộ dựng đang tắt; bản xuất sẽ dùng hiệu ứng mẫu cũ.')
        if self.worker and self.worker.isRunning():return
        try:
            self.store_row();event=deepcopy(self.plan['events'][self.row]) if self.row>=0 else None;plan=self.checked()
            # Validation sorts events: locate selected row by its immutable source interval.
            index=next(i for i,e in enumerate(plan['events']) if e['part']==event['part'] and e['offset']==event['offset']) if event else None
        except (ValueError,StopIteration) as exc:return self.error(exc)
        self.player.stop();self.player.setSource(QUrl());self.info.setText('Đang dựng bản thử trên máy…');self.preview_button.setEnabled(False)
        self.worker=Preview(self.source,self.parts,plan,index,self.temp.name,self)
        self.worker.result.connect(self.ready);self.worker.finished.connect(lambda:self.preview_button.setEnabled(True));self.worker.start()

    def ready(self,path,note):
        self.info.setText(note)
        if path:self.audio.setVolume(1);self.player.setSource(QUrl.fromLocalFile(path));self.player.play()

    def pick_target(self):
        if self.row<0 or (self.worker and self.worker.isRunning()):return
        if self.kind.currentData() not in ('arrow','circle'):return self.error('Chọn mũi tên hoặc khoanh chi tiết để bám vật.')
        part=self.parts[self.scene.currentIndex()];at=part['start']+self.offset.value()
        if at>=part['end']:return self.error('Mốc chọn nằm ngoài cảnh.')
        self.info.setText('Đang lấy hình nguồn…');self.preview_button.setEnabled(False)
        self.target_context=(self.row,self.scene.currentIndex(),self.offset.value(),self.kind.currentData())
        self.worker=SourceFrame(self.source,at,self.temp.name,self)
        self.worker.result.connect(self.target_ready);self.worker.finished.connect(lambda:self.preview_button.setEnabled(True));self.worker.start()

    def target_ready(self,path,error):
        if self.target_context!=(self.row,self.scene.currentIndex(),self.offset.value(),self.kind.currentData()):
            self.info.setText('Cảnh hoặc điểm nhấn đã đổi; bấm Chọn vật để lấy hình mới.');return
        if not path:return self.error(error)
        from PyQt6.QtGui import QPixmap
        pixmap=QPixmap(path)
        if pixmap.isNull():return self.error('Không đọc được hình nguồn.')
        dialog=QDialog(self);dialog.setWindowTitle('Bấm vào chi tiết cần bám trên hình nguồn')
        layout=QVBoxLayout(dialog);picture=TargetImage(pixmap);picture.point=(self.tx.value()/100,self.ty.value()/100);layout.addWidget(picture,1)
        label=QLabel('Chọn chi tiết có đường nét rõ. Khi đổi cảnh hoặc vật bị che, sticker sẽ tự ẩn.');label.setWordWrap(True);layout.addWidget(label)
        button=QPushButton('Dùng vị trí này');button.clicked.connect(dialog.accept);layout.addWidget(button);fit_dialog(dialog,850,580)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            self.tx.setValue(picture.point[0]*100);self.ty.setValue(picture.point[1]*100);self.track.setChecked(True)
        self.info.setText('Đã chọn tâm vật; bấm Xem thử để kiểm tra bám đúng.')

    def save(self):
        if self.worker and self.worker.isRunning():return self.error('Chờ dựng thử xong trước khi đóng.')
        try:self.plan=self.checked()
        except ValueError as exc:return self.error(exc)
        self.accept()

    def done(self,result):
        if self.worker and self.worker.isRunning():self.info.setText('Đang dựng thử; chờ hoàn tất trước khi đóng.');return
        self.player.stop();self.player.setSource(QUrl())
        super().done(result)
        self.temp.cleanup()

    def closeEvent(self,event):
        if self.worker and self.worker.isRunning():event.ignore();return
        super().closeEvent(event)
