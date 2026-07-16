"""
Lexis — Design System & Theme

Tüm renk, tipografi ve QSS stylesheet tanımları bu modülde merkezileştirilmiştir.
"""

from __future__ import annotations

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QWidget

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

    # Birincil aksiyon butonu (tema bazlı: koyu temada beyaz, açıkta vurgu rengi)
    BTN_BG: str
    BTN_BG_HOVER: str
    BTN_TEXT: str

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

# Minimalist, nötr (navy tonu olmayan) yakın-siyah karanlık tema.
# Tek vurgu rengi (violet), saç teli (hairline) kenarlıklar, yumuşatılmış durum tonları.
DARK_THEME = {
    "BG_BASE":       "#000000",  # saf siyah
    "BG_SURFACE":    "#0B0B0B",  # sidebar / kartlar (siyahtan ince ayrışma)
    "BG_ELEVATED":   "#151515",  # inputlar / hover yüzeyleri
    "BG_HOVER":      "#1E1E1E",
    "BG_PRESSED":    "#181818",
    "BORDER":        "#2A2A2A",
    "BORDER_FOCUS":  "#6E6E6E",
    "BORDER_SUBTLE": "#191919",
    "ACCENT":        "#FFFFFF",   # monokrom: vurgular beyaz/gri
    "ACCENT_HOVER":  "#D8D8D8",
    "ACCENT_MUTED":  "#1C1C1C",   # aktif/badge için nötr gri yüzey
    "ACCENT_LIGHT":  "#FFFFFF",   # aktif metin / logo / rozet metni
    "BTN_BG":        "#FFFFFF",   # beyaz birincil buton
    "BTN_BG_HOVER":  "#E2E2E2",
    "BTN_TEXT":      "#000000",
    "TEXT_PRIMARY":   "#ECECEE",
    "TEXT_SECONDARY": "#9A9AA4",
    "TEXT_MUTED":     "#5A5A62",
    "TEXT_INVERSE":   "#000000",
    "STATUS_NEW":     "#C6C6CC",
    "STATUS_LEARNING":"#E8B25E",
    "STATUS_LEARNED": "#5FD08A",
    "STATUS_REVIEW":  "#F07A75",
    "SUCCESS":        "#5FD08A",
    "WARNING":        "#E8B25E",
    "ERROR":          "#F07A75",
    "INFO":           "#6FA8FF",
    "FAVORITE":       "#FF8FB0",
    "SCROLLBAR_BG":   "#111113",
    "SCROLLBAR_HANDLE":"#2D2D32",
    "SCROLLBAR_HOVER":"#45454D",
}

# Temiz, beyaz tabanlı minimalist aydınlık tema.
LIGHT_THEME = {
    "BG_BASE":       "#F7F7F8",
    "BG_SURFACE":    "#FFFFFF",
    "BG_ELEVATED":   "#FFFFFF",
    "BG_HOVER":      "#F0F0F2",
    "BG_PRESSED":    "#E7E7EA",
    "BORDER":        "#E6E6E9",
    "BORDER_FOCUS":  "#6D5EF0",
    "BORDER_SUBTLE": "#EEEEF0",
    "ACCENT":        "#6D5EF0",
    "ACCENT_HOVER":  "#5A49E8",
    "ACCENT_MUTED":  "#EFEDFD",
    "ACCENT_LIGHT":  "#5A49E8",
    "BTN_BG":        "#6D5EF0",  # açık temada birincil buton vurgu rengi
    "BTN_BG_HOVER":  "#5A49E8",
    "BTN_TEXT":      "#FFFFFF",
    "TEXT_PRIMARY":   "#18181B",
    "TEXT_SECONDARY": "#55555F",
    "TEXT_MUTED":     "#9B9BA6",
    "TEXT_INVERSE":   "#FFFFFF",
    "STATUS_NEW":     "#6D5EF0",
    "STATUS_LEARNING":"#C8821C",
    "STATUS_LEARNED": "#1B9E55",
    "STATUS_REVIEW":  "#DD5752",
    "SUCCESS":        "#1B9E55",
    "WARNING":        "#C8821C",
    "ERROR":          "#DD5752",
    "INFO":           "#3B82F6",
    "FAVORITE":       "#E85C92",
    "SCROLLBAR_BG":   "#F0F0F2",
    "SCROLLBAR_HANDLE":"#D7D7DC",
    "SCROLLBAR_HOVER":"#BEBEC6",
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


STATUS_KEYS = ("new", "learning", "learned", "needs_review")


def _grade_button_rules() -> str:
    """
    Çalışma modundaki değerlendirme butonlarının renklerini üretir.

    Renkler domain'deki ReviewGrade.color'dan gelir; tek kaynak orası kalsın
    diye burada tekrar tanımlanmaz.
    """
    from lexis.domain.models import ReviewGrade

    return "\n".join(
        f'QPushButton#gradeBtn[grade="{g.name.lower()}"] {{ background-color: {g.color}; }}'
        for g in ReviewGrade
    )


def _badge_status_rules() -> str:
    """
    Durum rozetlerinin renklerini QSS kuralı olarak üretir.

    Renkler widget'a inline gömülmek yerine global stylesheet'e girdiği için
    tema değişiminde pencere yeniden kurulmadan yeniden boyanabilirler.
    """
    return "\n".join(
        f'QLabel#badge[status="{status}"] {{ background-color: {bg}; color: {text}; }}'
        for status, (bg, text) in ((s, get_status_style(s)) for s in STATUS_KEYS)
    )


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
    color: {Colors.ACCENT_LIGHT};
    font-size: 22px;
    font-weight: 800;
    letter-spacing: 0.5px;
}}

QLabel#appTagline {{
    color: {Colors.TEXT_MUTED};
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.5px;
}}

/* Sidebar bölüm etiketi ("MENÜ") */
QLabel#navSectionLabel {{
    color: {Colors.TEXT_MUTED};
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.5px;
    padding: 8px 8px 4px 8px;
}}

/* Yükleme katmanı mesajı */
QLabel#overlayMessage {{
    color: {Colors.TEXT_SECONDARY};
    font-size: 13px;
    font-weight: 500;
    background: transparent;
}}

/* Etiket rozeti (#tag) */
QLabel#tagBadgeText {{
    color: {Colors.ACCENT_LIGHT};
    font-size: 11px;
    font-weight: 600;
    background: transparent;
}}

QWidget#tagBadge {{
    background-color: {Colors.ACCENT_MUTED};
    border-radius: 8px;
    border: 1px solid {Colors.ACCENT};
}}

QPushButton#tagRemoveBtn {{
    background: transparent;
    color: {Colors.TEXT_MUTED};
    border: none;
    border-radius: 3px;
    font-size: 13px;
    font-weight: 700;
    padding: 0px;
}}

QPushButton#tagRemoveBtn:hover {{
    color: {Colors.ERROR};
    background: rgba(239, 68, 68, 0.15);
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
    border-left: 2px solid transparent;
    padding: 11px 14px 11px 14px;
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
    border-left: 2px solid {Colors.ACCENT};
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
    border-radius: 16px;
    border: 1px solid {Colors.BORDER_SUBTLE};
}}

QFrame#card:hover {{
    border: 1px solid {Colors.BORDER};
    background-color: {Colors.BG_ELEVATED};
}}

QFrame#statCard {{
    background-color: {Colors.BG_SURFACE};
    border-radius: 16px;
    border: 1px solid {Colors.BORDER_SUBTLE};
}}

/* ── Input Fields ── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {Colors.BG_ELEVATED};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 12px;
    padding: 11px 15px;
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
    border-radius: 12px;
    padding: 9px 18px;
    font-size: 13px;
    font-weight: 500;
}}

QPushButton#primaryBtn {{
    background-color: {Colors.BTN_BG};
    color: {Colors.BTN_TEXT};
    border: none;
    font-weight: 600;
    padding: 10px 22px;
}}

QPushButton#primaryBtn:hover {{
    background-color: {Colors.BTN_BG_HOVER};
}}

QPushButton#primaryBtn:pressed {{
    background-color: {Colors.BTN_BG_HOVER};
}}

QPushButton#primaryBtn:disabled {{
    background-color: {Colors.BG_ELEVATED};
    color: {Colors.TEXT_MUTED};
    border: none;
}}

QPushButton#secondaryBtn {{
    background-color: transparent;
    color: {Colors.TEXT_SECONDARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 17px;
    padding: 6px 16px;
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
    border-radius: 17px;
    padding: 6px 16px;
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

/* Detay ekranındaki büyük favori butonu */
QPushButton#favoriteBtn[size="large"] {{
    font-size: 22px;
    border-radius: 10px;
}}

/* ── Kelime detay ekranı ── */
QWidget#detailNavbar {{
    background: {Colors.BG_SURFACE};
    border-bottom: 1px solid {Colors.BORDER_SUBTLE};
}}

QLabel#detailTerm {{
    color: {Colors.TEXT_PRIMARY};
    font-size: 42px;
    font-weight: 800;
    letter-spacing: -0.5px;
}}

QLabel#detailShortDef {{
    color: {Colors.TEXT_SECONDARY};
    font-size: 15px;
    font-style: italic;
}}

QLabel#detailDefinition {{
    color: {Colors.TEXT_PRIMARY};
    font-size: 15px;
}}

QLabel#detailUsage {{
    color: {Colors.TEXT_SECONDARY};
    font-size: 14px;
}}

QLabel#detailLangBadge {{
    background: {Colors.BG_ELEVATED};
    color: {Colors.TEXT_SECONDARY};
    border-radius: 5px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 600;
}}

QLabel#detailPosBadge {{
    color: {Colors.TEXT_MUTED};
    font-size: 12px;
    font-style: italic;
    padding: 3px 6px;
}}

/* Örnek cümle satırları */
QLabel#exampleNumber {{
    color: {Colors.ACCENT};
    font-weight: 700;
    font-size: 14px;
    min-width: 20px;
    background: transparent;
    border: none;
}}

QLabel#exampleForeign {{
    color: {Colors.TEXT_PRIMARY};
    font-size: 14px;
    font-weight: 500;
}}

QLabel#exampleTranslation {{
    color: {Colors.TEXT_MUTED};
    font-size: 13px;
    font-style: italic;
}}

QPushButton#filterChip {{
    background-color: {Colors.BG_ELEVATED};
    color: {Colors.TEXT_SECONDARY};
    border: 1px solid {Colors.BORDER};
    border-radius: 14px;
    padding: 4px 14px;
    font-size: 13px;
    font-weight: 500;
    min-height: 28px;
    max-height: 28px;
}}

QPushButton#filterChip[active="true"] {{
    background-color: {Colors.ACCENT_MUTED};
    color: {Colors.ACCENT_LIGHT};
    border: 1px solid {Colors.ACCENT};
    border-radius: 14px;
}}

QPushButton#filterChip:hover {{
    border: 1px solid {Colors.ACCENT};
    color: {Colors.TEXT_PRIMARY};
    border-radius: 14px;
}}

QPushButton#quickAddBtn {{
    background-color: {Colors.BTN_BG};
    color: {Colors.BTN_TEXT};
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
    background-color: {Colors.BTN_BG_HOVER};
}}

/* ── Labels ── */
QLabel#heading1 {{
    color: {Colors.TEXT_PRIMARY};
    font-size: 26px;
    font-weight: 700;
}}

/* Sayfa başlığı (topbar içindeki büyük başlık) */
QLabel#pageTitle {{
    color: {Colors.TEXT_PRIMARY};
    font-size: 22px;
    font-weight: 700;
}}

/* Kart / bölüm başlığı */
QLabel#cardTitle {{
    color: {Colors.TEXT_PRIMARY};
    font-size: 14px;
    font-weight: 600;
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

/* Açıklama metni (ayar bölümlerindeki alt yazılar) */
QLabel#descText {{
    color: {Colors.TEXT_SECONDARY};
    font-size: 13px;
}}

/* Dosya yolu gibi teknik metinler */
QLabel#monoText {{
    color: {Colors.TEXT_SECONDARY};
    font-size: 12px;
    font-family: monospace;
}}

QLabel#badge {{
    border-radius: 6px;
    padding: 3px 9px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.3px;
}}

{_badge_status_rules()}

/* ── Topbar (kütüphane / ayarlar / çalışma başlıkları) ── */
QWidget#topbar {{
    background-color: {Colors.BG_BASE};
}}

/* ── İçerik yüzeyi ── */
QWidget#contentSurface {{
    background-color: {Colors.BG_BASE};
}}

/* ── Arama ikonu ── */
QLabel#searchIcon {{
    color: {Colors.TEXT_MUTED};
    font-size: 16px;
    background: transparent;
}}

/* ── Sayaç etiketi (ör. "12 kelime") ── */
QLabel#countLabel {{
    color: {Colors.TEXT_MUTED};
    font-size: 12px;
}}

/* ── Chip (etiket / meta rozet) ── */
QLabel#chip {{
    background-color: {Colors.BG_ELEVATED};
    color: {Colors.TEXT_SECONDARY};
    border-radius: 8px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: 500;
}}

QLabel#chip[variant="accent"] {{
    background-color: {Colors.ACCENT_MUTED};
    color: {Colors.ACCENT};
}}

/* Zıt anlamlılar için uyarı tonu */
QLabel#chip[variant="danger"] {{
    background-color: {get_status_style("needs_review")[0]};
    color: {get_status_style("needs_review")[1]};
}}

/* ── Durum metni (ayarlar ekranındaki geri bildirimler) ── */
QLabel#statusText {{
    color: {Colors.TEXT_MUTED};
    font-size: 12px;
}}

QLabel#statusText[level="success"] {{
    color: {Colors.SUCCESS};
}}

QLabel#statusText[level="error"] {{
    color: {Colors.ERROR};
}}

QLabel#statusText[level="info"] {{
    color: {Colors.INFO};
}}

QLabel#statusText[level="warning"] {{
    color: {Colors.WARNING};
}}

/* ── Çalışma (flashcard) modu ── */
QLabel#practiceProgress {{
    color: {Colors.TEXT_SECONDARY};
    font-size: 13px;
    font-weight: 600;
}}

QLabel#practiceTerm {{
    color: {Colors.TEXT_PRIMARY};
    font-size: 34px;
    font-weight: 800;
}}

QLabel#practiceMeta {{
    color: {Colors.TEXT_MUTED};
    font-size: 13px;
    font-weight: 500;
}}

QLabel#practiceDefinition {{
    color: {Colors.TEXT_PRIMARY};
    font-size: 16px;
}}

QLabel#practiceExamples {{
    color: {Colors.TEXT_SECONDARY};
    font-size: 13px;
}}

QLabel#practiceDone {{
    color: {Colors.TEXT_PRIMARY};
    font-size: 18px;
}}

/* Değerlendirme butonları (Tekrar / Zor / İyi / Kolay) */
QPushButton#gradeBtn {{
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: 700;
    font-size: 14px;
}}

{_grade_button_rules()}

/* ── Kütüphane filtre çubuğu ── */
QWidget#filterBar {{
    background: {Colors.BG_SURFACE};
    border-bottom: 1px solid {Colors.BORDER_SUBTLE};
}}

QWidget#searchContainer {{
    background: {Colors.BG_ELEVATED};
    border: none;
    border-radius: 10px;
}}

QLineEdit#searchField {{
    background: transparent;
    border: none;
    color: {Colors.TEXT_PRIMARY};
    font-size: 14px;
    padding: 9px 0;
}}

/* ── Dashboard ── */
QLabel#greeting {{
    color: {Colors.TEXT_PRIMARY};
    font-size: 26px;
    font-weight: 700;
}}

QLabel#dateLabel {{
    color: {Colors.TEXT_MUTED};
    font-size: 13px;
}}

QLabel#statValue {{
    font-size: 28px;
    font-weight: 700;
    color: {Colors.ACCENT};
}}

/* İstatistik kartının vurgu tonu (veriye göre seçilir) */
QLabel#statValue[tone="accent"]   {{ color: {Colors.ACCENT_LIGHT}; }}
QLabel#statValue[tone="review"]   {{ color: {Colors.STATUS_REVIEW}; }}
QLabel#statValue[tone="warning"]  {{ color: {Colors.WARNING}; }}
QLabel#statValue[tone="success"]  {{ color: {Colors.SUCCESS}; }}
QLabel#statValue[tone="favorite"] {{ color: {Colors.FAVORITE}; }}
QLabel#statValue[tone="streak"]   {{ color: {Colors.STATUS_LEARNING}; }}

QLabel#statLabel {{
    color: {Colors.TEXT_MUTED};
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.5px;
}}

/* Boş durum metni */
QLabel#emptyState {{
    color: {Colors.TEXT_MUTED};
    font-size: 14px;
    padding: 60px 0;
}}

/* ── Word Card ── */
QLabel#cardTerm {{
    color: {Colors.TEXT_PRIMARY};
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -0.2px;
}}

QLabel#langBadge {{
    background-color: {Colors.BG_ELEVATED};
    color: {Colors.TEXT_MUTED};
    border-radius: 5px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.5px;
}}

QLabel#posBadge {{
    color: {Colors.TEXT_MUTED};
    font-size: 11px;
    font-style: italic;
}}

QLabel#cardPreview {{
    color: {Colors.TEXT_SECONDARY};
    font-size: 13px;
}}

QLabel#cardTag {{
    color: {Colors.ACCENT};
    font-size: 10px;
    font-weight: 500;
}}

/* ── Toast bildirimleri ── */
QFrame#toast {{
    background-color: {Colors.BG_ELEVATED};
    border: 1px solid {Colors.BORDER};
    border-left: 3px solid {Colors.BORDER_FOCUS};
    border-radius: 10px;
}}

QFrame#toast[level="success"] {{
    border-left: 3px solid {Colors.SUCCESS};
}}

QFrame#toast[level="error"] {{
    border-left: 3px solid {Colors.ERROR};
}}

QFrame#toast[level="info"] {{
    border-left: 3px solid {Colors.INFO};
}}

QLabel#toastText {{
    color: {Colors.TEXT_PRIMARY};
    font-size: 13px;
    background: transparent;
}}

QPushButton#toastAction {{
    background: transparent;
    color: {Colors.ACCENT_LIGHT};
    border: none;
    padding: 4px 8px;
    font-size: 13px;
    font-weight: 700;
}}

QPushButton#toastAction:hover {{
    color: {Colors.ACCENT};
    background: {Colors.BG_HOVER};
    border-radius: 6px;
}}

/* ── Context Menu ── */
QMenu {{
    background-color: {Colors.BG_SURFACE};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER_SUBTLE};
    border-radius: 6px;
    padding: 4px;
}}

QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {Colors.ERROR};
    color: white;
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

QFrame#separator[spaced="true"] {{
    margin-bottom: 8px;
}}

/* ── Dialog ── */
QDialog {{
    background-color: {Colors.BG_SURFACE};
    border-radius: 16px;
}}

QWidget#dialogHeader {{
    background-color: {Colors.BG_ELEVATED};
    border-bottom: 1px solid {Colors.BORDER_SUBTLE};
    border-top-left-radius: 16px;
    border-top-right-radius: 16px;
}}

QWidget#dialogFooter {{
    background-color: {Colors.BG_ELEVATED};
    border-top: 1px solid {Colors.BORDER_SUBTLE};
    border-bottom-left-radius: 16px;
    border-bottom-right-radius: 16px;
}}

QWidget#dialogSurface {{
    background-color: {Colors.BG_SURFACE};
}}

QLabel#dialogTitle {{
    color: {Colors.TEXT_PRIMARY};
    font-size: 16px;
    font-weight: 700;
}}

QPushButton#closeBtn {{
    background: transparent;
    color: {Colors.TEXT_MUTED};
    font-size: 20px;
    border-radius: 8px;
}}

QPushButton#closeBtn:hover {{
    background: {Colors.BG_HOVER};
    color: {Colors.TEXT_PRIMARY};
}}

/* ── Message Box ── */
QMessageBox {{
    background-color: {Colors.BG_ELEVATED};
}}

QMessageBox QPushButton {{
    background-color: {Colors.BTN_BG};
    color: {Colors.BTN_TEXT};
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

    # Rich text (<a href>) bağlantıları QSS color'ını almaz; renkleri palette'in
    # Link rolünden okunur.
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Link, QColor(Colors.ACCENT_LIGHT))
    palette.setColor(QPalette.ColorRole.LinkVisited, QColor(Colors.ACCENT))
    app.setPalette(palette)


def repolish(widget) -> None:
    """
    Widget'ı ve tüm alt widget'larını yeniden boyar.

    Qt, dinamik property'ler ([active="true"] gibi) değiştiğinde ya da global
    stylesheet yenilendiğinde otomatik yeniden boyamaz; stil nesnesinin
    yeniden atanması (unpolish/polish) gerekir.
    """
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()

    for child in widget.findChildren(QWidget):
        child_style = child.style()
        child_style.unpolish(child)
        child_style.polish(child)
        child.update()


def get_status_style(status: str) -> tuple[str, str]:
    """Status için (background_color, text_color) döndürür."""
    if _current_theme == "dark":
        color_map = {
            "new":          (Colors.ACCENT_MUTED, Colors.ACCENT_LIGHT),
            "learning":     ("#2A2210", Colors.STATUS_LEARNING),
            "learned":      ("#13271C", Colors.STATUS_LEARNED),
            "needs_review": ("#2C1716", Colors.STATUS_REVIEW),
        }
    else:
        color_map = {
            "new":          (Colors.ACCENT_MUTED, Colors.ACCENT_LIGHT),
            "learning":     ("#FBF1DC", Colors.STATUS_LEARNING),
            "learned":      ("#E0F3E8", Colors.STATUS_LEARNED),
            "needs_review": ("#FBE7E6", Colors.STATUS_REVIEW),
        }
    return color_map.get(status, (Colors.BG_ELEVATED, Colors.TEXT_SECONDARY))


def get_status_badge_style(status: str) -> str:
    bg, text = get_status_style(status)
    return f"background-color: {bg}; color: {text}; border-radius: 6px; padding: 3px 9px; font-size: 11px; font-weight: 600;"
