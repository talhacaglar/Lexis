"""
Lexis — View: Dashboard

Ana ekran. İstatistikler, hızlı kelime ekleme ve son eklenenler.
"""

from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from lexis.domain.models import Word, WordStats
from lexis.services.word_service import WordService
from lexis.ui.theme import Colors
from lexis.ui.widgets.word_card import WordCard


class StatCard(QFrame):
    """İstatistik kartı."""

    def __init__(
        self,
        value: str,
        label: str,
        accent_color: str = Colors.ACCENT,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setFixedHeight(90)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        val_label = QLabel(value)
        val_label.setStyleSheet(f"""
            color: {accent_color};
            font-size: 28px;
            font-weight: 700;
        """)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"""
            color: {Colors.TEXT_MUTED};
            font-size: 11px;
            font-weight: 500;
            letter-spacing: 0.5px;
        """)

        layout.addWidget(val_label)
        layout.addWidget(lbl)


class DashboardView(QWidget):
    """
    Ana ekran.
    - Karşılama başlığı
    - İstatistik çubukları
    - Hızlı kelime ekleme butonu
    - Son eklenen kelimeler ızgarası
    """

    open_add_dialog = pyqtSignal()
    word_clicked = pyqtSignal(str)     # word_id
    favorite_toggled = pyqtSignal(str) # word_id

    def __init__(self, word_service: WordService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = word_service
        self._word_cards: list[WordCard] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(36, 32, 36, 32)
        layout.setSpacing(32)

        # ── Header ──
        header_row = QHBoxLayout()
        header_row.setSpacing(0)

        header_col = QVBoxLayout()
        header_col.setSpacing(4)

        today = datetime.now()
        greeting = self._get_greeting()

        self._greeting_label = QLabel(greeting)
        self._greeting_label.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-size: 26px;
            font-weight: 700;
        """)

        self._date_label = QLabel(today.strftime("%d %B %Y, %A"))
        self._date_label.setStyleSheet(f"""
            color: {Colors.TEXT_MUTED};
            font-size: 13px;
        """)

        header_col.addWidget(self._greeting_label)
        header_col.addWidget(self._date_label)
        header_row.addLayout(header_col, 1)

        add_btn = QPushButton("+ Kelime Ekle")
        add_btn.setObjectName("primaryBtn")
        add_btn.setMinimumHeight(42)
        add_btn.setMinimumWidth(140)
        add_btn.clicked.connect(self.open_add_dialog)
        header_row.addWidget(add_btn, 0)

        layout.addLayout(header_row)

        # ── Stats Row ──
        self._stats_container = QWidget()
        self._stats_layout = QHBoxLayout(self._stats_container)
        self._stats_layout.setContentsMargins(0, 0, 0, 0)
        self._stats_layout.setSpacing(12)
        layout.addWidget(self._stats_container)

        # ── Recent Words Section ──
        recent_header = QHBoxLayout()
        recent_label = QLabel("SON EKLENENLER")
        recent_label.setObjectName("sectionTitle")
        recent_label.setStyleSheet(f"""
            color: {Colors.TEXT_MUTED};
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.2px;
        """)
        recent_header.addWidget(recent_label, 1)
        layout.addLayout(recent_header)

        # Word cards grid
        self._grid_widget = QWidget()
        self._grid_layout = QGridLayout(self._grid_widget)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setSpacing(14)
        layout.addWidget(self._grid_widget)

        self._empty_label = QLabel("Henüz kelime eklenmemiş.\nİlk kelimenizi eklemek için yukarıdaki butona tıklayın.")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(f"""
            color: {Colors.TEXT_MUTED};
            font-size: 14px;
            line-height: 1.8;
            padding: 60px 0;
        """)
        self._empty_label.setVisible(False)
        layout.addWidget(self._empty_label)

        layout.addStretch()

        scroll.setWidget(container)
        root.addWidget(scroll)

    def _get_greeting(self) -> str:
        hour = datetime.now().hour
        if hour < 12:
            return "Günaydın 👋"
        elif hour < 18:
            return "İyi günler 👋"
        else:
            return "İyi akşamlar 👋"

    def refresh(self) -> None:
        """Veritabanından güncel veriyi yükler ve görünümü günceller."""
        stats = self._service.get_stats()
        self._refresh_stats(stats)
        words = self._service.get_recent(limit=12)
        self._refresh_words(words)

    def _refresh_stats(self, stats: WordStats) -> None:
        # Eski stat kartlarını temizle
        while self._stats_layout.count():
            item = self._stats_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cards = [
            (str(stats.total), "Toplam Kelime", Colors.ACCENT_LIGHT),
            (str(stats.learning), "Öğreniyorum", Colors.WARNING),
            (str(stats.learned), "Öğrendim", Colors.SUCCESS),
            (str(stats.added_today), "Bugün Eklendi", Colors.INFO),
            (str(stats.favorites), "Favori", Colors.FAVORITE),
        ]
        for val, lbl, color in cards:
            card = StatCard(val, lbl, color)
            self._stats_layout.addWidget(card)

    def _refresh_words(self, words: list[Word]) -> None:
        # Eski kartları temizle
        for card in self._word_cards:
            card.deleteLater()
        self._word_cards.clear()

        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not words:
            self._empty_label.setVisible(True)
            self._grid_widget.setVisible(False)
            return

        self._empty_label.setVisible(False)
        self._grid_widget.setVisible(True)

        cols = 3
        for i, word in enumerate(words):
            card = WordCard(word)
            card.clicked.connect(self.word_clicked)
            card.favorite_toggled.connect(self.favorite_toggled)
            self._word_cards.append(card)
            self._grid_layout.addWidget(card, i // cols, i % cols)
