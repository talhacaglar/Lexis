"""
Lexis — View: Library

Tüm kelimelerin arama ve filtreleme destekli listesi.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from lexis.domain.models import Word, WordStatus
from lexis.domain.models import SUPPORTED_LANGUAGES
from lexis.services.word_service import WordService
from lexis.ui.theme import Colors
from lexis.ui.widgets.word_card import WordCard


class LibraryView(QWidget):
    """
    Kelime kütüphanesi.
    - Gerçek zamanlı arama
    - Durum ve dil filtresi
    - Favori filtresi
    - 3 sütun ızgara
    """

    word_clicked = pyqtSignal(str)       # word_id
    favorite_toggled = pyqtSignal(str)   # word_id
    open_add_dialog = pyqtSignal()

    def __init__(self, word_service: WordService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = word_service
        self._word_cards: list[WordCard] = []
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)
        self._search_timer.timeout.connect(self._apply_filters)
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top Bar ──
        topbar = QWidget()
        topbar.setFixedHeight(72)
        topbar.setStyleSheet(f"background: {Colors.BG_BASE};")
        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(36, 0, 36, 0)
        topbar_layout.setSpacing(12)

        # Page title
        title = QLabel("Kütüphane")
        title.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-size: 22px;
            font-weight: 700;
        """)
        topbar_layout.addWidget(title)
        topbar_layout.addStretch()

        add_btn = QPushButton("+ Kelime Ekle")
        add_btn.setObjectName("primaryBtn")
        add_btn.setMinimumHeight(38)
        add_btn.clicked.connect(self.open_add_dialog)
        topbar_layout.addWidget(add_btn)

        root.addWidget(topbar)

        # ── Search + Filter Bar ──
        filter_bar = QWidget()
        filter_bar.setStyleSheet(f"""
            background: {Colors.BG_SURFACE};
            border-bottom: 1px solid {Colors.BORDER_SUBTLE};
        """)
        filter_layout = QVBoxLayout(filter_bar)
        filter_layout.setContentsMargins(36, 14, 36, 14)
        filter_layout.setSpacing(12)

        # Search row
        search_row = QHBoxLayout()
        search_row.setSpacing(10)

        search_container = QWidget()
        search_container.setStyleSheet(f"""
            background: {Colors.BG_ELEVATED};
            border: 1px solid {Colors.BORDER};
            border-radius: 10px;
        """)
        search_inner = QHBoxLayout(search_container)
        search_inner.setContentsMargins(14, 0, 14, 0)
        search_inner.setSpacing(8)

        search_icon = QLabel("⌕")
        search_icon.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 16px; background: transparent;")
        search_inner.addWidget(search_icon)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Kelime veya tanım ara...")
        self._search_input.setStyleSheet(f"""
            background: transparent;
            border: none;
            color: {Colors.TEXT_PRIMARY};
            font-size: 14px;
            padding: 9px 0;
        """)
        self._search_input.textChanged.connect(self._on_search_changed)
        search_inner.addWidget(self._search_input, 1)

        search_row.addWidget(search_container, 1)

        # Language filter
        self._lang_combo = QComboBox()
        self._lang_combo.addItem("Tüm Diller", "")
        for code, name in SUPPORTED_LANGUAGES.items():
            self._lang_combo.addItem(name, code)
        self._lang_combo.setMinimumHeight(40)
        self._lang_combo.currentIndexChanged.connect(self._apply_filters)
        search_row.addWidget(self._lang_combo)

        # Sort
        self._sort_combo = QComboBox()
        self._sort_combo.addItem("Son Eklenen", "created_at")
        self._sort_combo.addItem("Alfabetik", "term")
        self._sort_combo.addItem("Son Çalışılan", "updated_at")
        self._sort_combo.setMinimumHeight(40)
        self._sort_combo.currentIndexChanged.connect(self._apply_filters)
        search_row.addWidget(self._sort_combo)

        filter_layout.addLayout(search_row)

        # Filter chips row
        chips_row = QHBoxLayout()
        chips_row.setSpacing(8)

        self._filter_chips: dict[str, QPushButton] = {}
        chip_defs = [
            ("all", "Tümü"),
            ("new", "Yeni"),
            ("learning", "Öğreniyorum"),
            ("learned", "Öğrendim"),
            ("needs_review", "Tekrar Gerek"),
            ("favorites", "❤ Favoriler"),
        ]
        for key, label in chip_defs:
            btn = QPushButton(label)
            btn.setObjectName("filterChip")
            btn.setCheckable(False)
            btn.setProperty("active", "true" if key == "all" else "false")
            btn.clicked.connect(lambda _, k=key: self._set_active_filter(k))
            self._filter_chips[key] = btn
            chips_row.addWidget(btn)

        chips_row.addStretch()

        self._count_label = QLabel("")
        self._count_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px;")
        chips_row.addWidget(self._count_label)

        filter_layout.addLayout(chips_row)

        root.addWidget(filter_bar)

        # ── Word Grid (Scrollable) ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._grid_container = QWidget()
        self._grid_layout = QGridLayout(self._grid_container)
        self._grid_layout.setContentsMargins(36, 24, 36, 36)
        self._grid_layout.setSpacing(14)
        self._grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._empty_label = QLabel("Arama sonucu bulunamadı.")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(f"""
            color: {Colors.TEXT_MUTED};
            font-size: 14px;
            padding: 60px 0;
        """)
        self._empty_label.setVisible(False)

        scroll_content = QWidget()
        sc_layout = QVBoxLayout(scroll_content)
        sc_layout.setContentsMargins(0, 0, 0, 0)
        sc_layout.setSpacing(0)
        sc_layout.addWidget(self._grid_container)
        sc_layout.addWidget(self._empty_label)
        sc_layout.addStretch()

        self._scroll.setWidget(scroll_content)
        root.addWidget(self._scroll, 1)

        self._active_filter = "all"

    def _set_active_filter(self, key: str) -> None:
        self._active_filter = key
        for k, btn in self._filter_chips.items():
            btn.setProperty("active", "true" if k == key else "false")
            btn.setStyle(btn.style())
        self._apply_filters()

    def _on_search_changed(self, _: str) -> None:
        self._search_timer.start()

    def _apply_filters(self) -> None:
        search = self._search_input.text().strip()
        language = self._lang_combo.currentData() or ""
        sort_by = self._sort_combo.currentData() or "created_at"

        status = None
        favorites_only = False

        if self._active_filter == "favorites":
            favorites_only = True
        elif self._active_filter in ("new", "learning", "learned", "needs_review"):
            status = WordStatus(self._active_filter)

        words = self._service.get_all(
            search=search,
            language=language,
            status=status,
            favorites_only=favorites_only,
            sort_by=sort_by,
            sort_desc=True,
        )
        self._render_words(words)

    def _render_words(self, words: list[Word]) -> None:
        for card in self._word_cards:
            card.deleteLater()
        self._word_cards.clear()

        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        count = len(words)
        self._count_label.setText(f"{count} kelime")

        if not words:
            self._empty_label.setVisible(True)
            self._grid_container.setVisible(False)
            return

        self._empty_label.setVisible(False)
        self._grid_container.setVisible(True)

        cols = 3
        for i, word in enumerate(words):
            card = WordCard(word)
            card.clicked.connect(self.word_clicked)
            card.favorite_toggled.connect(self.favorite_toggled)
            self._word_cards.append(card)
            self._grid_layout.addWidget(card, i // cols, i % cols)

    def refresh(self) -> None:
        self._apply_filters()
