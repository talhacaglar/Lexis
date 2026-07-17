"""
Lexis — Widget: Word Card

Kelime listesinde kullanılan tıklanabilir kart.

Yapı bir kez kurulur (_setup_ui), veri ayrıca bağlanır (bind). Böylece
kütüphane filtrelenirken kartlar yok edilip yeniden yaratılmak yerine
yeniden kullanılabilir.
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
from lexis.ui.theme import repolish
from lexis.ui.widgets.common import StatusBadge

PREVIEW_CHARS = 110
MAX_TAGS = 3

# Kart ızgarası geometrisi — dashboard ve kütüphane aynı ölçüleri kullanır.
MIN_CARD_WIDTH = 300
MAX_COLUMNS = 4
GRID_MARGIN = 36
GRID_SPACING = 14


def grid_columns(available_width: int) -> int:
    """
    Verilen genişliğe sığan sütun sayısı.

    Sabit sütun sayısı dar pencerelerde kartları eziyordu.
    """
    width = available_width - GRID_MARGIN * 2
    return max(1, min(MAX_COLUMNS, (width + GRID_SPACING) // (MIN_CARD_WIDTH + GRID_SPACING)))


class WordCard(QFrame):
    """Tek bir kelimeyi temsil eden tıklanabilir kart."""

    clicked = pyqtSignal(str)  # word_id
    favorite_toggled = pyqtSignal(str)  # word_id
    delete_requested = pyqtSignal(str)  # word_id
    tag_clicked = pyqtSignal(str)  # tag adı

    def __init__(self, word: Word, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._word = word
        self._setup_ui()
        self.bind(word)

    def _setup_ui(self) -> None:
        self.setObjectName("card")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumHeight(148)
        self.setMaximumHeight(176)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # ── Üst satır: terim + favori ──
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)

        self._term_label = QLabel()
        self._term_label.setObjectName("cardTerm")

        self._fav_btn = QPushButton("♥")
        self._fav_btn.setObjectName("favoriteBtn")
        self._fav_btn.setFixedSize(30, 30)
        self._fav_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._fav_btn.clicked.connect(self._on_favorite)
        self._fav_btn.setToolTip("Favorilere ekle/çıkar")
        self._fav_btn.setAccessibleName("Favorilere ekle/çıkar")

        top.addWidget(self._term_label, 1)
        top.addWidget(self._fav_btn)
        layout.addLayout(top)

        # ── Rozetler: dil + durum + tür ──
        badges = QHBoxLayout()
        badges.setContentsMargins(0, 0, 0, 0)
        badges.setSpacing(6)

        self._lang_badge = QLabel()
        self._lang_badge.setObjectName("langBadge")
        self._status_badge = StatusBadge("new", "")
        self._pos_badge = QLabel()
        self._pos_badge.setObjectName("posBadge")

        badges.addWidget(self._lang_badge)
        badges.addWidget(self._status_badge)
        badges.addWidget(self._pos_badge)
        badges.addStretch()
        layout.addLayout(badges)

        # ── Tanım önizlemesi ──
        self._preview_label = QLabel()
        self._preview_label.setObjectName("cardPreview")
        self._preview_label.setWordWrap(True)
        layout.addWidget(self._preview_label, 1)

        # ── Etiketler ──
        self._tags_row = QHBoxLayout()
        self._tags_row.setContentsMargins(0, 0, 0, 0)
        self._tags_row.setSpacing(4)
        self._tag_labels: list[_ClickableTag] = []
        for _ in range(MAX_TAGS):
            tag = _ClickableTag()
            tag.clicked.connect(self.tag_clicked)
            self._tag_labels.append(tag)
            self._tags_row.addWidget(tag)
        self._tags_row.addStretch()
        layout.addLayout(self._tags_row)

    def bind(self, word: Word) -> None:
        """Kartı verilen kelimeye bağlar (widget'lar yeniden kullanılır)."""
        self._word = word

        self._term_label.setText(word.term)
        self._fav_btn.setProperty("active", str(word.is_favorite).lower())
        repolish(self._fav_btn)

        self._lang_badge.setText(word.language.upper())
        self._status_badge.set_status(word.status.value, word.status.display_name)

        self._pos_badge.setText(word.part_of_speech or "")
        self._pos_badge.setVisible(bool(word.part_of_speech))

        definition = word.definition_short or word.definition
        preview = definition[:PREVIEW_CHARS] + ("…" if len(definition) > PREVIEW_CHARS else "")
        self._preview_label.setText(preview)
        self._preview_label.setVisible(bool(definition))

        for i, label in enumerate(self._tag_labels):
            if i < len(word.tags):
                label.set_tag(word.tags[i])
                label.setVisible(True)
            else:
                label.setVisible(False)

    # Geriye dönük ad.
    update_word = bind

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

    @property
    def word(self) -> Word:
        return self._word


class _ClickableTag(QLabel):
    """Tıklanınca o etikete filtreleyen kart etiketi."""

    clicked = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("cardTag")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._tag = ""

    def set_tag(self, tag: str) -> None:
        self._tag = tag
        self.setText(f"#{tag}")
        self.setToolTip(f"'{tag}' etiketine göre filtrele")

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._tag:
            self.clicked.emit(self._tag)
            event.accept()  # kartın tıklamasını tetikleme
            return
        super().mousePressEvent(event)
