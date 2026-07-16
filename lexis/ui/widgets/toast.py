"""
Lexis — Widget: Toast Bildirimleri

Modal olmayan, kendiliğinden kapanan bildirim şeridi. Sessizce yutulan
hataların kullanıcıya görünmesini ve silme gibi işlemlerin geri alınmasını
sağlar.

Renkler global QSS'ten (#toast[level="..."]) gelir; tema değişiminde
kendiliğinden yeniden boyanırlar.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    QTimer,
)
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

logger = logging.getLogger(__name__)

TOAST_MARGIN = 24
TOAST_SPACING = 8
FADE_MS = 160


class Toast(QFrame):
    """Tek bir bildirim şeridi."""

    def __init__(
        self,
        message: str,
        level: str = "info",
        action_label: str | None = None,
        on_action: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("toast")
        self.setProperty("level", level)
        self._on_action = on_action
        self._dismissed = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 12, 12)
        layout.setSpacing(12)

        label = QLabel(message)
        label.setObjectName("toastText")
        label.setWordWrap(True)
        label.setMaximumWidth(360)
        layout.addWidget(label, 1)

        if action_label and on_action:
            btn = QPushButton(action_label)
            btn.setObjectName("toastAction")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(self._trigger_action)
            layout.addWidget(btn)

        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._effect.setOpacity(0.0)

        self.adjustSize()

    def _trigger_action(self) -> None:
        # Aksiyon bir kez çalışsın: kullanıcı hızlı çift tıklarsa iki kez
        # geri alma yapılmamalı.
        if self._dismissed:
            return
        self._dismissed = True
        try:
            if self._on_action:
                self._on_action()
        except Exception:
            logger.exception("Toast aksiyonu başarısız")
        finally:
            self.fade_out()

    def fade_in(self) -> None:
        self.show()
        self._anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._anim.setDuration(FADE_MS)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()

    def fade_out(self) -> None:
        if not self.isVisible():
            return
        self._anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._anim.setDuration(FADE_MS)
        self._anim.setStartValue(self._effect.opacity())
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._anim.finished.connect(self._finish)
        self._anim.start()

    def _finish(self) -> None:
        self.hide()
        parent = self.parent()
        manager = getattr(parent, "_toast_manager", None) if parent else None
        if manager is not None:
            manager._remove(self)
        self.deleteLater()


class ToastManager:
    """
    Bir pencereye bağlı bildirim yöneticisi.

    Bildirimleri pencerenin sağ altına, üst üste binmeyecek şekilde yığar.
    """

    MAX_VISIBLE = 3

    def __init__(self, host: QWidget) -> None:
        self._host = host
        self._toasts: list[Toast] = []
        host._toast_manager = self  # Toast._finish geri çağırabilsin

    def show(
        self,
        message: str,
        *,
        level: str = "info",
        action_label: str | None = None,
        on_action: Callable[[], None] | None = None,
        duration_ms: int = 4000,
    ) -> Toast:
        """
        Bildirim gösterir.

        action_label/on_action verilirse tıklanabilir bir aksiyon (ör. "Geri al")
        eklenir. duration_ms=0 kalıcı yapar (yalnızca aksiyonla kapanır).
        """
        toast = Toast(message, level, action_label, on_action, parent=self._host)

        # Ekranı doldurmasın: en eskiyi düşür.
        while len(self._toasts) >= self.MAX_VISIBLE:
            self._toasts[0].fade_out()
            self._toasts.pop(0)

        self._toasts.append(toast)
        self._reposition()
        toast.fade_in()

        if duration_ms > 0:
            QTimer.singleShot(duration_ms, toast.fade_out)

        return toast

    def error(self, message: str) -> Toast:
        return self.show(message, level="error", duration_ms=6000)

    def success(self, message: str) -> Toast:
        return self.show(message, level="success")

    def _remove(self, toast: Toast) -> None:
        if toast in self._toasts:
            self._toasts.remove(toast)
            self._reposition()

    def _reposition(self) -> None:
        """Bildirimleri sağ alttan yukarı doğru dizer."""
        y = self._host.height() - TOAST_MARGIN
        for toast in reversed(self._toasts):
            toast.adjustSize()
            y -= toast.height()
            toast.move(self._host.width() - toast.width() - TOAST_MARGIN, y)
            y -= TOAST_SPACING
            toast.raise_()

    def reposition(self) -> None:
        """Pencere yeniden boyutlandığında çağrılır."""
        self._reposition()
