"""
Lexis — View: Settings

API anahtarı, import/export ve uygulama ayarları.
"""

from __future__ import annotations

import logging
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
from lexis.ui.theme import repolish
from lexis.ui.widgets.common import Divider
from lexis.workers.task_worker import TaskWorker

logger = logging.getLogger(__name__)


class SettingsSection(QWidget):
    """Ayarlar bölüm kutusu."""

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        container = QFrame()
        container.setObjectName("card")
        self._inner = QVBoxLayout(container)
        self._inner.setContentsMargins(24, 20, 24, 22)
        self._inner.setSpacing(16)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("cardTitle")
        self._inner.addWidget(title_lbl)

        self._inner.addWidget(Divider())

        layout.addWidget(container)

    def add_widget(self, w: QWidget) -> None:
        self._inner.addWidget(w)

    def add_layout(self, inner_layout) -> None:
        self._inner.addLayout(inner_layout)


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
        self._workers: list[TaskWorker] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top Bar ──
        topbar = QWidget()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(72)
        tb_layout = QHBoxLayout(topbar)
        tb_layout.setContentsMargins(36, 0, 36, 0)
        title = QLabel("Ayarlar")
        title.setObjectName("pageTitle")
        tb_layout.addWidget(title)
        tb_layout.addStretch()
        root.addWidget(topbar)

        # ── Scroll Content ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setObjectName("contentSurface")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(36, 12, 36, 48)
        layout.setSpacing(20)

        # ── Appearance Section ──
        appearance_section = SettingsSection("🎨  Görünüm")
        app_desc = QLabel("Uygulama temasını seçin.")
        app_desc.setObjectName("descText")
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

        # Seçili tema birincil buton olarak vurgulanır; renkleri #primaryBtn
        # QSS kuralından gelir.
        active_theme = get_settings().app_theme
        selected = self._light_btn if active_theme == "light" else self._dark_btn
        selected.setObjectName("primaryBtn")

        appearance_section.add_layout(theme_row)
        layout.addWidget(appearance_section)

        # ── İçerik kaynağı ──
        source_section = SettingsSection("📚  İçerik Kaynağı")
        self._source_label = QLabel("")
        self._source_label.setWordWrap(True)
        self._source_label.setObjectName("descText")
        source_section.add_widget(self._source_label)
        layout.addWidget(source_section)
        self._refresh_source_label()

        # ── API Key Section ──
        api_section = SettingsSection("🔑  Gemini API Anahtarı (isteğe bağlı)")

        desc = QLabel(
            "Anahtar girmeden de kelime ekleyebilirsiniz: içerik açık sözlük "
            "kaynaklarından derlenir. Gemini anahtarı girerseniz tanımlar daha "
            "akıcı Türkçe olur ve kullanım notu eklenir.\n\n"
            "Anahtar yalnızca yerel veritabanınızda (~/.lexis/lexis.db) saklanır."
        )
        desc.setWordWrap(True)
        desc.setObjectName("descText")
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
        self._api_status.setObjectName("statusText")
        api_section.add_widget(self._api_status)

        # Bağlantı rengi uygulama paletinden (ColorRole.Link) gelir; rich text
        # anchor'ları QSS color'ını almadığı için tema değişiminde palet güncellenir.
        link = QLabel(
            '<a href="https://aistudio.google.com/app/apikey">'
            "API anahtarı almak için Google AI Studio'yu ziyaret edin →</a>"
        )
        link.setOpenExternalLinks(True)
        link.setObjectName("mutedText")
        api_section.add_widget(link)

        layout.addWidget(api_section)

        # ── Database Info ──
        db_section = SettingsSection("🗄  Veritabanı")

        db_path = get_settings().db_path
        db_info = QLabel(f"Konum: {db_path}")
        db_info.setObjectName("monoText")
        db_section.add_widget(db_info)

        # Ekrana her dönüşte tazelenebilmesi için referansı saklanır.
        self._stats_label = QLabel("")
        self._stats_label.setObjectName("descText")
        db_section.add_widget(self._stats_label)
        self._refresh_stats_label()

        layout.addWidget(db_section)

        # ── Export Section ──
        export_section = SettingsSection("📤  Dışa Aktar")

        export_desc = QLabel("Tüm kelimelerinizi JSON veya CSV formatında dışa aktarın.")
        export_desc.setWordWrap(True)
        export_desc.setObjectName("descText")
        export_section.add_widget(export_desc)

        export_row = QHBoxLayout()
        export_row.setSpacing(10)

        json_export_btn = QPushButton("JSON Olarak İndir")
        json_export_btn.setObjectName("secondaryBtn")
        json_export_btn.setMinimumHeight(40)
        json_export_btn.clicked.connect(lambda: self._run_export("json"))
        export_row.addWidget(json_export_btn)

        csv_export_btn = QPushButton("CSV Olarak İndir")
        csv_export_btn.setObjectName("secondaryBtn")
        csv_export_btn.setMinimumHeight(40)
        csv_export_btn.clicked.connect(lambda: self._run_export("csv"))
        export_row.addWidget(csv_export_btn)
        export_row.addStretch()

        export_section.add_layout(export_row)

        self._export_status = QLabel("")
        self._export_status.setObjectName("statusText")
        export_section.add_widget(self._export_status)

        layout.addWidget(export_section)

        # ── Import Section ──
        import_section = SettingsSection("📥  İçe Aktar")

        import_desc = QLabel("Daha önce dışa aktardığınız JSON veya CSV dosyasından içe aktarın.")
        import_desc.setWordWrap(True)
        import_desc.setObjectName("descText")
        import_section.add_widget(import_desc)

        import_row = QHBoxLayout()
        import_row.setSpacing(10)

        json_import_btn = QPushButton("JSON Dosyası Seç")
        json_import_btn.setObjectName("secondaryBtn")
        json_import_btn.setMinimumHeight(40)
        json_import_btn.clicked.connect(lambda: self._run_import("json"))
        import_row.addWidget(json_import_btn)

        csv_import_btn = QPushButton("CSV Dosyası Seç")
        csv_import_btn.setObjectName("secondaryBtn")
        csv_import_btn.setMinimumHeight(40)
        csv_import_btn.clicked.connect(lambda: self._run_import("csv"))
        import_row.addWidget(csv_import_btn)
        import_row.addStretch()

        import_section.add_layout(import_row)

        self._import_status = QLabel("")
        self._import_status.setObjectName("statusText")
        import_section.add_widget(self._import_status)

        layout.addWidget(import_section)

        # ── About ──
        about_section = SettingsSection("ℹ  Hakkında")
        about_text = QLabel(
            "Lexis — Kişisel Sözlük & Kelime Öğrenme Uygulaması\n"
            "Sürüm 0.1.0  ·  Python & PyQt6\n"
            "Verileriniz tamamen lokal olarak saklanır."
        )
        about_text.setObjectName("descText")
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

    def _refresh_stats_label(self) -> None:
        stats = self._service.get_stats()
        self._stats_label.setText(
            f"Toplam kelime: {stats.total}  ·  Öğrenilen: {stats.learned}"
            f"  ·  Favoriler: {stats.favorites}"
        )

    def _refresh_source_label(self) -> None:
        """Şu an hangi kaynağın kullanıldığını gösterir."""
        if self._service.ai_configured:
            self._source_label.setText(
                "✨ Gemini — API anahtarınız tanımlı. Tanımlar yapay zekâ ile "
                "üretiliyor: akıcı Türkçe, kullanım notları ve örnek cümleler."
            )
        else:
            self._source_label.setText(
                "📖 Açık sözlük — anahtar gerekmez. İçerik Wiktionary, "
                "dictionaryapi.dev, Tatoeba ve MyMemory'den derlenir; telaffuz "
                "da gelir. Tanımlar uydurma değil, gerçek sözlük kaydıdır."
            )

    def refresh(self) -> None:
        """Ekrana her dönüşte güncel veriyi gösterir."""
        self._refresh_stats_label()
        self._refresh_source_label()

    @staticmethod
    def _set_status(label: QLabel, message: str, level: str) -> None:
        """
        Durum etiketini günceller. Renk, QSS'teki #statusText[level="..."]
        kuralından gelir; böylece tema değişiminde kendiliğinden yeniden boyanır.
        """
        label.setText(message)
        label.setProperty("level", level)
        repolish(label)

    def _save_api_key(self) -> None:
        key = self._api_key_input.text().strip()
        if not key:
            self._set_status(self._api_status, "API anahtarı boş olamaz.", "error")
            return
        try:
            save_api_key(key)
            self._service.configure_ai(key)
            self._set_status(self._api_status, "✓ API anahtarı kaydedildi", "success")
            self._refresh_source_label()
            self.settings_changed.emit()
        except Exception as e:
            logger.exception("API anahtarı kaydedilemedi")
            self._set_status(self._api_status, f"Hata: {e}", "error")

    def _run_in_background(
        self,
        fn,
        status_label: QLabel,
        busy_message: str,
        on_success,
    ) -> None:
        """
        Bloklayan bir dosya işlemini arka planda çalıştırır.

        Büyük kütüphanelerde senkron içe/dışa aktarma pencereyi dondururdu.
        Worker referansı saklanır; aksi hâlde GC bitmeden toplayabilir.
        """
        self._set_status(status_label, busy_message, "info")

        worker = TaskWorker(fn, parent=self)
        self._workers.append(worker)

        def cleanup() -> None:
            if worker in self._workers:
                self._workers.remove(worker)

        worker.succeeded.connect(on_success)
        worker.failed.connect(
            lambda msg: self._set_status(status_label, f"Hata: {msg}", "error")
        )
        worker.finished.connect(cleanup)
        worker.start()

    def _run_export(self, fmt: str) -> None:
        """JSON/CSV dışa aktarımını tek yerden yürütür."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            f"{fmt.upper()} Dışa Aktar",
            f"lexis_export.{fmt}",
            f"{fmt.upper()} Dosyaları (*.{fmt})",
        )
        if not path:
            return

        export = self._export.export_json if fmt == "json" else self._export.export_csv
        self._run_in_background(
            lambda: export(Path(path)),
            self._export_status,
            "Dışa aktarılıyor...",
            lambda count: self._set_status(
                self._export_status, f"✓ {count} kelime dışa aktarıldı", "success"
            ),
        )

    def _run_import(self, fmt: str) -> None:
        """JSON/CSV içe aktarımını tek yerden yürütür."""
        path, _ = QFileDialog.getOpenFileName(
            self, f"{fmt.upper()} İçe Aktar", "", f"{fmt.upper()} Dosyaları (*.{fmt})"
        )
        if not path:
            return

        do_import = self._export.import_json if fmt == "json" else self._export.import_csv

        def on_done(result) -> None:
            imported, skipped = result
            self._set_status(
                self._import_status,
                f"✓ {imported} kelime içe aktarıldı, {skipped} atlandı",
                "success",
            )
            self._refresh_stats_label()
            self.settings_changed.emit()

        self._run_in_background(
            lambda: do_import(Path(path)),
            self._import_status,
            "İçe aktarılıyor...",
            on_done,
        )

    def _trigger_theme_change(self, theme_name: str) -> None:
        save_theme(theme_name)
        self.theme_changed.emit(theme_name)
        self._sync_theme_buttons(theme_name)

    def _sync_theme_buttons(self, active_theme: str) -> None:
        """Seçili temayı birincil buton olarak vurgular."""
        for btn, name in ((self._dark_btn, "dark"), (self._light_btn, "light")):
            btn.setObjectName("primaryBtn" if name == active_theme else "secondaryBtn")
            repolish(btn)
