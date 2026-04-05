"""
Lexis — View: Settings

API anahtarı, import/export ve uygulama ayarları.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from lexis.config.settings import get_settings, save_api_key, save_theme
from lexis.services.export_service import ExportService
from lexis.services.word_service import WordService
from lexis.ui.theme import Colors


class SettingsSection(QWidget):
    """Ayarlar bölüm kutusu."""

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        container = QFrame()
        container.setObjectName("card")
        container.setStyleSheet(f"""
            QFrame#card {{
                background: {Colors.BG_SURFACE};
                border-radius: 14px;
                border: 1px solid {Colors.BORDER_SUBTLE};
            }}
        """)
        self._inner = QVBoxLayout(container)
        self._inner.setContentsMargins(24, 20, 24, 22)
        self._inner.setSpacing(16)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-size: 14px;
            font-weight: 600;
        """)
        self._inner.addWidget(title_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {Colors.BORDER_SUBTLE}; max-height:1px;")
        self._inner.addWidget(sep)

        layout.addWidget(container)

    def add_widget(self, w: QWidget) -> None:
        self._inner.addWidget(w)

    def add_layout(self, l) -> None:
        self._inner.addLayout(l)


class SettingsView(QWidget):
    """Ayarlar ekranı."""

    settings_changed = pyqtSignal()
    theme_changed = pyqtSignal(str)

    def __init__(
        self,
        word_service: WordService,
        export_service: ExportService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = word_service
        self._export = export_service
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top Bar ──
        topbar = QWidget()
        topbar.setFixedHeight(72)
        topbar.setStyleSheet(f"background: {Colors.BG_BASE};")
        tb_layout = QHBoxLayout(topbar)
        tb_layout.setContentsMargins(36, 0, 36, 0)
        title = QLabel("Ayarlar")
        title.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-size: 22px;
            font-weight: 700;
        """)
        tb_layout.addWidget(title)
        tb_layout.addStretch()
        root.addWidget(topbar)

        # ── Scroll Content ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setStyleSheet(f"background: {Colors.BG_BASE};")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(36, 12, 36, 48)
        layout.setSpacing(20)

        # ── Appearance Section ──
        appearance_section = SettingsSection("🎨  Görünüm")
        app_desc = QLabel("Uygulama temasını seçin.")
        app_desc.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 13px;")
        appearance_section.add_widget(app_desc)

        theme_row = QHBoxLayout()
        theme_row.setSpacing(10)
        
        self._dark_btn = QPushButton("Karanlık Tema")
        self._dark_btn.setObjectName("secondaryBtn")
        self._dark_btn.setMinimumHeight(44)
        self._dark_btn.clicked.connect(lambda: self._trigger_theme_change("dark"))
        theme_row.addWidget(self._dark_btn)

        self._light_btn = QPushButton("Aydınlık Tema")
        self._light_btn.setObjectName("secondaryBtn")
        self._light_btn.setMinimumHeight(44)
        self._light_btn.clicked.connect(lambda: self._trigger_theme_change("light"))
        theme_row.addWidget(self._light_btn)
        theme_row.addStretch()

        active_theme = get_settings().app_theme
        if active_theme == "light":
            self._light_btn.setObjectName("primaryBtn")
            self._light_btn.setStyleSheet(f"background-color: {Colors.ACCENT}; color: white; border: none;")
        else:
            self._dark_btn.setObjectName("primaryBtn")
            self._dark_btn.setStyleSheet(f"background-color: {Colors.ACCENT}; color: white; border: none;")

        appearance_section.add_layout(theme_row)
        layout.addWidget(appearance_section)

        # ── API Key Section ──
        api_section = SettingsSection("🔑  Gemini API Anahtarı")

        desc = QLabel(
            "Google AI Studio'dan aldığınız API anahtarını buraya girin. "
            "Anahtar yerel olarak .env dosyasında saklanır."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 13px; line-height: 1.6;")
        api_section.add_widget(desc)

        api_row = QHBoxLayout()
        api_row.setSpacing(10)

        self._api_key_input = QLineEdit()
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_input.setPlaceholderText("AIzaSy...")
        self._api_key_input.setMinimumHeight(44)
        settings = get_settings()
        if settings.has_api_key:
            self._api_key_input.setText(settings.gemini_api_key or "")
        api_row.addWidget(self._api_key_input, 1)

        show_btn = QPushButton("Göster")
        show_btn.setObjectName("secondaryBtn")
        show_btn.setFixedHeight(44)
        show_btn.setMinimumWidth(80)
        show_btn.clicked.connect(self._toggle_key_visibility)
        self._show_btn = show_btn
        api_row.addWidget(show_btn)

        save_btn = QPushButton("Kaydet")
        save_btn.setObjectName("primaryBtn")
        save_btn.setFixedHeight(44)
        save_btn.setMinimumWidth(90)
        save_btn.clicked.connect(self._save_api_key)
        api_row.addWidget(save_btn)
        api_section.add_layout(api_row)

        self._api_status = QLabel("")
        self._api_status.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px;")
        api_section.add_widget(self._api_status)

        link = QLabel('<a href="https://aistudio.google.com/app/apikey" style="color: #7C6EE8;">API anahtarı almak için Google AI Studio\'yu ziyaret edin →</a>')
        link.setOpenExternalLinks(True)
        link.setStyleSheet(f"font-size: 12px;")
        api_section.add_widget(link)

        layout.addWidget(api_section)

        # ── Database Info ──
        db_section = SettingsSection("🗄  Veritabanı")

        db_path = get_settings().db_path
        db_info = QLabel(f"Konum: {db_path}")
        db_info.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: 12px;
            font-family: monospace;
        """)
        db_section.add_widget(db_info)

        stats = self._service.get_stats()
        stats_label = QLabel(f"Toplam kelime: {stats.total}  ·  Öğrenilen: {stats.learned}  ·  Favoriler: {stats.favorites}")
        stats_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 13px;")
        db_section.add_widget(stats_label)

        layout.addWidget(db_section)

        # ── Export Section ──
        export_section = SettingsSection("📤  Dışa Aktar")

        export_desc = QLabel("Tüm kelimelerinizi JSON veya CSV formatında dışa aktarın.")
        export_desc.setWordWrap(True)
        export_desc.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 13px;")
        export_section.add_widget(export_desc)

        export_row = QHBoxLayout()
        export_row.setSpacing(10)

        json_export_btn = QPushButton("JSON Olarak İndir")
        json_export_btn.setObjectName("secondaryBtn")
        json_export_btn.setMinimumHeight(40)
        json_export_btn.clicked.connect(self._export_json)
        export_row.addWidget(json_export_btn)

        csv_export_btn = QPushButton("CSV Olarak İndir")
        csv_export_btn.setObjectName("secondaryBtn")
        csv_export_btn.setMinimumHeight(40)
        csv_export_btn.clicked.connect(self._export_csv)
        export_row.addWidget(csv_export_btn)
        export_row.addStretch()

        export_section.add_layout(export_row)

        self._export_status = QLabel("")
        self._export_status.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px;")
        export_section.add_widget(self._export_status)

        layout.addWidget(export_section)

        # ── Import Section ──
        import_section = SettingsSection("📥  İçe Aktar")

        import_desc = QLabel("Daha önce dışa aktardığınız JSON veya CSV dosyasından içe aktarın.")
        import_desc.setWordWrap(True)
        import_desc.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 13px;")
        import_section.add_widget(import_desc)

        import_row = QHBoxLayout()
        import_row.setSpacing(10)

        json_import_btn = QPushButton("JSON Dosyası Seç")
        json_import_btn.setObjectName("secondaryBtn")
        json_import_btn.setMinimumHeight(40)
        json_import_btn.clicked.connect(self._import_json)
        import_row.addWidget(json_import_btn)

        csv_import_btn = QPushButton("CSV Dosyası Seç")
        csv_import_btn.setObjectName("secondaryBtn")
        csv_import_btn.setMinimumHeight(40)
        csv_import_btn.clicked.connect(self._import_csv)
        import_row.addWidget(csv_import_btn)
        import_row.addStretch()

        import_section.add_layout(import_row)

        self._import_status = QLabel("")
        self._import_status.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px;")
        import_section.add_widget(self._import_status)

        layout.addWidget(import_section)

        # ── About ──
        about_section = SettingsSection("ℹ  Hakkında")
        about_text = QLabel(
            "Lexis — Kişisel Sözlük & Kelime Öğrenme Uygulaması\n"
            "Sürüm 0.1.0  ·  Python & PyQt6\n"
            "Verileriniz tamamen lokal olarak saklanır."
        )
        about_text.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: 13px;
            line-height: 1.8;
        """)
        about_section.add_widget(about_text)
        layout.addWidget(about_section)

        layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

    def _toggle_key_visibility(self) -> None:
        if self._api_key_input.echoMode() == QLineEdit.EchoMode.Password:
            self._api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._show_btn.setText("Gizle")
        else:
            self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._show_btn.setText("Göster")

    def _save_api_key(self) -> None:
        key = self._api_key_input.text().strip()
        if not key:
            self._api_status.setText("API anahtarı boş olamaz.")
            self._api_status.setStyleSheet(f"color: {Colors.ERROR}; font-size: 12px;")
            return
        try:
            save_api_key(key)
            self._service._ai.configure(key)
            self._api_status.setText("✓ API anahtarı kaydedildi")
            self._api_status.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 12px;")
            self.settings_changed.emit()
        except Exception as e:
            self._api_status.setText(f"Hata: {e}")
            self._api_status.setStyleSheet(f"color: {Colors.ERROR}; font-size: 12px;")

    def _export_json(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "JSON Dışa Aktar", "lexis_export.json", "JSON Dosyaları (*.json)"
        )
        if path:
            try:
                count = self._export.export_json(Path(path))
                self._export_status.setText(f"✓ {count} kelime dışa aktarıldı")
                self._export_status.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 12px;")
            except Exception as e:
                self._export_status.setText(f"Hata: {e}")
                self._export_status.setStyleSheet(f"color: {Colors.ERROR}; font-size: 12px;")

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "CSV Dışa Aktar", "lexis_export.csv", "CSV Dosyaları (*.csv)"
        )
        if path:
            try:
                count = self._export.export_csv(Path(path))
                self._export_status.setText(f"✓ {count} kelime dışa aktarıldı")
                self._export_status.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 12px;")
            except Exception as e:
                self._export_status.setText(f"Hata: {e}")
                self._export_status.setStyleSheet(f"color: {Colors.ERROR}; font-size: 12px;")

    def _import_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "JSON İçe Aktar", "", "JSON Dosyaları (*.json)"
        )
        if path:
            try:
                imported, skipped = self._export.import_json(Path(path))
                self._import_status.setText(f"✓ {imported} kelime içe aktarıldı, {skipped} atlandı")
                self._import_status.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 12px;")
                self.settings_changed.emit()
            except Exception as e:
                self._import_status.setText(f"Hata: {e}")
                self._import_status.setStyleSheet(f"color: {Colors.ERROR}; font-size: 12px;")

    def _import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "CSV İçe Aktar", "", "CSV Dosyaları (*.csv)"
        )
        if path:
            try:
                imported, skipped = self._export.import_csv(Path(path))
                self._import_status.setText(f"✓ {imported} kelime içe aktarıldı, {skipped} atlandı")
                self._import_status.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 12px;")
                self.settings_changed.emit()
            except Exception as e:
                self._import_status.setText(f"Hata: {e}")
                self._import_status.setStyleSheet(f"color: {Colors.ERROR}; font-size: 12px;")

    def _trigger_theme_change(self, theme_name: str) -> None:
        save_theme(theme_name)
        self.theme_changed.emit(theme_name)
