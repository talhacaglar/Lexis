"""
Lexis — Ortak UI Primitifleri

Birden fazla ekranda tekrarlanan küçük widget'lar. Stilleri global QSS'ten
gelir (theme.py); hiçbiri renk gömmez, böylece tema değişiminde pencere
yeniden kurulmadan yeniden boyanabilirler.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QLabel, QWidget


class Divider(QFrame):
    """
    Yatay ayırıcı çizgi. Stili QSS'teki QFrame#separator kuralından gelir.

    spaced=True altına boşluk bırakır (sidebar bölümleri arasında kullanılır).
    """

    def __init__(self, spaced: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("separator")
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFixedHeight(1)
        if spaced:
            self.setProperty("spaced", "true")


class SectionLabel(QLabel):
    """Küçük, seyrek harfli bölüm başlığı (ör. "TANIM", "ÖRNEKLER")."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("sectionTitle")


class Chip(QLabel):
    """
    Küçük etiket/rozet.

    variant="accent" vurgu renklerini kullanır; varsayılan nötr yüzeydir.
    """

    def __init__(
        self,
        text: str,
        variant: str = "default",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setObjectName("chip")
        self.setProperty("variant", variant)


class StatusBadge(QLabel):
    """
    Öğrenme durumu rozeti. Renkleri QSS'teki QLabel#badge[status="..."]
    kurallarından alır (theme._badge_status_rules).
    """

    def __init__(self, status: str, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("badge")
        self.setProperty("status", status)

    def set_status(self, status: str, text: str) -> None:
        from lexis.ui.theme import repolish

        self.setProperty("status", status)
        self.setText(text)
        repolish(self)
