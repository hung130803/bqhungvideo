from PyQt6.QtWidgets import (QDialog,QVBoxLayout,QLabel,QCheckBox,QComboBox,QSpinBox,
                            QLineEdit,QPushButton,QMessageBox,QFormLayout)
from PyQt6.QtCore import Qt
from app.ui.appsettings import app_settings
from app.ui.theme import SP_2,SP_3,SP_4,pad,set_role,set_variant


class TwelveDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle('TwelveLabs · hỗ trợ tìm cảnh'); self.setMinimumWidth(520)
        self.s=app_settings(); lay=QVBoxLayout(self); pad(lay,SP_4,spacing=SP_3)
        label=QLabel('Khi bật, video sẽ được gửi lên TwelveLabs để tìm tình tiết.\n'
                     'Dùng dung lượng và hạn mức tài khoản. Groq vẫn kiểm tra và viết kịch bản.\n'
                     'Kết quả đã xong được lưu trên máy; không tự đổi sang tài khoản khác.')
        label.setWordWrap(True);set_role(label,'muted');lay.addWidget(label)
        self.enabled=QCheckBox('Bật cho lần phân tích mới và dây chuyền dựng chuyện AI')
        self.enabled.setChecked(str(self.s.value('story_twelve',False)).lower() in ('true','1'));lay.addWidget(self.enabled)
        from app.ai.twelve_keys import load
        try:self.keys=load()
        except RuntimeError:self.keys=[]
        form=QFormLayout();form.setHorizontalSpacing(SP_3);form.setVerticalSpacing(SP_2);lay.addLayout(form)
        self.slot=QComboBox()
        for i,_ in enumerate(self.keys):self.slot.addItem(f'Key {i+1}',i)
        self.slot.setCurrentIndex(max(0,self.slot.findData(self.s.value('story_twelve_key',0,type=int))))
        form.addRow('Key dùng cho công việc mới',self.slot)
        self.index=QLineEdit(str(self.s.value('story_twelve_index','')))
        self.index.setPlaceholderText('Để trống: kho Marengo đầu tiên của key')
        form.addRow('Mã kho (Index ID)',self.index)
        self.minutes=QSpinBox();self.minutes.setRange(1,120)
        self.minutes.setValue(self.s.value('story_twelve_max_minutes',60,type=int))
        form.addRow('Tối đa phút/video được gửi',self.minutes)
        self.newkey=QLineEdit();self.newkey.setEchoMode(QLineEdit.EchoMode.Password)
        self.newkey.setPlaceholderText('Dán key mới nếu muốn thêm; không cần nhập lại key cũ')
        form.addRow('Thêm key',self.newkey)
        info=QLabel('Đầy kho/hết hạn mức: giữ tiến độ và báo rõ để xử lý.\n'
                    'Bản trên TwelveLabs hiện được giữ lại để hỏi tiếp; chưa tự xóa.\n'
                    'Giới hạn 200 MB/bản gửi; video gốc và mẫu xuất không đổi.')
        info.setWordWrap(True);set_role(info,'hint');lay.addWidget(info)
        button=QPushButton('Lưu');set_variant(button,'primary');button.clicked.connect(self.store)
        lay.addWidget(button,0,Qt.AlignmentFlag.AlignRight)

    def store(self):
        from app.ai.twelve_keys import save
        keys=list(self.keys)
        if self.newkey.text().strip() and self.newkey.text().strip() not in keys:keys.append(self.newkey.text().strip())
        if self.enabled.isChecked() and not keys:
            QMessageBox.warning(self,'Thiếu key','Nhập key TwelveLabs trước khi bật.');return
        index=self.index.text().strip()
        if index and (len(index)!=24 or any(c not in '0123456789abcdefABCDEF' for c in index)):
            QMessageBox.warning(self,'Mã kho','Index ID cần là mã 24 ký tự, không phải tên kho.');return
        try:save(keys)
        except (RuntimeError,ValueError,OSError) as exc:
            QMessageBox.warning(self,'Chưa lưu được',str(exc));return
        self.s.setValue('story_twelve',self.enabled.isChecked())
        self.s.setValue('story_twelve_key',self.slot.currentData() or 0)
        self.s.setValue('story_twelve_index',index)
        self.s.setValue('story_twelve_max_minutes',self.minutes.value())
        self.accept()
