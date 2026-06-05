"""
Lexis — Icons

Tema rengine göre yeniden renklendirilebilen minimalist çizgi (line) ikonları.
SVG yol verileri tek renklidir; `colored_icon` ile istenen renkte QIcon üretilir.
"""

from __future__ import annotations

from PyQt6.QtCore import QByteArray, QSize, Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

# 24x24 viewBox, stroke tabanlı minimalist ikonlar. {color} çalışma anında doldurulur.
_PATHS: dict[str, str] = {
    "home": "<path d='M3 9.8 12 3l9 6.8'/><path d='M5.2 9v11h13.6V9'/>",
    "book": "<path d='M5 4h11.5a1.5 1.5 0 0 1 1.5 1.5V20H6.5A1.5 1.5 0 0 1 5 18.5V4z'/>"
            "<path d='M18 16.5H6.5A1.5 1.5 0 0 0 5 18'/>",
    "cards": "<rect x='3.5' y='6.5' width='13' height='13' rx='2'/>"
             "<path d='M7.5 6.5V5a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-1.5'/>",
    "settings": "<path d='M4 7h9'/><path d='M17 7h3'/><circle cx='15' cy='7' r='2'/>"
                "<path d='M4 17h3'/><path d='M11 17h9'/><circle cx='9' cy='17' r='2'/>",
}


def _svg(name: str, color: str) -> bytes:
    body = _PATHS[name]
    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
        f"stroke='{color}' stroke-width='1.7' stroke-linecap='round' "
        f"stroke-linejoin='round'>{body}</svg>"
    ).encode()


def colored_icon(name: str, color: str, size: int = 18) -> QIcon:
    """Verilen ikonu istenen renkte (HiDPI'a uygun) bir QIcon olarak döndürür."""
    renderer = QSvgRenderer(QByteArray(_svg(name, color)))
    scale = 2  # keskinlik için 2x render
    pixmap = QPixmap(QSize(size * scale, size * scale))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(scale)
    return QIcon(pixmap)
