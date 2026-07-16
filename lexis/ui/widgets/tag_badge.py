"""
Lexis — Widget: Tag Badge

Etiket gösterimi için küçük, tıklanabilir chip widget.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from lexis.ui.theme import Colors


class TagBadge(QWidget):
    """
    Tek bir etiketi gösteren chip widget.
    İsteğe bağlı olarak silme butonu içerebilir.
    """

    remove_requested = pyqtSignal(str)  # tag name
    clicked = pyqtSignal(str)           # tag name

    def __init__(
        self,
        tag: str,
        removable: bool = False,
        clickable: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._tag = tag
        self._setup_ui(removable, clickable)

    def _setup_ui(self, removable: bool, clickable: bool) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        container_style = f"""
            background-color: {Colors.ACCENT_MUTED};
            border-radius: 8px;
            border: 1px solid {Colors.ACCENT};
        """

        container = QWidget()
        container.setStyleSheet(container_style)

        inner = QHBoxLayout(container)
        inner.setContentsMargins(8, 4, 6 if removable else 8, 4)
        inner.setSpacing(4)

        label = QLabel(f"#{self._tag}")
        label.setStyleSheet(f"""
            color: {Colors.ACCENT_LIGHT};
            font-size: 11px;
            font-weight: 600;
            background: transparent;
        """)
        inner.addWidget(label)

        if removable:
            remove_btn = QPushButton("×")
            remove_btn.setFixedSize(16, 16)
            remove_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            remove_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {Colors.TEXT_MUTED};
                    border: none;
                    border-radius: 3px;
                    font-size: 13px;
                    font-weight: 700;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    color: {Colors.ERROR};
                    background: rgba(239, 68, 68, 0.15);
                }}
            """)
            remove_btn.clicked.connect(lambda: self.remove_requested.emit(self._tag))
            inner.addWidget(remove_btn)

        if clickable:
            container.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            container.mousePressEvent = lambda e: self.clicked.emit(self._tag)

        layout.addWidget(container)

    @property
    def tag(self) -> str:
        return self._tag
