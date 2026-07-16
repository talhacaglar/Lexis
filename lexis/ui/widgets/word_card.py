"""
Lexis — Widget: Word Card

Kelime listesinde kullanılan hover-animasyonlu kart widget'ı.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from lexis.domain.models import Word
from lexis.ui.widgets.common import StatusBadge


class WordCard(QFrame):
    """
    Tek bir kelimeyi temsil eden tıklanabilir kart.
    Hover'da yumuşak bir border animasyonu gösterir.
    """

    clicked = pyqtSignal(str)          # word_id
    favorite_toggled = pyqtSignal(str) # word_id
    delete_requested = pyqtSignal(str) # word_id

    def __init__(self, word: Word, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._word = word
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName("card")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumHeight(148)
        self.setMaximumHeight(176)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # ── Top Row: Term + Favorite ──
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)

        self._term_label = QLabel(self._word.term)
        self._term_label.setObjectName("cardTerm")

        self._fav_btn = QPushButton("♥")
        self._fav_btn.setObjectName("favoriteBtn")
        self._fav_btn.setFixedSize(30, 30)
        self._fav_btn.setProperty("active", str(self._word.is_favorite).lower())
        self._fav_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._fav_btn.clicked.connect(self._on_favorite)
        self._fav_btn.setToolTip("Favorilere ekle/çıkar")
        self._fav_btn.setAccessibleName("Favorilere ekle/çıkar")

        top.addWidget(self._term_label, 1)
        top.addWidget(self._fav_btn)
        layout.addLayout(top)

        # ── Badges Row: Language + Status + POS ──
        badges = QHBoxLayout()
        badges.setContentsMargins(0, 0, 0, 0)
        badges.setSpacing(6)

        lang_badge = QLabel(self._word.language.upper())
        lang_badge.setObjectName("langBadge")

        badges.addWidget(lang_badge)
        badges.addWidget(
            StatusBadge(self._word.status.value, self._word.status.display_name)
        )

        if self._word.part_of_speech:
            pos_badge = QLabel(self._word.part_of_speech)
            pos_badge.setObjectName("posBadge")
            badges.addWidget(pos_badge)

        badges.addStretch()
        layout.addLayout(badges)

        # ── Definition Preview ──
        definition = self._word.definition_short or self._word.definition
        if definition:
            preview = definition[:110] + ("…" if len(definition) > 110 else "")
            def_label = QLabel(preview)
            def_label.setObjectName("cardPreview")
            def_label.setWordWrap(True)
            layout.addWidget(def_label, 1)
        else:
            layout.addStretch(1)

        # ── Tags Row ──
        if self._word.tags:
            tags_row = QHBoxLayout()
            tags_row.setContentsMargins(0, 0, 0, 0)
            tags_row.setSpacing(4)
            for tag in self._word.tags[:3]:
                t = QLabel(f"#{tag}")
                t.setObjectName("cardTag")
                tags_row.addWidget(t)
            tags_row.addStretch()
            layout.addLayout(tags_row)

    def update_word(self, word: Word) -> None:
        """Kart verisi güncellenir."""
        self._word = word
        # Basit güncelleme: kartı yeniden oluştur
        for child in self.findChildren(QWidget):
            child.deleteLater()
        self._setup_ui()

    def _on_favorite(self) -> None:
        self.favorite_toggled.emit(self._word.id)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._word.id)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event) -> None:
        # Menü stili global QSS'teki QMenu kurallarından gelir.
        menu = QMenu(self)
        del_action = menu.addAction("Sil")
        action = menu.exec(event.globalPos())
        if action == del_action:
            self.delete_requested.emit(self._word.id)

    @property
    def word_id(self) -> str:
        return self._word.id
