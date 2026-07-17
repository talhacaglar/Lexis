"""
Lexis — Main Window

Ana pencere: sidebar navigasyonu + QStackedWidget içerik alanı.
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from lexis.services.export_service import ExportService
from lexis.services.word_service import WordService
from lexis.ui.animations import fade_in
from lexis.ui.icons import colored_icon
from lexis.ui.theme import Colors
from lexis.ui.views.dashboard_view import DashboardView
from lexis.ui.views.library_view import LibraryView
from lexis.ui.views.practice_view import PracticeView
from lexis.ui.views.settings_view import SettingsView
from lexis.ui.views.word_detail_view import WordDetailView
from lexis.ui.widgets.add_word_dialog import AddWordDialog
from lexis.ui.widgets.common import Divider
from lexis.ui.widgets.toast import ToastManager

logger = logging.getLogger(__name__)

# Page indices
PAGE_DASHBOARD = 0
PAGE_LIBRARY = 1
PAGE_DETAIL = 2
PAGE_SETTINGS = 3
PAGE_PRACTICE = 4


class NavButton(QPushButton):
    """Sidebar navigasyon butonu (tema rengine uyan çizgi ikon)."""

    def __init__(self, icon_name: str, label: str, parent=None) -> None:
        super().__init__(f"   {label}", parent)
        self._icon_name = icon_name
        self.setObjectName("navBtn")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumHeight(42)
        self.setIconSize(QSize(18, 18))
        self.setCheckable(False)
        self._active = False
        self._refresh_icon()

    def _refresh_icon(self) -> None:
        color = Colors.ACCENT_LIGHT if self._active else Colors.TEXT_SECONDARY
        self.setIcon(colored_icon(self._icon_name, color))

    def set_active(self, active: bool) -> None:
        self._active = active
        self.setProperty("active", "true" if active else "false")
        self._refresh_icon()
        self.setStyle(self.style())


class Sidebar(QWidget):
    """Sol sidebar: logo + navigasyon butonları."""

    navigate = pyqtSignal(int)  # page_index

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self._nav_btns: list[tuple[NavButton, int]] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 24)
        layout.setSpacing(4)

        # ── Logo ──
        logo_container = QWidget()
        logo_container.setFixedHeight(80)
        logo_layout = QVBoxLayout(logo_container)
        logo_layout.setContentsMargins(8, 0, 0, 0)
        logo_layout.setSpacing(2)
        logo_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        logo_label = QLabel("Lexis")
        logo_label.setObjectName("appTitle")

        sub_label = QLabel("kişisel sözlüğün")
        sub_label.setObjectName("appTagline")

        logo_layout.addWidget(logo_label)
        logo_layout.addWidget(sub_label)
        layout.addWidget(logo_container)

        # ── Separator ──
        layout.addWidget(Divider(spaced=True))

        # ── Section label ──
        nav_lbl = QLabel("MENÜ")
        nav_lbl.setObjectName("navSectionLabel")
        layout.addWidget(nav_lbl)

        # ── Nav items ──
        nav_items = [
            ("home", "Ana Sayfa", PAGE_DASHBOARD),
            ("book", "Kütüphane", PAGE_LIBRARY),
        ]
        for icon, label, page in nav_items:
            btn = NavButton(icon, label)
            btn.clicked.connect(lambda _, p=page: self.navigate.emit(p))
            self._nav_btns.append((btn, page))
            layout.addWidget(btn)

        layout.addStretch()

        # ── Bottom section ──
        layout.addWidget(Divider(spaced=True))

        settings_btn = NavButton("settings", "Ayarlar")
        settings_btn.clicked.connect(lambda: self.navigate.emit(PAGE_SETTINGS))
        self._nav_btns.append((settings_btn, PAGE_SETTINGS))
        layout.addWidget(settings_btn)

    def set_active_page(self, page: int) -> None:
        for btn, page_idx in self._nav_btns:
            btn.set_active(page_idx == page)


class MainWindow(QWidget):
    """Ana uygulama penceresi."""

    def __init__(
        self,
        word_service: WordService,
        export_service: ExportService,
    ) -> None:
        super().__init__()
        self._service = word_service
        self._export_service = export_service
        self._previous_page: int | None = None
        self.toasts = ToastManager(self)
        self._setup_ui()
        self._setup_connections()
        self._setup_shortcuts()
        self._navigate_to(PAGE_DASHBOARD)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.toasts.reposition()

    def _setup_shortcuts(self) -> None:
        """Uygulama geneli klavye kısayolları."""
        shortcuts = {
            "Ctrl+N": self._open_add_dialog,
            "Ctrl+P": self._start_practice,
            "Ctrl+1": lambda: self._navigate_to(PAGE_DASHBOARD),
            "Ctrl+2": lambda: self._navigate_to(PAGE_LIBRARY),
            "Ctrl+,": lambda: self._navigate_to(PAGE_SETTINGS),
            "Ctrl+F": self._focus_search,
            "/": self._focus_search,
            "Escape": self._escape,
        }
        for key, handler in shortcuts.items():
            QShortcut(QKeySequence(key), self, activated=handler)

    def _focus_search(self) -> None:
        """Kütüphaneye geçip arama alanına odaklanır."""
        self._navigate_to(PAGE_LIBRARY)
        self._library.focus_search()

    def _escape(self) -> None:
        """Detay ve çalışma ekranlarından geri döner."""
        if self._stack.currentIndex() in (PAGE_DETAIL, PAGE_PRACTICE):
            self._go_back()

    def _setup_ui(self) -> None:
        self.setObjectName("root")
        self.setWindowTitle("Lexis — Kişisel Sözlük")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 820)

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Sidebar ──
        self._sidebar = Sidebar()
        root_layout.addWidget(self._sidebar)

        # ── Content Stack ──
        self._stack = QStackedWidget()
        self._stack.setObjectName("contentArea")
        root_layout.addWidget(self._stack, 1)

        # Create views
        self._dashboard = DashboardView(self._service)
        self._library = LibraryView(self._service)
        self._detail = WordDetailView(self._service)
        self._settings = SettingsView(self._service, self._export_service)
        self._practice = PracticeView(self._service)

        self._stack.addWidget(self._dashboard)  # 0
        self._stack.addWidget(self._library)  # 1
        self._stack.addWidget(self._detail)  # 2
        self._stack.addWidget(self._settings)  # 3
        self._stack.addWidget(self._practice)  # 4

    def _setup_connections(self) -> None:
        # Sidebar navigation
        self._sidebar.navigate.connect(self._navigate_to)

        # Dashboard
        self._dashboard.open_add_dialog.connect(self._open_add_dialog)
        self._dashboard.word_clicked.connect(self._show_word_detail)
        self._dashboard.favorite_toggled.connect(self._toggle_favorite)
        self._dashboard.delete_requested.connect(self._delete_word)

        # Library
        self._library.open_add_dialog.connect(self._open_add_dialog)
        self._library.word_clicked.connect(self._show_word_detail)
        self._library.favorite_toggled.connect(self._toggle_favorite)
        self._library.delete_requested.connect(self._delete_word)

        # Detail
        self._detail.back_requested.connect(self._go_back)
        self._detail.delete_requested.connect(self._delete_word)
        self._detail.word_updated.connect(self._on_word_changed)

        # Settings
        self._settings.settings_changed.connect(self._on_word_changed)

        # Practice
        self._dashboard.start_practice.connect(self._start_practice)
        self._practice.back_requested.connect(self._go_back)
        self._practice.session_finished.connect(self._on_word_changed)

        # Görünümlerden gelen hatalar kullanıcıya toast olarak gösterilir.
        self._detail.error_occurred.connect(self.toasts.error)
        self._practice.error_occurred.connect(self.toasts.error)

    def current_page(self) -> int:
        """Şu an görüntülenen sayfanın indeksi (tema yeniden uygulanırken korunur)."""
        return self._stack.currentIndex()

    def navigate_to(self, page: int) -> None:
        """Belirtilen sayfaya geçer (genel API)."""
        self._navigate_to(page)

    def _navigate_to(self, page: int) -> None:
        current = self._stack.currentIndex()
        if current != PAGE_DETAIL:
            self._previous_page = current

        page_changed = current != page
        self._stack.setCurrentIndex(page)
        self._sidebar.set_active_page(page)

        # Ekrana her dönüşte güncel veriyi göster.
        if page == PAGE_DASHBOARD:
            self._dashboard.refresh()
        elif page == PAGE_LIBRARY:
            self._library.refresh()
        elif page == PAGE_SETTINGS:
            self._settings.refresh()

        # Tazelemeden sonra: içerik yerine oturmuş hâliyle belirsin.
        # Aynı sayfaya tekrar gidildiğinde (ör. Ctrl+F ile kütüphaneye odak)
        # ekranın boşuna yanıp sönmesi engellenir.
        if page_changed:
            fade_in(self._stack.currentWidget())

    def _open_add_dialog(self) -> None:
        dialog = AddWordDialog(self._service, parent=self)
        dialog.word_added.connect(self._on_word_added)
        dialog.exec()

    def _on_word_added(self, word_id: str) -> None:
        self._dashboard.refresh()
        self._library.refresh()

    def _show_word_detail(self, word_id: str) -> None:
        self._previous_page = self._stack.currentIndex()
        self._detail.load_word(word_id)
        self._stack.setCurrentIndex(PAGE_DETAIL)
        self._sidebar.set_active_page(PAGE_DETAIL)

    def _start_practice(self) -> None:
        self._previous_page = self._stack.currentIndex()
        self._stack.setCurrentIndex(PAGE_PRACTICE)
        self._sidebar.set_active_page(PAGE_PRACTICE)
        self._practice.start_session()

    def _toggle_favorite(self, word_id: str) -> None:
        try:
            self._service.toggle_favorite(word_id)
            self._dashboard.refresh()
            self._library.refresh()
        except Exception:
            logger.exception("Favori durumu değiştirilemedi: %s", word_id)
            self.toasts.error("Favori durumu değiştirilemedi.")

    def _delete_word(self, word_id: str) -> None:
        """
        Kelimeyi onay alarak siler ve geri alma imkânı sunar.

        Üç ekran (dashboard, kütüphane, detay) da buraya bağlanır; silme mantığı
        ve geri alma tek yerde durur.
        """
        try:
            word = self._service.get_by_id(word_id)
        except Exception:
            logger.exception("Silinecek kelime okunamadı: %s", word_id)
            self.toasts.error("Kelime bulunamadı.")
            return

        reply = QMessageBox.question(
            self,
            "Kelimeyi Sil",
            f"'{word.term}' kelimesini silmek istediğinizden emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            self._service.delete_word(word_id)
        except Exception:
            logger.exception("Kelime silinemedi: %s", word_id)
            self.toasts.error("Kelime silinemedi.")
            return

        if self._stack.currentIndex() == PAGE_DETAIL:
            self._go_back()
        self._on_word_changed()

        # Silinen kelime bellekte tutulur; "Geri al" aynı id ile geri yazar.
        self.toasts.show(
            f"'{word.term}' silindi.",
            action_label="Geri al",
            on_action=lambda: self._restore_word(word),
            duration_ms=8000,
        )

    def _restore_word(self, word) -> None:
        try:
            self._service.restore_word(word)
            self._on_word_changed()
            self.toasts.success(f"'{word.term}' geri yüklendi.")
        except Exception:
            logger.exception("Kelime geri yüklenemedi: %s", word.id)
            self.toasts.error("Kelime geri yüklenemedi.")

    def _go_back(self) -> None:
        target = self._previous_page if self._previous_page is not None else PAGE_DASHBOARD
        self._navigate_to(target)

    def _on_word_changed(self, _: str = "") -> None:
        self._dashboard.refresh()
        self._library.refresh()
