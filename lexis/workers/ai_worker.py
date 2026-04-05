"""
Lexis — AI Worker

QThread tabanlı arka plan işçisi. AI çağrıları sırasında UI'ı bloklamaz.
"""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from lexis.services.ai_service import AIService


class AIGenerationWorker(QThread):
    """AI içerik üretimini arka planda çalıştıran QThread worker."""

    # Başarılı tamamlanma: üretilen veri dict
    finished = pyqtSignal(dict)
    # Hata: hata mesajı string
    error = pyqtSignal(str)
    # İlerleme bildirimi (isteğe bağlı string mesaj)
    progress = pyqtSignal(str)

    def __init__(
        self,
        ai_service: AIService,
        term: str,
        language: str = "en",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._ai_service = ai_service
        self._term = term
        self._language = language

    def run(self) -> None:
        """QThread tarafından çağrılır. Ana thread'i bloklamaz."""
        try:
            self.progress.emit(f"'{self._term}' için içerik üretiliyor...")
            data = self._ai_service.generate_word_data(self._term, self._language)
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))


class AIRegenerateWorker(QThread):
    """Mevcut kelime için AI içeriğini yenileyen worker."""

    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(
        self,
        ai_service: AIService,
        term: str,
        language: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._ai_service = ai_service
        self._term = term
        self._language = language

    def run(self) -> None:
        try:
            data = self._ai_service.generate_word_data(self._term, self._language)
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))
