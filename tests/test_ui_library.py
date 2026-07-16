"""
Lexis — Tests: Kütüphane görünümü (sayfalama, etiket filtresi, boş durumlar)
"""

import pytest

pytest.importorskip("PyQt6.QtWidgets")

from lexis.domain.models import Word, WordStatus  # noqa: E402
from lexis.persistence.word_repository import WordRepository  # noqa: E402
from lexis.services.word_service import WordService  # noqa: E402
from lexis.ui.views.library_view import PAGE_SIZE, LibraryView  # noqa: E402


@pytest.fixture
def library(qtbot, word_service: WordService) -> LibraryView:
    """
    Bağımsız kütüphane görünümü.

    MainWindow'a bağlanmaz: oradaki "kelime ekle" akışı modal dialog.exec()
    çağırdığı için testi süresiz bloklardı.
    """
    view = LibraryView(word_service)
    view.resize(1200, 800)
    qtbot.addWidget(view)
    return view


def _make_words(n: int, prefix: str = "kelime") -> list[Word]:
    # term'ler sıralamada öngörülebilir olsun diye sıfır dolgulu.
    return [Word(term=f"{prefix}{i:03d}", language="en") for i in range(n)]


def _visible_terms(library) -> list[str]:
    return [c.word.term for c in library._word_cards[: library._word_cards_used]]


# ── Sayfalama ─────────────────────────────────────────────────────────────

def test_first_page_is_capped(library, repo: WordRepository):
    repo.create_many(_make_words(PAGE_SIZE + 25))
    library.refresh()

    assert library._word_cards_used == PAGE_SIZE
    assert library._load_more_btn.isVisibleTo(library)
    assert "25" in library._load_more_btn.text()


def test_load_more_appends_next_page(library, repo: WordRepository):
    repo.create_many(_make_words(PAGE_SIZE + 25))
    library.refresh()

    library._load_next_page()

    assert library._word_cards_used == PAGE_SIZE + 25
    assert not library._load_more_btn.isVisibleTo(library)


def test_load_more_hidden_when_all_fit(library, repo: WordRepository):
    repo.create_many(_make_words(5))
    library.refresh()

    assert library._word_cards_used == 5
    assert not library._load_more_btn.isVisibleTo(library)


def test_count_label_shows_progress_then_total(library, repo: WordRepository):
    repo.create_many(_make_words(PAGE_SIZE + 10))

    library.refresh()
    assert library._count_label.text() == f"{PAGE_SIZE} / {PAGE_SIZE + 10} kelime"

    library._load_next_page()
    assert library._count_label.text() == f"{PAGE_SIZE + 10} kelime"


def test_filter_change_resets_to_first_page(library, repo: WordRepository):
    repo.create_many(_make_words(PAGE_SIZE + 25))
    library.refresh()
    library._load_next_page()
    assert library._word_cards_used == PAGE_SIZE + 25

    library._search_input.setText("kelime00")
    library._apply_filters()

    assert library._word_cards_used == 10  # kelime000..kelime009


# ── Kart yeniden kullanımı ────────────────────────────────────────────────

def test_cards_are_reused_across_filters(library, repo: WordRepository):
    """
    Her filtrede kartlar yok edilip yeniden yaratılmamalı; havuz büyümemeli.
    """
    repo.create_many(_make_words(10))
    library.refresh()
    pool_size = len(library._word_cards)

    library._search_input.setText("kelime00")
    library._apply_filters()
    library._search_input.clear()
    library._apply_filters()

    assert len(library._word_cards) == pool_size
    assert library._word_cards_used == 10


def test_surplus_cards_are_hidden_not_shown(library, repo: WordRepository):
    repo.create_many(_make_words(10))
    library.refresh()

    library._search_input.setText("kelime001")
    library._apply_filters()

    assert library._word_cards_used == 1
    hidden = library._word_cards[1:]
    assert all(not c.isVisible() for c in hidden)


def test_card_rebinds_to_new_word(library, repo: WordRepository):
    repo.create(Word(term="ilk", language="en", definition_short="birinci"))
    library.refresh()
    card = library._word_cards[0]

    repo.delete_all()
    repo.create(Word(term="ikinci", language="de", definition_short="ikinci tanım"))
    library.refresh()

    assert library._word_cards[0] is card  # aynı widget
    assert card.word.term == "ikinci"
    assert card._lang_badge.text() == "DE"
    assert "ikinci tanım" in card._preview_label.text()


# ── Etiket filtresi ───────────────────────────────────────────────────────

def test_tag_filter_lists_existing_tags(library, repo: WordRepository):
    repo.create(Word(term="bir", language="en", tags=["fiil", "temel"]))
    repo.create(Word(term="iki", language="en", tags=["temel"]))
    library.refresh()

    tags = [library._tag_combo.itemData(i) for i in range(library._tag_combo.count())]
    assert tags == ["", "fiil", "temel"]  # ilki "Tüm Etiketler"


def test_tag_filter_narrows_results(library, repo: WordRepository):
    repo.create(Word(term="bir", language="en", tags=["fiil"]))
    repo.create(Word(term="iki", language="en", tags=["isim"]))
    library.refresh()

    library.filter_by_tag("fiil")

    assert _visible_terms(library) == ["bir"]


def test_clicking_card_tag_filters(library, repo: WordRepository):
    """Karttaki etikete tıklamak o etikete filtrelemeli."""
    repo.create(Word(term="bir", language="en", tags=["fiil"]))
    repo.create(Word(term="iki", language="en", tags=["isim"]))
    library.refresh()

    card = library._word_cards[0]
    card.tag_clicked.emit("fiil")

    assert _visible_terms(library) == ["bir"]


def test_tag_selection_survives_refresh(library, repo: WordRepository):
    repo.create(Word(term="bir", language="en", tags=["fiil"]))
    repo.create(Word(term="iki", language="en", tags=["isim"]))
    library.refresh()
    library.filter_by_tag("fiil")

    library.refresh()

    assert library._tag_combo.currentData() == "fiil"
    assert _visible_terms(library) == ["bir"]


# ── Boş durumlar ──────────────────────────────────────────────────────────

def test_empty_library_offers_to_add(library):
    library.refresh()

    assert library._empty_widget.isVisibleTo(library)
    assert "henüz boş" in library._empty_label.text()
    assert "Ekle" in library._empty_action_btn.text()


def test_empty_library_action_opens_add_dialog(library, qtbot):
    library.refresh()

    with qtbot.waitSignal(library.open_add_dialog, timeout=500):
        library._empty_action_btn.click()


def test_no_filter_match_offers_to_clear(library, repo: WordRepository):
    """Filtre eşleşmemesi, boş kütüphaneden farklı bir durumdur."""
    repo.create(Word(term="ephemeral", language="en"))
    library.refresh()

    library._search_input.setText("bulunamayacak-kelime")
    library._apply_filters()

    assert library._empty_widget.isVisibleTo(library)
    assert "uyan kelime yok" in library._empty_label.text()
    assert library._empty_action_btn.text() == "Filtreleri Temizle"


def test_clear_filters_restores_results(library, repo: WordRepository):
    repo.create(Word(term="ephemeral", language="en", status=WordStatus.LEARNED))
    library.refresh()
    library._search_input.setText("yok")
    library._apply_filters()
    assert library._word_cards_used == 0

    library._empty_action_btn.click()  # "Filtreleri Temizle"

    assert library._search_input.text() == ""
    assert _visible_terms(library) == ["ephemeral"]


# ── Duyarlı ızgara ────────────────────────────────────────────────────────

def test_column_count_follows_width(library, repo: WordRepository, qtbot):
    """Sütun sayısı sabit 3 değil, pencere genişliğine uymalı."""
    repo.create_many(_make_words(8))
    library.show()
    qtbot.waitExposed(library)
    library.refresh()

    def columns_at(width: int) -> int:
        library.resize(width, 800)
        qtbot.waitUntil(lambda: library._scroll.viewport().width() > 0, timeout=1000)
        # resize'ın scroll viewport'a yayılması için bir layout geçişi gerekir.
        qtbot.wait(10)
        return library._columns()

    narrow = columns_at(700)
    wide = columns_at(1800)

    assert narrow >= 1
    assert narrow < wide
    assert wide <= 4  # MAX_COLUMNS
