"""
Lexis — Application Bootstrap

QApplication oluşturma, tema uygulama ve pencere başlatma.
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QStyleFactory

from lexis.config.settings import bind_database, get_settings
from lexis.persistence.database import Database
from lexis.persistence.word_repository import WordRepository
from lexis.services.ai_service import AIService
from lexis.services.export_service import ExportService
from lexis.services.word_service import WordService
from lexis.ui.theme import apply_theme, repolish, set_theme
from lexis.ui.windows.main_window import MainWindow


def setup_logging() -> None:
    """
    Konsola ve ~/.lexis/lexis.log dosyasına loglar.

    Masaüstü uygulaması genelde terminalden başlatılmadığı için konsol çıktısı
    kaybolur; dosya kaydı olmadan çökmeleri sonradan teşhis etmek mümkün olmaz.
    """
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    try:
        log_path = settings.db_path.parent / "lexis.log"
        handlers.append(
            RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        )
    except OSError:
        # Log dosyası açılamıyorsa (salt-okunur dizin vb.) uygulama yine de açılmalı.
        pass

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
    )


def create_services() -> tuple[WordService, ExportService]:
    """Bağımlılık ağacını kurarak servis nesnelerini oluşturur."""
    settings = get_settings()
    db = Database(settings.db_path)

    # Kalıcı tercihleri (API anahtarı, tema) DB'den yükle.
    bind_database(db)
    settings = get_settings()

    repo = WordRepository(db)
    ai = AIService(
        api_key=settings.gemini_api_key if settings.has_api_key else None,
        model=settings.gemini_model,
    )

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

    # Servisler (DB'yi de bağlar; kalıcı tercihler buradan sonra okunabilir)
    word_service, export_service = create_services()

    # Tema tercihini (DB'den) yükle ve uygula
    theme_name = get_settings().app_theme
    set_theme(theme_name)
    apply_theme(app)

    def on_theme_changed(new_theme: str) -> None:
        """
        Temayı yerinde değiştirir.

        Renkler global QSS'te tanımlı olduğundan stylesheet'i yenileyip widget
        ağacını yeniden boyamak yeterli: pencere yeniden kurulmaz, dolayısıyla
        arama metni, scroll konumu ve açık kelime korunur.
        """
        logger.info("Tema değiştiriliyor: %s", new_theme)
        set_theme(new_theme)
        apply_theme(app)
        repolish(app._main_window)

    window = MainWindow(word_service=word_service, export_service=export_service)
    window._settings.theme_changed.connect(on_theme_changed)

    # Python GC'nin temizlememesi için window referansını app'e takıyoruz
    app._main_window = window
    window.show()

    logger.info("Lexis hazır.")
    return app.exec()
