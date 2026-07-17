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
    QVBoxLayout,
    QWidget,
)

from lexis.domain.models import SUPPORTED_LANGUAGES, Word, WordStatus
from lexis.services.word_service import WordService
from lexis.ui.theme import repolish
from lexis.ui.widgets.word_card import WordCard, grid_columns

# Sayfa başına kelime; kütüphane büyüdüğünde tüm tablo belleğe çekilmesin.
PAGE_SIZE = 60


class LibraryView(QWidget):
    """
    Kelime kütüphanesi.
    - Gerçek zamanlı arama
    - Durum, dil ve etiket filtresi
    - Favori filtresi
    - Pencere genişliğine uyan ızgara ve sayfalama
    """

    word_clicked = pyqtSignal(str)  # word_id
    favorite_toggled = pyqtSignal(str)  # word_id
    delete_requested = pyqtSignal(str)  # word_id — silmeyi MainWindow yürütür
    open_add_dialog = pyqtSignal()

    def __init__(self, word_service: WordService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = word_service
        # Kartlar yeniden kullanılır; _word_cards_used o an görünen sayıdır.
        self._word_cards: list[WordCard] = []
        self._word_cards_used = 0
        self._loaded = 0
        self._last_columns = 0
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)
        self._search_timer.timeout.connect(self._apply_filters)
        self._setup_ui()
        self._refresh_tag_filter()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top Bar ──
        topbar = QWidget()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(72)
        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(36, 0, 36, 0)
        topbar_layout.setSpacing(12)

        # Page title
        title = QLabel("Kütüphane")
        title.setObjectName("pageTitle")
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
        filter_bar.setObjectName("filterBar")
        filter_layout = QVBoxLayout(filter_bar)
        filter_layout.setContentsMargins(36, 14, 36, 14)
        filter_layout.setSpacing(12)

        # Search row
        search_row = QHBoxLayout()
        search_row.setSpacing(10)

        search_container = QWidget()
        search_container.setObjectName("searchContainer")
        search_inner = QHBoxLayout(search_container)
        search_inner.setContentsMargins(14, 0, 14, 0)
        search_inner.setSpacing(8)

        search_icon = QLabel("⌕")
        search_icon.setObjectName("searchIcon")
        search_inner.addWidget(search_icon)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Kelime veya tanım ara...")
        self._search_input.setObjectName("searchField")
        self._search_input.setAccessibleName("Kelime ara")
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

        # Etiket filtresi — servis bunu zaten destekliyordu ama UI'da yoktu.
        self._tag_combo = QComboBox()
        self._tag_combo.setMinimumHeight(40)
        self._tag_combo.setAccessibleName("Etikete göre filtrele")
        self._tag_combo.currentIndexChanged.connect(self._apply_filters)
        search_row.addWidget(self._tag_combo)

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
        self._count_label.setObjectName("countLabel")
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

        # Boş durum: "hiç kelime yok" ile "filtre eşleşmedi" ayrı ele alınır;
        # ilkinde kullanıcıya ekleme, ikincisinde filtreyi temizleme sunulur.
        self._empty_widget = QWidget()
        empty_layout = QVBoxLayout(self._empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(16)

        self._empty_label = QLabel("")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setObjectName("emptyState")
        empty_layout.addWidget(self._empty_label)

        self._empty_action_btn = QPushButton("")
        self._empty_action_btn.setObjectName("primaryBtn")
        self._empty_action_btn.setMinimumHeight(40)
        self._empty_action_btn.setMaximumWidth(220)
        empty_layout.addWidget(self._empty_action_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self._empty_widget.setVisible(False)

        # "Daha fazla yükle": kütüphane büyüdüğünde tüm tabloyu belleğe çekip
        # her kelime için widget kurmamak için sayfalama.
        self._load_more_btn = QPushButton("")
        self._load_more_btn.setObjectName("secondaryBtn")
        self._load_more_btn.setMinimumHeight(40)
        self._load_more_btn.setVisible(False)
        self._load_more_btn.clicked.connect(self._load_next_page)

        scroll_content = QWidget()
        sc_layout = QVBoxLayout(scroll_content)
        sc_layout.setContentsMargins(0, 0, 0, 0)
        sc_layout.setSpacing(0)
        sc_layout.addWidget(self._grid_container)
        sc_layout.addWidget(self._empty_widget)
        sc_layout.addWidget(self._load_more_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        sc_layout.addStretch()

        self._scroll.setWidget(scroll_content)
        root.addWidget(self._scroll, 1)

        self._active_filter = "all"

    def _set_active_filter(self, key: str) -> None:
        self._active_filter = key
        for k, btn in self._filter_chips.items():
            btn.setProperty("active", "true" if k == key else "false")
            repolish(btn)
        self._apply_filters()

    def _on_search_changed(self, _: str) -> None:
        self._search_timer.start()

    def focus_search(self) -> None:
        """Arama alanına odaklanır (Ctrl+F / '/')."""
        self._search_input.setFocus()
        self._search_input.selectAll()

    def _clear_filters(self) -> None:
        self._search_input.clear()
        self._lang_combo.setCurrentIndex(0)
        self._tag_combo.setCurrentIndex(0)
        self._set_active_filter("all")

    def filter_by_tag(self, tag: str) -> None:
        """Karttaki etikete tıklanınca o etikete filtreler."""
        index = self._tag_combo.findData(tag)
        if index >= 0:
            self._tag_combo.setCurrentIndex(index)

    def _current_filters(self) -> dict:
        """Aktif filtreleri servis çağrısı için toplar."""
        status = None
        favorites_only = False
        if self._active_filter == "favorites":
            favorites_only = True
        elif self._active_filter in ("new", "learning", "learned", "needs_review"):
            status = WordStatus(self._active_filter)

        return {
            "search": self._search_input.text().strip(),
            "language": self._lang_combo.currentData() or "",
            "tag": self._tag_combo.currentData() or "",
            "status": status,
            "favorites_only": favorites_only,
        }

    def _apply_filters(self) -> None:
        """Filtreleri baştan uygular (ilk sayfa)."""
        self._loaded = 0
        self._word_cards_used = 0
        self._apply_filters_page()

    def _load_next_page(self) -> None:
        self._apply_filters_page()

    def _apply_filters_page(self) -> None:
        filters = self._current_filters()
        sort_by = self._sort_combo.currentData() or "created_at"

        total = self._service.count(**filters)
        words = self._service.get_all(
            **filters,
            sort_by=sort_by,
            sort_desc=True,
            limit=PAGE_SIZE,
            offset=self._loaded,
        )
        self._loaded += len(words)
        self._render_page(words, total, filters)

    def _render_page(self, words: list[Word], total: int, filters: dict) -> None:
        for word in words:
            self._add_or_update_card(word)

        # Sayfa küçüldüyse fazlalık kartlar gizlenir (yok edilmez: yeniden
        # kullanılırlar; her tuş vuruşunda widget yaratmak pahalıydı).
        for card in self._word_cards[self._word_cards_used :]:
            card.setVisible(False)

        self._count_label.setText(
            f"{self._loaded} / {total} kelime" if self._loaded < total else f"{total} kelime"
        )
        self._relayout_grid()

        has_results = total > 0
        self._grid_container.setVisible(has_results)
        self._load_more_btn.setVisible(self._loaded < total)
        if self._loaded < total:
            self._load_more_btn.setText(f"Daha fazla yükle ({total - self._loaded})")

        if has_results:
            self._empty_widget.setVisible(False)
        else:
            self._show_empty_state(filters)

    def _add_or_update_card(self, word: Word) -> None:
        """Havuzdan kart alır; yoksa yenisini oluşturur."""
        if self._word_cards_used < len(self._word_cards):
            card = self._word_cards[self._word_cards_used]
            card.bind(word)
            card.setVisible(True)
        else:
            card = WordCard(word)
            card.clicked.connect(self.word_clicked)
            card.favorite_toggled.connect(self.favorite_toggled)
            card.delete_requested.connect(self.delete_requested)
            card.tag_clicked.connect(self.filter_by_tag)
            self._word_cards.append(card)
        self._word_cards_used += 1

    def _show_empty_state(self, filters: dict) -> None:
        """Kütüphane gerçekten boş mu, yoksa filtre mi eşleşmedi — ayırt eder."""
        self._empty_widget.setVisible(True)
        filtering = bool(
            filters["search"]
            or filters["language"]
            or filters["tag"]
            or filters["status"]
            or filters["favorites_only"]
        )

        if filtering:
            self._empty_label.setText(
                "Bu filtrelere uyan kelime yok.\nFiltreleri değiştirmeyi deneyin."
            )
            self._empty_action_btn.setText("Filtreleri Temizle")
            self._reconnect(self._empty_action_btn, self._clear_filters)
        else:
            self._empty_label.setText("Kütüphaneniz henüz boş.\nİlk kelimenizi ekleyerek başlayın.")
            self._empty_action_btn.setText("+ İlk Kelimeni Ekle")
            self._reconnect(self._empty_action_btn, self.open_add_dialog.emit)

    @staticmethod
    def _reconnect(button: QPushButton, handler) -> None:
        """Butonun tek bir aksiyona bağlı kalmasını sağlar."""
        try:
            button.clicked.disconnect()
        except TypeError:
            pass  # bağlı değildi
        button.clicked.connect(handler)

    def _columns(self) -> int:
        """Sütun sayısını viewport genişliğinden hesaplar."""
        return grid_columns(self._scroll.viewport().width())

    def _relayout_grid(self) -> None:
        # Önce ızgarayı boşalt: aynı widget'ı yeni hücreye eklemek eskisini
        # bırakmadığı için satırlar üst üste biniyordu. takeAt widget'ı yok
        # etmez, havuzda kalır.
        while self._grid_layout.count():
            self._grid_layout.takeAt(0)

        cols = self._columns()
        for i, card in enumerate(self._word_cards[: self._word_cards_used]):
            self._grid_layout.addWidget(card, i // cols, i % cols)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Sütun sayısı değiştiyse ızgarayı yeniden diz (sabit 3 sütun,
        # dar pencerede kartları eziyordu).
        if self._word_cards_used and self._columns() != self._last_columns:
            self._last_columns = self._columns()
            self._relayout_grid()

    def _refresh_tag_filter(self) -> None:
        """Etiket listesini korunarak tazeler (seçili etiket kaybolmasın)."""
        current = self._tag_combo.currentData()
        self._tag_combo.blockSignals(True)
        self._tag_combo.clear()
        self._tag_combo.addItem("Tüm Etiketler", "")
        for tag in self._service.get_all_tags():
            self._tag_combo.addItem(f"#{tag}", tag)
        index = self._tag_combo.findData(current)
        self._tag_combo.setCurrentIndex(max(0, index))
        self._tag_combo.blockSignals(False)

    def refresh(self) -> None:
        self._refresh_tag_filter()
        self._apply_filters()
