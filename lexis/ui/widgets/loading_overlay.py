"""
Lexis — Widget: Loading Overlay

İçerik alanını kaplayan animasyonlu yükleme göstergesi.
"""

from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, QTimer, pyqtProperty
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class SpinnerWidget(QWidget):
    """Dönen daire animasyonu."""

    def __init__(self, parent: QWidget | None = None, size: int = 40, color: str = "#7C6EE8") -> None:
        super().__init__(parent)
        self._size = size
        self._color = QColor(color)
        self._angle = 0
        self.setFixedSize(size, size)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.start(16)  # ~60 fps

    def _rotate(self) -> None:
        self._angle = (self._angle + 6) % 360
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(self._color, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        rect_size = self._size - 8
        x = (self._size - rect_size) // 2
        y = (self._size - rect_size) // 2

        painter.drawArc(x, y, rect_size, rect_size, self._angle * 16, 270 * 16)

    def stop(self) -> None:
        self._timer.stop()

    def start(self) -> None:
        if not self._timer.isActive():
            self._timer.start(16)


class LoadingOverlay(QWidget):
    """
    Ebeveyn widget'ı kaplayan yarı-saydam yükleme katmanı.
    """

    def __init__(self, parent: QWidget, message: str = "İçerik üretiliyor...") -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background-color: rgba(11, 13, 23, 0.85); border-radius: 14px;")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        self._spinner = SpinnerWidget(self, size=48)
        layout.addWidget(self._spinner, alignment=Qt.AlignmentFlag.AlignCenter)

        self._msg_label = QLabel(message)
        self._msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._msg_label.setStyleSheet("""
            color: #8B8FA8;
            font-size: 13px;
            font-weight: 500;
            background: transparent;
        """)
        layout.addWidget(self._msg_label)

        self.hide()

    def set_message(self, text: str) -> None:
        self._msg_label.setText(text)

    def show_loading(self, message: str = "") -> None:
        if message:
            self._msg_label.setText(message)
        self._spinner.start()
        self.resize(self.parent().size())
        self.raise_()
        self.show()

    def hide_loading(self) -> None:
        self._spinner.stop()
        self.hide()

    def resizeEvent(self, event) -> None:
        if self.parent():
            self.resize(self.parent().size())
        super().resizeEvent(event)
