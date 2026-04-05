"""
Lexis — Design System & Theme

Tüm renk, tipografi ve QSS stylesheet tanımları bu modülde merkezileştirilmiştir.
"""

from __future__ import annotations

from PyQt6.QtGui import QFont, QFontDatabase


# ─────────────────────────────────────────────────────────────────────────────
# Renk Paleti Altyapısı
# ─────────────────────────────────────────────────────────────────────────────

class PaletteClass:
    BG_BASE: str
    BG_SURFACE: str
    BG_ELEVATED: str
    BG_HOVER: str
    BG_PRESSED: str

    BORDER: str
    BORDER_FOCUS: str
    BORDER_SUBTLE: str

    ACCENT: str
    ACCENT_HOVER: str
    ACCENT_MUTED: str
    ACCENT_LIGHT: str

    TEXT_PRIMARY: str
    TEXT_SECONDARY: str
    TEXT_MUTED: str
    TEXT_INVERSE: str

    STATUS_NEW: str
    STATUS_LEARNING: str
    STATUS_LEARNED: str
    STATUS_REVIEW: str

    SUCCESS: str
    WARNING: str
    ERROR: str
    INFO: str
    FAVORITE: str

    SCROLLBAR_BG: str
    SCROLLBAR_HANDLE: str
    SCROLLBAR_HOVER: str

    def update(self, theme_dict: dict) -> None:
        for k, v in theme_dict.items():
            setattr(self, k, v)


Colors = PaletteClass()

DARK_THEME = {
    "BG_BASE":       "#0B0D17",
    "BG_SURFACE":    "#13162A",
    "BG_ELEVATED":   "#1A1D36",
    "BG_HOVER":      "#222640",
    "BG_PRESSED":    "#1C1F38",
    "BORDER":        "#252842",
    "BORDER_FOCUS":  "#7C6EE8",
    "BORDER_SUBTLE": "#1E213A",
    "ACCENT":        "#7C6EE8",
    "ACCENT_HOVER":  "#9485F5",
    "ACCENT_MUTED":  "#2A2756",
    "ACCENT_LIGHT":  "#B4ABFF",
    "TEXT_PRIMARY":   "#E8EAFF",
    "TEXT_SECONDARY": "#8B8FA8",
    "TEXT_MUTED":     "#4A4D66",
    "TEXT_INVERSE":   "#0B0D17",
    "STATUS_NEW":     "#7C6EE8",
    "STATUS_LEARNING":"#F59E0B",
    "STATUS_LEARNED": "#4ADE80",
    "STATUS_REVIEW":  "#EF4444",
    "SUCCESS":        "#4ADE80",
    "WARNING":        "#F59E0B",
    "ERROR":          "#EF4444",
    "INFO":           "#60A5FA",
    "FAVORITE":       "#FF6B9D",
    "SCROLLBAR_BG":   "#13162A",
    "SCROLLBAR_HANDLE":"#252842",
    "SCROLLBAR_HOVER":"#7C6EE8",
}

LIGHT_THEME = {
    "BG_BASE":       "#F3F4F6", # gray-100
    "BG_SURFACE":    "#FFFFFF", # white
    "BG_ELEVATED":   "#F9FAFB", # gray-50
    "BG_HOVER":      "#E5E7EB", # gray-200
    "BG_PRESSED":    "#D1D5DB", # gray-300
    "BORDER":        "#E5E7EB", # gray-200
    "BORDER_FOCUS":  "#6366F1", # indigo-500
    "BORDER_SUBTLE": "#F3F4F6", # gray-100
    "ACCENT":        "#6366F1", # indigo-500
    "ACCENT_HOVER":  "#4F46E5", # indigo-600
    "ACCENT_MUTED":  "#EEF2FF", # indigo-50
    "ACCENT_LIGHT":  "#4F46E5", # indigo-600
    "TEXT_PRIMARY":   "#111827", # gray-900
    "TEXT_SECONDARY": "#4B5563", # gray-600
    "TEXT_MUTED":     "#9CA3AF", # gray-400
    "TEXT_INVERSE":   "#FFFFFF", # white
    "STATUS_NEW":     "#6366F1",
    "STATUS_LEARNING":"#D97706", # amber-600
    "STATUS_LEARNED": "#16A34A", # green-600
    "STATUS_REVIEW":  "#DC2626", # red-600
    "SUCCESS":        "#22C55E",
    "WARNING":        "#F59E0B",
    "ERROR":          "#EF4444",
    "INFO":           "#3B82F6",
    "FAVORITE":       "#EC4899",
    "SCROLLBAR_BG":   "#F9FAFB",
    "SCROLLBAR_HANDLE":"#D1D5DB",
    "SCROLLBAR_HOVER":"#9CA3AF",
}

_current_theme = "dark"


def set_theme(theme_name: str) -> None:
    global _current_theme
    _current_theme = theme_name
    if theme_name == "light":
        Colors.update(LIGHT_THEME)
    else:
        Colors.update(DARK_THEME)


# Uygulama açılışında karanlık tema ile başlat
set_theme("dark")


def STATUS_COLORS():
    return {
        "new":          Colors.STATUS_NEW,
        "learning":     Colors.STATUS_LEARNING,
        "learned":      Colors.STATUS_LEARNED,
        "needs_review": Colors.STATUS_REVIEW,
    }


# ─────────────────────────────────────────────────────────────────────────────
# QSS Stylesheet
# ─────────────────────────────────────────────────────────────────────────────

def get_stylesheet() -> str:
    return f"""
/* ── Globals ── */
* {{
    font-family: 'Inter', 'Segoe UI', 'SF Pro Display', 'Ubuntu', sans-serif;
    font-size: 14px;
    color: {Colors.TEXT_PRIMARY};
    border: none;
    outline: none;
}}

QMainWindow, QDialog {{
    background-color: {Colors.BG_BASE};
}}

QWidget {{
    background-color: transparent;
}}

QWidget#root {{
    background-color: {Colors.BG_BASE};
}}

/* ── Sidebar ── */
QWidget#sidebar {{
    background-color: {Colors.BG_SURFACE};
    border-right: 1px solid {Colors.BORDER_SUBTLE};
    min-width: 220px;
    max-width: 220px;
}}

QLabel#appTitle {{
    color: {Colors.TEXT_PRIMARY};
    font-size: 17px;
    font-weight: 700;
    letter-spacing: 1px;
}}

QLabel#appSubTitle {{
    color: {Colors.TEXT_MUTED};
    font-size: 11px;
    letter-spacing: 0.5px;
}}

/* ── Nav Buttons ── */
QPushButton#navBtn {{
    background-color: transparent;
    color: {Colors.TEXT_SECONDARY};
    border-radius: 10px;
    padding: 10px 14px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}}

QPushButton#navBtn:hover {{
    background-color: {Colors.BG_HOVER};
    color: {Colors.TEXT_PRIMARY};
}}

QPushButton#navBtn[active="true"] {{
    background-color: {Colors.ACCENT_MUTED};
    color: {Colors.ACCENT_LIGHT};
    font-weight: 600;
}}

/* ── Content Area ── */
QWidget#contentArea {{
    background-color: {Colors.BG_BASE};
}}

QStackedWidget {{
    background-color: {Colors.BG_BASE};
}}

/* ── Cards ── */
QFrame#card {{
    background-color: {Colors.BG_SURFACE};
    border-radius: 14px;
    border: 1px solid {Colors.BORDER_SUBTLE};
}}

QFrame#card:hover {{
    border: 1px solid {Colors.BORDER};
    background-color: {Colors.BG_ELEVATED};
}}

QFrame#statCard {{
    background-color: {Colors.BG_ELEVATED};
    border-radius: 12px;
    border: 1px solid {Colors.BORDER_SUBTLE};
}}

/* ── Input Fields ── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {Colors.BG_ELEVATED};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 14px;
    selection-background-color: {Colors.ACCENT_MUTED};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {Colors.BORDER_FOCUS};
    background-color: {Colors.BG_ELEVATED};
}}

QLineEdit::placeholder, QPlainTextEdit::placeholder {{
    color: {Colors.TEXT_MUTED};
}}

QLineEdit#searchInput {{
    background-color: {Colors.BG_ELEVATED};
    border: 1px solid {Colors.BORDER};
    border-radius: 24px;
    padding: 10px 18px 10px 44px;
    font-size: 14px;
}}

QLineEdit#searchInput:focus {{
    border: 1px solid {Colors.BORDER_FOCUS};
}}

/* ── ComboBox ── */
QComboBox {{
    background-color: {Colors.BG_ELEVATED};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 10px;
    padding: 8px 14px;
    font-size: 13px;
    min-width: 140px;
}}

QComboBox:hover {{
    border: 1px solid {Colors.ACCENT};
}}

QComboBox:focus {{
    border: 1px solid {Colors.BORDER_FOCUS};
}}

QComboBox::drop-down {{
    border: none;
    width: 30px;
}}

QComboBox::down-arrow {{
    image: none;
    border: none;
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {Colors.TEXT_SECONDARY};
}}

QComboBox QAbstractItemView {{
    background-color: {Colors.BG_ELEVATED};
    border: 1px solid {Colors.BORDER};
    border-radius: 10px;
    color: {Colors.TEXT_PRIMARY};
    selection-background-color: {Colors.ACCENT_MUTED};
    outline: none;
}}

/* ── Buttons ── */
QPushButton {{
    border-radius: 10px;
    padding: 9px 18px;
    font-size: 13px;
    font-weight: 500;
}}

QPushButton#primaryBtn {{
    background-color: {Colors.ACCENT};
    color: white;
    font-weight: 600;
    padding: 10px 22px;
}}

QPushButton#primaryBtn:hover {{
    background-color: {Colors.ACCENT_HOVER};
}}

QPushButton#primaryBtn:pressed {{
    background-color: {Colors.ACCENT_MUTED};
}}

QPushButton#primaryBtn:disabled {{
    background-color: {Colors.BG_ELEVATED};
    color: {Colors.TEXT_MUTED};
}}

QPushButton#secondaryBtn {{
    background-color: transparent;
    color: {Colors.TEXT_SECONDARY};
    border: 1px solid {Colors.BORDER};
}}

QPushButton#secondaryBtn:hover {{
    background-color: {Colors.BG_HOVER};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER_FOCUS};
}}

QPushButton#dangerBtn {{
    background-color: transparent;
    color: {Colors.ERROR};
    border: 1px solid {Colors.ERROR};
}}

QPushButton#dangerBtn:hover {{
    background-color: {Colors.ERROR};
    color: white;
}}

QPushButton#iconBtn {{
    background-color: transparent;
    color: {Colors.TEXT_MUTED};
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 16px;
}}

QPushButton#iconBtn:hover {{
    background-color: {Colors.BG_HOVER};
    color: {Colors.TEXT_PRIMARY};
}}

QPushButton#favoriteBtn {{
    background-color: transparent;
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 16px;
    color: {Colors.TEXT_MUTED};
}}

QPushButton#favoriteBtn[active="true"] {{
    color: {Colors.FAVORITE};
}}

QPushButton#favoriteBtn:hover {{
    background-color: {Colors.BG_HOVER};
}}

QPushButton#filterChip {{
    background-color: {Colors.BG_ELEVATED};
    color: {Colors.TEXT_SECONDARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 20px;
    padding: 5px 14px;
    font-size: 12px;
    font-weight: 500;
}}

QPushButton#filterChip[active="true"] {{
    background-color: {Colors.ACCENT_MUTED};
    color: {Colors.ACCENT_LIGHT};
    border: 1px solid {Colors.ACCENT};
}}

QPushButton#filterChip:hover {{
    border: 1px solid {Colors.ACCENT};
    color: {Colors.TEXT_PRIMARY};
}}

QPushButton#quickAddBtn {{
    background-color: {Colors.ACCENT};
    color: white;
    font-size: 20px;
    font-weight: 300;
    border-radius: 14px;
    padding: 0px;
    min-width: 44px;
    max-width: 44px;
    min-height: 44px;
    max-height: 44px;
}}

QPushButton#quickAddBtn:hover {{
    background-color: {Colors.ACCENT_HOVER};
}}

/* ── Labels ── */
QLabel#heading1 {{
    color: {Colors.TEXT_PRIMARY};
    font-size: 26px;
    font-weight: 700;
}}

QLabel#heading2 {{
    color: {Colors.TEXT_PRIMARY};
    font-size: 20px;
    font-weight: 600;
}}

QLabel#heading3 {{
    color: {Colors.TEXT_PRIMARY};
    font-size: 16px;
    font-weight: 600;
}}

QLabel#sectionTitle {{
    color: {Colors.TEXT_SECONDARY};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.2px;
}}

QLabel#bodyText {{
    color: {Colors.TEXT_PRIMARY};
    font-size: 14px;
    line-height: 1.6;
}}

QLabel#mutedText {{
    color: {Colors.TEXT_MUTED};
    font-size: 12px;
}}

QLabel#badge {{
    border-radius: 6px;
    padding: 3px 9px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.3px;
}}

/* ── Scroll Area ── */
QScrollArea {{
    background-color: transparent;
    border: none;
}}

QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}

QScrollBar:vertical {{
    background-color: transparent;
    width: 6px;
    border-radius: 3px;
}}

QScrollBar::handle:vertical {{
    background-color: {Colors.SCROLLBAR_HANDLE};
    border-radius: 3px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {Colors.SCROLLBAR_HOVER};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    height: 0px;
}}

/* ── Separator ── */
QFrame#separator {{
    background-color: {Colors.BORDER_SUBTLE};
    max-height: 1px;
    min-height: 1px;
}}

/* ── Dialog ── */
QDialog {{
    background-color: {Colors.BG_SURFACE};
    border-radius: 16px;
}}

/* ── Message Box ── */
QMessageBox {{
    background-color: {Colors.BG_ELEVATED};
}}

QMessageBox QPushButton {{
    background-color: {Colors.ACCENT};
    color: white;
    min-width: 80px;
    padding: 8px 16px;
}}

/* ── Tooltip ── */
QToolTip {{
    background-color: {Colors.BG_ELEVATED};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 12px;
}}

/* ── CheckBox ── */
QCheckBox {{
    color: {Colors.TEXT_SECONDARY};
    font-size: 13px;
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid {Colors.BORDER};
    background-color: {Colors.BG_ELEVATED};
}}

QCheckBox::indicator:checked {{
    background-color: {Colors.ACCENT};
    border: 1px solid {Colors.ACCENT};
}}
"""


def apply_theme(app) -> None:
    """QApplication'a o an aktif olan temayı uygular."""
    app.setStyleSheet(get_stylesheet())


def get_status_style(status: str) -> tuple[str, str]:
    """Status için (background_color, text_color) döndürür."""
    if _current_theme == "dark":
        color_map = {
            "new":          (Colors.ACCENT_MUTED, Colors.ACCENT_LIGHT),
            "learning":     ("#3A2E0F", "#F59E0B"),
            "learned":      ("#0F3020", "#4ADE80"),
            "needs_review": ("#3A0F0F", "#EF4444"),
        }
    else:
        color_map = {
            "new":          (Colors.ACCENT_MUTED, Colors.ACCENT_LIGHT),
            "learning":     ("#FEF3C7", "#D97706"), # amber-50, amber-600
            "learned":      ("#DCFCE7", "#16A34A"), # green-50, green-600
            "needs_review": ("#FEE2E2", "#DC2626"), # red-50, red-600
        }
    return color_map.get(status, (Colors.BG_ELEVATED, Colors.TEXT_SECONDARY))


def get_status_badge_style(status: str) -> str:
    bg, text = get_status_style(status)
    return f"background-color: {bg}; color: {text}; border-radius: 6px; padding: 3px 9px; font-size: 11px; font-weight: 600;"
