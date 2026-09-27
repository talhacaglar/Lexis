"""
Lexis — Genel Arka Plan İşçisi

Bloklayan bir çağrıyı (dosya okuma/yazma, toplu DB işlemi) arka planda çalıştırır.
Büyük kütüphanelerde içe/dışa aktarma UI thread'inde yapıldığında pencere
donuyordu.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from PyQt6.QtCore import Qt, QThread, pyqtSignal

logger = logging.getLogger(__name__)


class TaskWorker(QThread):
    """
    Verilen fonksiyonu arka planda çalıştırır; sonucu ya da hatayı sinyalle
    ana thread'e iletir.

    Not: SQLite bağlantıları thread'ler arasında paylaşılamaz. Repository her
    çağrıda kendi bağlantısını açtığı için buradan repo çağırmak güvenlidir.
    """

    succeeded = pyqtSignal(object)  # fonksiyonun dönüş değeri
    failed = pyqtSignal(str)  # hata mesajı

    def __init__(self, fn: Callable[[], Any], parent=None) -> None:
        super().__init__(parent)
        self._fn = fn
        if parent is not None:
            # QObject emits destroyed before deleting its children. A bounded
            # closeEvent wait is insufficient for slow I/O and older workers
            # whose UI reference was replaced by a newer request.
            parent.destroyed.connect(
                self._wait_before_parent_deletion, Qt.ConnectionType.DirectConnection
            )

    def _wait_before_parent_deletion(self) -> None:
        # No result/cleanup callback may access an owner during destruction.
        for signal in (self.succeeded, self.failed, self.finished):
            try:
                signal.disconnect()
            except TypeError:
                pass
        self.requestInterruption()
        self.wait()

    def run(self) -> None:
        try:
            self.succeeded.emit(self._fn())
        except Exception as e:
            logger.exception("Arka plan görevi başarısız")
            self.failed.emit(str(e))
