"""
Lexis — Widget: Aktivite Grafiği

Son 7 günün tekrar sayısını gösteren sütun grafiği. Saf QPainter ile çizilir;
grafik kütüphanesi bağımlılığı yoktur.

Renkler boyama anında Colors'tan okunur, dolayısıyla tema değişiminde
kendiliğinden doğru renkte yeniden çizilir.
"""

from __future__ import annotations

from datetime import date

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath
from PyQt6.QtWidgets import QSizePolicy, QWidget

from lexis.ui.theme import Colors

# Pazartesi=0 (date.weekday sırası)
DAY_INITIALS = ("Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz")

CHART_HEIGHT = 132
BAR_RADIUS = 4
LABEL_HEIGHT = 18
VALUE_HEIGHT = 14
MIN_BAR_HEIGHT = 3
BAR_GAP = 10


class ActivityChart(QWidget):
    """Gün → tekrar sayısı sütun grafiği."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._counts: dict[date, int] = {}
        self.setFixedHeight(CHART_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_counts(self, counts: dict[date, int]) -> None:
        """Veriyi günün sırasına göre (eskiden yeniye) alır."""
        self._counts = counts
        self.setToolTip(f"Son {len(counts)} günde {sum(counts.values())} tekrar")
        self.update()

    def paintEvent(self, event) -> None:
        if not self._counts:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        days = sorted(self._counts)
        peak = max(self._counts.values())
        today = date.today()

        slot_width = self.width() / len(days)
        bar_width = max(6.0, slot_width - BAR_GAP)
        plot_height = self.height() - LABEL_HEIGHT - VALUE_HEIGHT

        accent = QColor(Colors.ACCENT)
        # Boş günün izi kart zemininde görünmeli: BG_ELEVATED açık temada
        # kart arka planıyla aynı renk olduğu için çubuk kayboluyordu.
        muted_bar = QColor(Colors.BORDER)
        text_muted = QColor(Colors.TEXT_MUTED)

        font = QFont(painter.font())
        font.setPointSize(8)
        painter.setFont(font)

        for i, day in enumerate(days):
            count = self._counts[day]
            x = i * slot_width + (slot_width - bar_width) / 2

            # Boş günler de bir iz bırakır; grafik "delik" görünmesin.
            ratio = (count / peak) if peak else 0
            bar_height = max(MIN_BAR_HEIGHT, ratio * plot_height)
            y = VALUE_HEIGHT + plot_height - bar_height

            path = QPainterPath()
            path.addRoundedRect(QRectF(x, y, bar_width, bar_height), BAR_RADIUS, BAR_RADIUS)
            painter.fillPath(path, accent if count else muted_bar)

            # Sayı yalnızca tekrar yapılmış günlerde yazılır.
            if count:
                painter.setPen(text_muted)
                painter.drawText(
                    QRectF(x - BAR_GAP / 2, 0, bar_width + BAR_GAP, VALUE_HEIGHT),
                    Qt.AlignmentFlag.AlignCenter,
                    str(count),
                )

            # Bugünün etiketi vurgulanır.
            painter.setPen(accent if day == today else text_muted)
            label_font = QFont(font)
            label_font.setBold(day == today)
            painter.setFont(label_font)
            painter.drawText(
                QRectF(x - BAR_GAP / 2, self.height() - LABEL_HEIGHT, bar_width + BAR_GAP, LABEL_HEIGHT),
                Qt.AlignmentFlag.AlignCenter,
                DAY_INITIALS[day.weekday()],
            )
            painter.setFont(font)

        painter.end()
