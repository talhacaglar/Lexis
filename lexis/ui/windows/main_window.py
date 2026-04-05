"""
Lexis — Main Window

Ana pencere: sidebar navigasyonu + QStackedWidget içerik alanı.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from lexis.services.export_service import ExportService
from lexis.services.word_service import WordService
from lexis.ui.theme import Colors
from lexis.ui.views.dashboard_view import DashboardView
from lexis.ui.views.library_view import LibraryView
from lexis.ui.views.settings_view import SettingsView
from lexis.ui.views.word_detail_view import WordDetailView
from lexis.ui.widgets.add_word_dialog import AddWordDialog


# Page indices
PAGE_DASHBOARD = 0
PAGE_LIBRARY   = 1
PAGE_DETAIL    = 2
PAGE_SETTINGS  = 3


class NavButton(QPushButton):
    """Sidebar navigasyon butonu."""

    def __init__(self, icon: str, label: str, parent=None) -> None:
        super().__init__(f"  {icon}   {label}", parent)
        self.setObjectName("navBtn")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumHeight(42)
        self.setCheckable(False)
        self._active = False

    def set_active(self, active: bool) -> None:
        self._active = active
        self.setProperty("active", "true" if active else "false")
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
        logo_label.setStyleSheet(f"""
            color: {Colors.ACCENT_LIGHT};
            font-size: 22px;
            font-weight: 800;
            letter-spacing: 0.5px;
        """)

        sub_label = QLabel("kişisel sözlüğün")
        sub_label.setStyleSheet(f"""
            color: {Colors.TEXT_MUTED};
            font-size: 10px;
            font-weight: 500;
            letter-spacing: 0.5px;
        """)

        logo_layout.addWidget(logo_label)
        logo_layout.addWidget(sub_label)
        layout.addWidget(logo_container)

        # ── Separator ──
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {Colors.BORDER_SUBTLE}; max-height: 1px; margin-bottom: 8px;")
        layout.addWidget(sep)

        # ── Section label ──
        nav_lbl = QLabel("MENÜ")
        nav_lbl.setStyleSheet(f"""
            color: {Colors.TEXT_MUTED};
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 1.5px;
            padding: 8px 8px 4px 8px;
        """)
        layout.addWidget(nav_lbl)

        # ── Nav items ──
        nav_items = [
            ("🏠", "Ana Sayfa",    PAGE_DASHBOARD),
            ("📚", "Kütüphane",    PAGE_LIBRARY),
        ]
        for icon, label, page in nav_items:
            btn = NavButton(icon, label)
            btn.clicked.connect(lambda _, p=page: self.navigate.emit(p))
            self._nav_btns.append((btn, page))
            layout.addWidget(btn)

        layout.addStretch()

        # ── Bottom section ──
        settings_sep = QFrame()
        settings_sep.setFrameShape(QFrame.Shape.HLine)
        settings_sep.setStyleSheet(f"background: {Colors.BORDER_SUBTLE}; max-height: 1px; margin-bottom: 8px;")
        layout.addWidget(settings_sep)

        settings_btn = NavButton("⚙", "Ayarlar")
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
        self._setup_ui()
        self._setup_connections()
        self._navigate_to(PAGE_DASHBOARD)

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

        self._stack.addWidget(self._dashboard)   # 0
        self._stack.addWidget(self._library)     # 1
        self._stack.addWidget(self._detail)      # 2
        self._stack.addWidget(self._settings)    # 3

    def _setup_connections(self) -> None:
        # Sidebar navigation
        self._sidebar.navigate.connect(self._navigate_to)

        # Dashboard
        self._dashboard.open_add_dialog.connect(self._open_add_dialog)
        self._dashboard.word_clicked.connect(self._show_word_detail)
        self._dashboard.favorite_toggled.connect(self._toggle_favorite)

        # Library
        self._library.open_add_dialog.connect(self._open_add_dialog)
        self._library.word_clicked.connect(self._show_word_detail)
        self._library.favorite_toggled.connect(self._toggle_favorite)

        # Detail
        self._detail.back_requested.connect(self._go_back)
        self._detail.word_deleted.connect(self._on_word_changed)
        self._detail.word_updated.connect(self._on_word_changed)

        # Settings
        self._settings.settings_changed.connect(self._on_word_changed)

    def _navigate_to(self, page: int) -> None:
        current = self._stack.currentIndex()
        if current != PAGE_DETAIL:
            self._previous_page = current

        self._stack.setCurrentIndex(page)
        self._sidebar.set_active_page(page)

        # Refresh on navigate
        if page == PAGE_DASHBOARD:
            self._dashboard.refresh()
        elif page == PAGE_LIBRARY:
            self._library.refresh()

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

    def _toggle_favorite(self, word_id: str) -> None:
        try:
            self._service.toggle_favorite(word_id)
            self._dashboard.refresh()
            self._library.refresh()
        except Exception:
            pass

    def _go_back(self) -> None:
        target = self._previous_page if self._previous_page is not None else PAGE_DASHBOARD
        self._navigate_to(target)

    def _on_word_changed(self, _: str = "") -> None:
        self._dashboard.refresh()
        self._library.refresh()
