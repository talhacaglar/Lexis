"""
Lexis — View: Dashboard

Ana ekran. İstatistikler, hızlı kelime ekleme ve son eklenenler.
"""

from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import QDate, QLocale, QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from lexis.domain.models import Word, WordStats
from lexis.services.word_service import WordService
from lexis.ui.icons import colored_icon
from lexis.ui.theme import Colors
from lexis.ui.widgets.activity_chart import ActivityChart
from lexis.ui.widgets.common import SectionLabel
from lexis.ui.widgets.word_card import WordCard, grid_columns

ACTIVITY_DAYS = 7

_TR_LOCALE = QLocale(QLocale.Language.Turkish, QLocale.Country.Turkey)


def _format_date_tr(when: datetime) -> str:
    """
    Tarihi Türkçe biçimler (ör. "17 Temmuz 2026, Cuma").

    strftime sistem yereline bağlı olduğundan Türkçe arayüzde "July"/"Friday"
    basabiliyordu; QLocale dilden bağımsız olarak Türkçe verir.
    """
    return _TR_LOCALE.toString(QDate(when.year, when.month, when.day), "d MMMM yyyy, dddd")


class StatCard(QFrame):
    """
    İstatistik kartı.

    tone, değerin vurgu rengini seçer; renkler QSS'teki
    #statValue[tone="..."] kurallarından gelir.
    """

    def __init__(
        self,
        value: str,
        label: str,
        tone: str = "accent",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setFixedHeight(90)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        val_label = QLabel(value)
        val_label.setObjectName("statValue")
        val_label.setProperty("tone", tone)

        lbl = QLabel(label)
        lbl.setObjectName("statLabel")

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
    word_clicked = pyqtSignal(str)      # word_id
    favorite_toggled = pyqtSignal(str)  # word_id
    delete_requested = pyqtSignal(str)  # word_id — silmeyi MainWindow yürütür
    start_practice = pyqtSignal()

    def __init__(self, word_service: WordService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = word_service
        self._word_cards: list[WordCard] = []
        self._streak = 0
        self._last_columns = 0
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
        self._greeting_label.setObjectName("greeting")

        self._date_label = QLabel(_format_date_tr(today))
        self._date_label.setObjectName("dateLabel")

        header_col.addWidget(self._greeting_label)
        header_col.addWidget(self._date_label)
        header_row.addLayout(header_col, 1)

        self._practice_btn = QPushButton("  Çalış")
        self._practice_btn.setObjectName("secondaryBtn")
        self._practice_btn.setIcon(colored_icon("cards", Colors.TEXT_SECONDARY, 16))
        self._practice_btn.setIconSize(QSize(16, 16))
        self._practice_btn.setMinimumHeight(42)
        self._practice_btn.setMinimumWidth(120)
        self._practice_btn.clicked.connect(self.start_practice)
        header_row.addWidget(self._practice_btn, 0)

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

        # ── Aktivite Grafiği ──
        activity_card = QFrame()
        activity_card.setObjectName("card")
        activity_layout = QVBoxLayout(activity_card)
        activity_layout.setContentsMargins(18, 16, 18, 12)
        activity_layout.setSpacing(10)

        activity_header = QHBoxLayout()
        activity_header.addWidget(SectionLabel("SON 7 GÜN"), 1)
        self._activity_summary = QLabel("")
        self._activity_summary.setObjectName("mutedText")
        activity_header.addWidget(self._activity_summary)
        activity_layout.addLayout(activity_header)

        self._activity_chart = ActivityChart()
        activity_layout.addWidget(self._activity_chart)
        layout.addWidget(activity_card)

        # ── Recent Words Section ──
        recent_header = QHBoxLayout()
        recent_label = SectionLabel("SON EKLENENLER")
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
        self._empty_label.setObjectName("emptyState")
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
        self._streak = self._service.get_streak()
        self._refresh_stats(stats)
        self._refresh_activity()
        words = self._service.get_recent(limit=12)
        self._refresh_words(words)

    def _refresh_activity(self) -> None:
        counts = self._service.get_review_counts(days=ACTIVITY_DAYS)
        self._activity_chart.set_counts(counts)

        total = sum(counts.values())
        self._activity_summary.setText(
            f"{total} tekrar" if total else "Bu hafta henüz çalışılmadı"
        )

    def _refresh_stats(self, stats: WordStats) -> None:
        # Çalış butonu, çalışma kuyruğunun tamamını sayar: planlı tekrarlar +
        # hiç çalışılmamış kelimeler (get_due_words da ikisini birden döndürür).
        queue = stats.practice_queue_size
        if queue > 0:
            self._practice_btn.setText(f"  Çalış ({queue})")
            self._practice_btn.setEnabled(True)
        else:
            self._practice_btn.setText("  Çalış")
            self._practice_btn.setEnabled(stats.total > 0)

        # Eski stat kartlarını temizle
        while self._stats_layout.count():
            item = self._stats_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cards = [
            (str(stats.total), "Toplam Kelime", "accent"),
            (str(stats.practice_queue_size), "Bugün Tekrar", "review"),
            (f"🔥 {self._streak}" if self._streak else "0", "Günlük Seri", "streak"),
            (str(stats.learning), "Öğreniyorum", "warning"),
            (str(stats.learned), "Öğrendim", "success"),
            (str(stats.favorites), "Favori", "favorite"),
        ]
        for val, lbl, tone in cards:
            self._stats_layout.addWidget(StatCard(val, lbl, tone))

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

        for word in words:
            card = WordCard(word)
            card.clicked.connect(self.word_clicked)
            card.favorite_toggled.connect(self.favorite_toggled)
            card.delete_requested.connect(self.delete_requested)
            self._word_cards.append(card)
        self._relayout_grid()

    def _columns(self) -> int:
        """Sütun sayısını mevcut genişlikten hesaplar (sabit 3 değil)."""
        return grid_columns(self.width())

    def _relayout_grid(self) -> None:
        # Kartlar önce ızgaradan çıkarılır: aynı widget'ı yeni bir hücreye
        # eklemek eski hücreyi boşaltmadığı için satırlar üst üste biniyordu.
        # takeAt yalnızca yerleşimden çıkarır, widget'ları yok etmez.
        while self._grid_layout.count():
            self._grid_layout.takeAt(0)

        cols = self._columns()
        for i, card in enumerate(self._word_cards):
            self._grid_layout.addWidget(card, i // cols, i % cols)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._word_cards and self._columns() != self._last_columns:
            self._last_columns = self._columns()
            self._relayout_grid()

