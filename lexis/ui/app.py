"""
Lexis — Application Bootstrap

QApplication oluşturma, tema uygulama ve pencere başlatma.
"""

from __future__ import annotations

import logging
import os
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QStyleFactory

from lexis.config.settings import get_settings
from lexis.persistence.database import Database
from lexis.persistence.word_repository import WordRepository
from lexis.services.ai_service import AIService
from lexis.services.export_service import ExportService
from lexis.services.word_service import WordService
from lexis.ui.theme import apply_theme
from lexis.ui.windows.main_window import MainWindow


def setup_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def create_services() -> tuple[WordService, ExportService]:
    """Bağımlılık ağacını kurarak servis nesnelerini oluşturur."""
    settings = get_settings()
    db = Database(settings.db_path)
    repo = WordRepository(db)

    ai = AIService(api_key=settings.gemini_api_key if settings.has_api_key else None)

    word_service = WordService(repository=repo, ai_service=ai)
    export_service = ExportService(repository=repo)

    return word_service, export_service


def run() -> int:
    """Uygulamayı başlatır ve çıkış kodunu döndürür."""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Lexis başlatılıyor...")

    style_override = os.environ.get("QT_STYLE_OVERRIDE")
    available_styles = {style.lower() for style in QStyleFactory.keys()}
    if style_override and style_override.lower() not in available_styles:
        logger.info("Geçersiz QT_STYLE_OVERRIDE değeri temizleniyor: %s", style_override)
        os.environ.pop("QT_STYLE_OVERRIDE", None)

    app = QApplication(sys.argv)
    app.setApplicationName("Lexis")
    app.setOrganizationName("Lexis")
    app.setApplicationVersion("0.1.0")

    # Qt6'da yüksek DPI pixmap desteği varsayılan olabilir; eski enum yoksa atla.
    high_dpi_attr = getattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps", None)
    if high_dpi_attr is not None:
        app.setAttribute(high_dpi_attr, True)

    # Varsayılan font
    font = QFont("Inter")
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    # Tema varsayılanını yükle
    theme_name = get_settings().app_theme
    from lexis.ui.theme import set_theme
    set_theme(theme_name)
    apply_theme(app)

    # Servisler
    word_service, export_service = create_services()

    # Ana pencere
    # Python GC'nin temizlememesi için window referansını app'e takıyoruz
    app._main_window = MainWindow(word_service=word_service, export_service=export_service)
    
    def on_theme_changed(new_theme: str) -> None:
        logger.info("Tema değiştiriliyor: %s", new_theme)
        set_theme(new_theme)
        apply_theme(app)
        
        # Yeni pencere oluştur ve Ayarlar sayfasını aç
        new_window = MainWindow(word_service=word_service, export_service=export_service)
        # Settings sayfasının indexi 3 (PAGE_SETTINGS)
        new_window._navigate_to(3) 
        new_window.show()
        
        old_window = app._main_window
        app._main_window = new_window
        app._main_window._settings.theme_changed.connect(on_theme_changed)
        old_window.close()
        old_window.deleteLater()

    app._main_window._settings.theme_changed.connect(on_theme_changed)
    app._main_window.show()

    logger.info("Lexis hazır.")
    return app.exec()
