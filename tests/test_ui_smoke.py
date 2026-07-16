"""
Lexis — Tests: UI duman testleri (headless)

QT_QPA_PLATFORM=offscreen altında çalışır. Amaç piksel doğrulamak değil;
pencerenin kurulduğunu, ekranlar arasında gezinilebildiğini ve tema
değişiminin durumu koruduğunu doğrulamaktır.
"""

import pytest

pytest.importorskip("PyQt6.QtWidgets")

from PyQt6.QtWidgets import QApplication, QLabel  # noqa: E402

from lexis.domain.models import Word  # noqa: E402
from lexis.persistence.word_repository import WordRepository  # noqa: E402
from lexis.ui.theme import Colors, apply_theme, get_stylesheet, set_theme  # noqa: E402
from lexis.ui.widgets.common import StatusBadge  # noqa: E402
from lexis.ui.windows.main_window import (  # noqa: E402
    PAGE_DASHBOARD,
    PAGE_LIBRARY,
    PAGE_SETTINGS,
)


@pytest.fixture(autouse=True)
def _restore_dark_theme():
    """Tema değiştiren testler diğerlerini etkilemesin."""
    yield
    set_theme("dark")


def test_main_window_builds(window):
    assert window.windowTitle().startswith("Lexis")


def test_navigation_between_pages(window):
    for page in (PAGE_LIBRARY, PAGE_SETTINGS, PAGE_DASHBOARD):
        window._navigate_to(page)
        assert window.current_page() == page


def test_theme_switch_keeps_window_alive(window):
    """
    Tema değişimi pencereyi yeniden kurmamalı.

    Eskiden renkler widget'lara inşa anında gömüldüğü için pencere yıkılıp
    yeniden kuruluyordu; bu test o hack'in geri gelmesini engeller.
    """
    window_id = id(window)
    search_field = window._library._search_input
    search_field.setText("ephemeral")

    set_theme("light")
    apply_theme(QApplication.instance())

    assert id(window) == window_id
    assert search_field.text() == "ephemeral"  # kullanıcının girdisi korundu


def test_stylesheet_changes_with_theme():
    set_theme("dark")
    dark = get_stylesheet()
    dark_bg = Colors.BG_BASE

    set_theme("light")
    light = get_stylesheet()

    assert dark != light
    assert Colors.BG_BASE != dark_bg
    assert Colors.BG_BASE in light


def test_stylesheet_has_no_unresolved_placeholders():
    """QSS f-string'i kaçmış süslü parantez bırakmamalı."""
    for theme in ("dark", "light"):
        set_theme(theme)
        qss = get_stylesheet()
        assert "{Colors." not in qss
        assert "None" not in qss.split("QToolTip")[0]


def test_status_badge_carries_status_property(qtbot):
    badge = StatusBadge("learned", "Öğrendim")
    qtbot.addWidget(badge)
    assert badge.property("status") == "learned"

    badge.set_status("new", "Yeni")
    assert badge.property("status") == "new"
    assert badge.text() == "Yeni"


def test_library_renders_word_cards(window, repo: WordRepository, sample_word: Word):
    repo.create(sample_word)
    window._library.refresh()

    assert [c.word_id for c in window._library._word_cards] == [sample_word.id]


def test_word_detail_loads(window, repo: WordRepository, sample_word: Word):
    repo.create(sample_word)
    window._show_word_detail(sample_word.id)

    assert window.current_page() == 2
    assert window._detail._term_label.text() == "ephemeral"


def test_practice_view_shows_empty_state_without_words(window):
    window._practice.start_session()

    # Kuyruk boşken kart gizlenir ve bilgilendirme metni gösterilir.
    assert not window._practice._card.isVisibleTo(window._practice)
    assert "Tekrar edilecek kelime yok" in window._practice._done_label.text()


def test_practice_session_shows_first_card(window, repo: WordRepository, sample_word: Word):
    repo.create(sample_word)
    window._practice.start_session()

    assert window._practice._term_label.text() == "ephemeral"
    assert not window._practice._answer_widget.isVisible()  # cevap gizli başlar


def test_settings_stats_refresh(window, repo: WordRepository, sample_word: Word):
    """Ayarlar ekranı, dönüldüğünde güncel sayıyı göstermeli."""
    window._navigate_to(PAGE_SETTINGS)
    assert "Toplam kelime: 0" in window._settings._stats_label.text()

    repo.create(sample_word)
    window._navigate_to(PAGE_DASHBOARD)
    window._navigate_to(PAGE_SETTINGS)

    assert "Toplam kelime: 1" in window._settings._stats_label.text()


def test_labels_use_object_names_not_inline_colors(window):
    """
    Renk taşıyan hiçbir widget inline stil kullanmamalı; aksi hâlde tema
    değişiminde yeniden boyanmaz.
    """
    offenders = [
        lbl.objectName() or lbl.text()[:30]
        for lbl in window.findChildren(QLabel)
        if "color:" in lbl.styleSheet()
    ]
    assert offenders == []
