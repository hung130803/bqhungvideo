"""Bố cục dùng chung: menu chức năng và nhảy nhanh trong biểu mẫu dài."""
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QMenu, QPushButton


def button_menu(parent, text, buttons):
    """Gom nút vào menu, giữ chính signal/handler và trạng thái enabled cũ."""
    button = QPushButton(text, parent)
    button.setProperty('ghost', True)
    menu = QMenu(button)
    pairs = []
    for original in buttons:
        original.setParent(parent)
        original.hide()
        action = menu.addAction(original.text())
        action.setToolTip(original.toolTip())
        action.triggered.connect(lambda _=False, b=original: b.click())
        pairs.append((action, original))

    def sync():
        for action, original in pairs:
            action.setEnabled(original.isEnabled())
            action.setText(original.text())
    menu.aboutToShow.connect(sync)
    button.setMenu(menu)
    return button


class SectionJump(QComboBox):
    """Tìm và cuộn tới nhóm cài đặt; không thay giá trị các trường trong nhóm."""
    def __init__(self, scroll, parent=None):
        super().__init__(parent)
        self.scroll = scroll
        self.sections = []
        self.addItem('Đi tới mục cài đặt…')
        self.setMinimumContentsLength(16)
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.setToolTip('Chọn mục để cuộn tới. Các giá trị đang chỉnh được giữ nguyên.')
        self.activated.connect(self.jump)

    def add_section(self, title, widget):
        self.sections.append(widget)
        self.addItem(title)

    def jump(self, index):
        if 0 < index <= len(self.sections):
            widget = self.sections[index-1]
            pos = widget.mapTo(self.scroll.widget(), widget.rect().topLeft())
            self.scroll.verticalScrollBar().setValue(max(0, pos.y()-8))

    def wheelEvent(self, event):
        event.ignore()


def jump_row(scroll, parent=None):
    row = QHBoxLayout()
    row.addWidget(QLabel('Đi tới'))
    jump = SectionJump(scroll, parent)
    row.addWidget(jump, 1)
    return row, jump


def fit_dialog(dialog, width, height):
    screen = dialog.screen()
    geometry = screen.availableGeometry() if screen else None
    if geometry:
        width = min(width, max(440, geometry.width()-50))
        height = min(height, max(380, geometry.height()-65))
    dialog.resize(width, height)
