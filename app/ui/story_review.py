"""Expose source evidence and narration instead of opaque AI quality scores."""
import json
from copy import deepcopy
from pathlib import Path
from PyQt6.QtCore import QUrl,Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QApplication,QLabel,QTableWidget,QTableWidgetItem,QHeaderView,QPlainTextEdit,QPushButton,QAbstractItemView,QMessageBox,QComboBox,QSlider
from app.ui.layout_tools import fit_dialog


def preview_scene(parent,source,start,end):
    """Review the actual selected interval without creating or changing media."""
    from PyQt6.QtMultimedia import QMediaPlayer,QAudioOutput
    from PyQt6.QtMultimediaWidgets import QVideoWidget
    dlg=QDialog(parent);dlg.setWindowTitle(f'Cảnh nguồn {start:.1f}–{end:.1f}s')
    lay=QVBoxLayout(dlg);screen=QVideoWidget();lay.addWidget(screen,1)
    player=QMediaPlayer(dlg);audio=QAudioOutput(dlg);player.setAudioOutput(audio);player.setVideoOutput(screen)
    a,b=int(start*1000),int(end*1000);slider=QSlider(Qt.Orientation.Horizontal);slider.setRange(a,b);lay.addWidget(slider)
    info=QLabel(f'Chỉ phát khoảng nguồn {start:.1f}–{end:.1f}s; chưa có giọng AI hoặc hiệu ứng.');info.setWordWrap(True);lay.addWidget(info)
    row=QHBoxLayout();lay.addLayout(row);play=QPushButton('Phát / tạm dừng');row.addWidget(play)
    external=QPushButton('Mở nguồn bằng Windows');row.addWidget(external)
    external.clicked.connect(lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(source)))
    def toggle():
        if player.playbackState()==QMediaPlayer.PlaybackState.PlayingState:player.pause()
        else:
            if player.position()<a or player.position()>=b:player.setPosition(a)
            player.play()
    play.clicked.connect(toggle)
    def position(ms):
        if not slider.isSliderDown():slider.setValue(max(a,min(b,ms)))
        if ms>=b:player.pause()
    player.positionChanged.connect(position)
    slider.sliderReleased.connect(lambda:player.setPosition(slider.value()))
    loaded=False
    def ready(status):
        nonlocal loaded
        if status==QMediaPlayer.MediaStatus.LoadedMedia and not loaded:
            loaded=True;player.setPosition(a);player.play()
    player.mediaStatusChanged.connect(ready)
    player.errorOccurred.connect(lambda code,message:info.setText('Trình phát gặp lỗi: '+message+' · Bấm Mở nguồn bằng Windows để đối chiếu.'))
    player.setSource(QUrl.fromLocalFile(source));fit_dialog(dlg,850,570)
    try:dlg.exec()
    finally:player.stop();player.setSource(QUrl())


def show_story(parent,meta,clip_id=None):
    from app.ai.story_quality import approve_script,digest,is_approved
    revision=digest(meta);saved=False;voice=meta.get('voice','');edit_plan=deepcopy(meta.get('edit_plan'));music=meta.get('music_path','')
    dlg=QDialog(parent);dlg.setWindowTitle('Kịch bản & căn cứ từ video nguồn')
    lay=QVBoxLayout(dlg)
    note=QLabel('Groq có thể nhận sai hình. Mở video nguồn để đối chiếu mốc thời gian; nhấp đúp ô Lời kể để sửa. Chỉ bấm Lưu & duyệt khi đã xem từng câu. Đóng cửa sổ không có nghĩa là duyệt.')
    note.setWordWrap(True);lay.addWidget(note)
    from app.core.music_library import describe
    music_row=QHBoxLayout();lay.addLayout(music_row)
    try:music_description=describe(music)
    except (OSError,ValueError):music_description='Không tìm thấy bài đã chọn; hãy chọn lại nhạc.'
    music_label=QLabel('Nhạc: '+music_description);music_label.setWordWrap(True);music_label.setTextFormat(Qt.TextFormat.PlainText);music_row.addWidget(music_label,1)
    choose_music=QPushButton('Đổi nhạc / nghe thử');choose_music.setEnabled(clip_id is not None);music_row.addWidget(choose_music)
    def change_music():
        nonlocal music
        from app.ui.music_picker import MusicPicker
        picker=MusicPicker(dlg,music,allow_auto=False)
        if picker.exec()==QDialog.DialogCode.Accepted:
            music=picker.selection;music_label.setText('Nhạc: '+describe(music)+' · áp dụng khi Lưu & duyệt')
    choose_music.clicked.connect(change_music)
    parts=meta['parts'] if clip_id is not None else meta.get('rendered_parts') or meta['parts']
    state=QLabel(('Đã duyệt' if is_approved(meta) else 'CHỜ DUYỆT')+' · Giữ nguyên lời đã duyệt. Câu quá dài sẽ yêu cầu bạn viết ngắn rồi duyệt lại.')
    state.setWordWrap(True);lay.addWidget(state)
    angle=QLabel('Góc kể: '+str(meta.get('angle') or 'Theo nội dung nguồn'))
    angle.setTextFormat(Qt.TextFormat.PlainText);angle.setWordWrap(True);lay.addWidget(angle)
    voice_row=QHBoxLayout();lay.addLayout(voice_row)
    voice_label=QLabel('Giọng đọc: '+voice);voice_label.setTextFormat(Qt.TextFormat.PlainText);voice_row.addWidget(voice_label,1)
    change_voice=QPushButton('Chọn giọng / nghe thử');change_voice.setEnabled(clip_id is not None);voice_row.addWidget(change_voice)
    def choose_voice():
        nonlocal voice
        from app.ui.recap_settings import RecapSettingsDialog
        picker=RecapSettingsDialog(dlg,voice_only=True,initial_voice=voice)
        if picker.exec()==QDialog.DialogCode.Accepted:
            from app.core.dubbing import default_voice
            voice=picker.voice.currentData() or default_voice(meta.get('lang','vi'))
            voice_label.setText('Giọng đọc: '+voice+' · áp dụng khi Lưu & duyệt')
    change_voice.clicked.connect(choose_voice)
    if meta.get('hooks'):
        hook_row=QHBoxLayout();lay.addLayout(hook_row);hook_row.addWidget(QLabel('Gợi ý mở đầu:'))
        hooks=QComboBox();hooks.setMinimumWidth(150)
        for i,h in enumerate(meta['hooks']):hooks.addItem(f'{i+1}. {h}',h)
        hooks.setCurrentIndex(max(0,min(hooks.count()-1,int(meta.get('selected_hook',0)))))
        hooks.setToolTip('Gợi ý của AI; chép rồi sửa câu đầu trong bảng sau khi đối chiếu nguồn.')
        hook_row.addWidget(hooks,1);copy_hook=QPushButton('Chép hook');hook_row.addWidget(copy_hook)
        copy_hook.clicked.connect(lambda:QApplication.clipboard().setText(hooks.currentData() or ''))
    if (meta.get('review') or {}).get('approved') is False:
        warning=QPlainTextEdit();warning.setReadOnly(True);warning.setMaximumHeight(70)
        warning.setPlainText('CẦN KIỂM TRA / SỬA: '+str(meta['review'].get('issues','Cần đối chiếu lại nguồn.')))
        lay.addWidget(warning)
    from app.core.story_craft import DELIVERY,ENERGY
    deliveries=[];energies=[]
    table=QTableWidget(len(parts),5);table.setHorizontalHeaderLabels(['Mốc nguồn','Vai','Lời kể','Nhịp đọc','Nhạc trong cảnh'])
    table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.EditKeyPressed if clip_id is not None else QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
    for i,p in enumerate(parts):
        for j,value in enumerate((f"{p['start']:.1f}–{p['end']:.1f}s",'Giữ tiếng gốc' if p['mode']=='orig' else 'Thuyết minh',p['text'])):
            item=QTableWidgetItem(value)
            if j!=2 or p['mode']!='narrate':item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(i,j,item)
        choice=QComboBox()
        for key,label in DELIVERY.items():choice.addItem(label,key)
        choice.setCurrentIndex(max(0,choice.findData(p.get('delivery','neutral'))))
        choice.setEnabled(clip_id is not None and p['mode']=='narrate')
        choice.setToolTip('Điều chỉnh nhịp đọc nhẹ; khả năng biểu cảm phụ thuộc giọng. Không đổi lời đã viết.')
        deliveries.append(choice);table.setCellWidget(i,3,choice)
        energy=QComboBox()
        for key,label in ENERGY.items():energy.addItem(label,key)
        energy.setCurrentIndex(max(0,energy.findData(p.get('music_energy','auto'))));energy.setEnabled(clip_id is not None)
        energy.setToolTip('Áp khi bật Phối nhạc theo lời kể; nếu dùng bộ dựng, cần bật Nhạc theo diễn biến. Tiếng gốc quan trọng luôn được ưu tiên.')
        energies.append(energy);table.setCellWidget(i,4,energy)
    table.resizeRowsToContents();lay.addWidget(table,3)
    evidence=QPlainTextEdit();evidence.setReadOnly(True);lay.addWidget(evidence,2)
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
        roles={'hook':'Mở đầu gây tò mò','setup':'Bối cảnh','build':'Diễn biến','payoff':'Kết quả / trả lời hook','ending':'Kết'}
        sound=p.get('sfx','none')
        if sound!='none' and 'sfx_offset' in p:
            sound+=f" · sau {p['sfx_offset']:.1f}s từ đầu cảnh · "+p.get('sfx_reason','')
        evidence.setPlainText('VAI TRÒ: '+roles.get(p.get('role'),p.get('mode',''))+'\nLÝ DO CHỌN: '+p.get('reason','')+'\nTIẾNG ĐỘNG: '+sound+'\n\n'+text)
    table.itemSelectionChanged.connect(selected)
    if parts:table.selectRow(0)
    row=QHBoxLayout();lay.addLayout(row)
    source=(meta.get('source_signature') or [''])[0]
    open_source=QPushButton('Mở video nguồn');open_source.setEnabled(bool(source) and Path(source).is_file())
    open_source.clicked.connect(lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(source)));row.addWidget(open_source)
    watch=QPushButton('Xem cảnh đang chọn');watch.setEnabled(open_source.isEnabled());row.addWidget(watch)
    def watch_selected():
        i=table.currentRow()
        if 0<=i<len(parts):preview_scene(dlg,source,parts[i]['start'],parts[i]['end'])
    watch.clicked.connect(watch_selected)
    edit=QPushButton('Dựng hình & âm thanh');edit.setEnabled(clip_id is not None);row.addWidget(edit)
    def edit_selected():
        nonlocal edit_plan
        from app.ui.editorial_dialog import EditorialDialog
        current=deepcopy(parts)
        for i,p in enumerate(current):p['text']=table.item(i,2).text()
        panel=EditorialDialog(dlg,source,current,edit_plan)
        if panel.exec()==QDialog.DialogCode.Accepted:
            edit_plan=panel.plan
            state.setText(f"Đã chỉnh {len(edit_plan['events'])} điểm nhấn · cần Lưu & duyệt để áp dụng; xuất lại nếu Part đã xuất.")
    edit.clicked.connect(edit_selected)
    copy=QPushButton('Chép kịch bản');copy.clicked.connect(lambda:QApplication.clipboard().setText('\n\n'.join(
        f"{p['start']:.1f}–{p['end']:.1f}s: {table.item(i,2).text() or '[Giữ tiếng gốc]'}" for i,p in enumerate(parts))));row.addWidget(copy)
    if clip_id is not None:
        approve=QPushButton('Lưu & duyệt');row.addWidget(approve)
        def save():
            nonlocal saved
            try:
                options={'voice':voice} if voice!=meta.get('voice','') else {}
                if edit_plan is not None:options['edit_plan']=edit_plan
                if music!=meta.get('music_path',''):options['music']=music
                chosen=[c.currentData() for c in deliveries]
                if chosen!=[p.get('delivery','neutral') for p in parts]:options['deliveries']=chosen
                chosen_energy=[c.currentData() for c in energies]
                if chosen_energy!=[p.get('music_energy','auto') for p in parts]:options['energies']=chosen_energy
                approve_script(clip_id,revision,[table.item(i,2).text() for i in range(len(parts))],**options)
            except (RuntimeError,ValueError,OSError) as exc:
                QMessageBox.warning(dlg,'Chưa duyệt được',str(exc));return
            saved=True;dlg.accept()
        approve.clicked.connect(save)
    row.addStretch();close=QPushButton('Đóng');close.clicked.connect(dlg.accept);row.addWidget(close)
    fit_dialog(dlg,1000,650);dlg.exec()
    return saved
