"""
Lexis — Tests: Çalışma oturumu kuyruğu ve elle düzenleme diyaloğu
"""

import pytest

pytest.importorskip("PyQt6.QtWidgets")

from lexis.domain.models import ReviewGrade, Word  # noqa: E402
from lexis.persistence.word_repository import WordRepository  # noqa: E402
from lexis.services.word_service import WordService  # noqa: E402
from lexis.ui.views.practice_view import PracticeView  # noqa: E402
from lexis.ui.widgets.edit_word_dialog import EditWordDialog  # noqa: E402


@pytest.fixture
def practice(qtbot, word_service: WordService) -> PracticeView:
    view = PracticeView(word_service)
    qtbot.addWidget(view)
    return view


def _reveal_and_grade(practice: PracticeView, grade: ReviewGrade) -> None:
    practice._reveal()
    practice._grade(grade)


# ── Oturum içi tekrar kuyruğu ─────────────────────────────────────────────

def test_again_requeues_card_in_same_session(practice, repo: WordRepository):
    """
    'Tekrar' verilen kart oturumu terk etmeden yeniden sorulmalı.
    Eskiden bir gün sonraya atılıp oturumda bir daha görünmüyordu.
    """
    repo.create_many([Word(term="bir", language="en"), Word(term="iki", language="en")])
    practice.start_session()

    first = practice._term_label.text()
    _reveal_and_grade(practice, ReviewGrade.AGAIN)

    assert practice._term_label.text() != first  # sıradaki karta geçti
    _reveal_and_grade(practice, ReviewGrade.GOOD)

    # 'Tekrar' verilen kart kuyruğun sonunda geri geldi.
    assert practice._term_label.text() == first


def test_good_does_not_requeue(practice, repo: WordRepository):
    repo.create(Word(term="tek", language="en"))
    practice.start_session()
    assert len(practice._queue) == 1

    _reveal_and_grade(practice, ReviewGrade.GOOD)

    assert len(practice._queue) == 1  # kuyruğa geri eklenmedi
    assert "Oturum tamamlandı" in practice._done_label.text()


def test_requeued_card_counts_once(practice, repo: WordRepository):
    """Aynı kelime iki kez sorulsa da 'çalışıldı' sayısı bir artmalı."""
    repo.create(Word(term="tek", language="en"))
    practice.start_session()

    _reveal_and_grade(practice, ReviewGrade.AGAIN)  # kuyruğa geri döner
    _reveal_and_grade(practice, ReviewGrade.GOOD)   # ikinci kez

    assert practice._reviewed == 1
    assert "1 kelime çalışıldı" in practice._done_label.text()


def test_progress_reflects_growing_queue(practice, repo: WordRepository):
    repo.create(Word(term="tek", language="en"))
    practice.start_session()
    assert practice._progress_label.text() == "1 / 1"

    _reveal_and_grade(practice, ReviewGrade.AGAIN)

    assert practice._progress_label.text() == "2 / 2"  # kart yeniden kuyrukta


def test_grade_before_reveal_is_ignored(practice, repo: WordRepository):
    """Cevap açılmadan değerlendirme kaydedilmemeli."""
    repo.create(Word(term="tek", language="en"))
    practice.start_session()

    practice._grade(ReviewGrade.GOOD)

    assert practice._reviewed == 0


# ── Oturum uzunluğu ───────────────────────────────────────────────────────

def test_session_length_limits_queue(practice, repo: WordRepository):
    repo.create_many([Word(term=f"k{i}", language="en") for i in range(30)])

    practice._length_combo.setCurrentIndex(0)  # 10 kelime → oturumu yeniden başlatır

    assert practice._session_limit() == 10
    assert len(practice._queue) == 10


def test_session_length_all_loads_everything(practice, repo: WordRepository):
    repo.create_many([Word(term=f"k{i}", language="en") for i in range(45)])

    practice._length_combo.setCurrentIndex(4)  # "Tümü"

    assert practice._session_limit() == 0
    assert len(practice._queue) == 45


def test_default_session_length_is_thirty(practice, repo: WordRepository):
    repo.create_many([Word(term=f"k{i}", language="en") for i in range(40)])
    practice.start_session()

    assert practice._session_limit() == 30
    assert len(practice._queue) == 30


# ── Odak sağlamlaştırma ───────────────────────────────────────────────────

def test_grade_buttons_do_not_steal_focus(practice):
    """
    Odak view'da kalmalı; aksi hâlde değerlendirmeden sonra Boşluk tuşu
    keyPressEvent yerine odaklanmış butonu tetikliyordu.
    """
    from PyQt6.QtCore import Qt

    for btn in practice._grade_buttons:
        assert btn.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert practice._reveal_btn.focusPolicy() == Qt.FocusPolicy.NoFocus


# ── Düzenleme diyaloğu ────────────────────────────────────────────────────

def test_edit_dialog_populates_existing_content(qtbot, word_service: WordService, sample_word: Word):
    word = word_service.add_word("ephemeral", "en", ai_data={
        "definition": "Uzun tanım.",
        "definition_short": "Kısa tanım.",
        "part_of_speech": "Sıfat",
        "synonyms": ["transient", "fleeting"],
        "antonyms": ["permanent"],
        "example_sentences": ["A\nB", "C\nD"],
        "usage_notes": "Not.",
        "phonetic": "/x/",
    })

    dialog = EditWordDialog(word, word_service)
    qtbot.addWidget(dialog)

    assert dialog._term_input.text() == "ephemeral"
    assert dialog._short_input.text() == "Kısa tanım."
    assert dialog._definition_input.toPlainText() == "Uzun tanım."
    assert dialog._synonyms_input.text() == "transient, fleeting"
    assert dialog._phonetic_input.text() == "/x/"
    assert dialog._examples_input.toPlainText() == "A\nB\n\nC\nD"


def test_edit_dialog_saves_changes(qtbot, word_service: WordService):
    word = word_service.add_word("ephemeral", "en", ai_data={"definition": "eski"})
    dialog = EditWordDialog(word, word_service)
    qtbot.addWidget(dialog)

    dialog._definition_input.setPlainText("elle yazılmış yeni tanım")
    dialog._synonyms_input.setText("a, b , c")
    dialog._tags_input.setText("Fiil, TEMEL")

    with qtbot.waitSignal(dialog.word_saved, timeout=500):
        dialog._save()

    saved = word_service.get_by_id(word.id)
    assert saved.definition == "elle yazılmış yeni tanım"
    assert saved.synonyms == ["a", "b", "c"]
    assert saved.tags == ["fiil", "temel"]  # etiketler küçük harfe indirilir
    assert saved.ai_generated is False      # elle düzenlendi


def test_edit_dialog_rejects_empty_term(qtbot, word_service: WordService):
    word = word_service.add_word("ephemeral", "en")
    dialog = EditWordDialog(word, word_service)
    qtbot.addWidget(dialog)

    dialog._term_input.setText("   ")
    dialog._save()

    assert "boş olamaz" in dialog._status_label.text()
    assert word_service.get_by_id(word.id).term == "ephemeral"  # değişmedi


def test_edit_dialog_round_trips_examples(qtbot, word_service: WordService):
    """Örnekler 'foreign\\nturkish' saklanır; editörde boş satırla ayrılır."""
    word = word_service.add_word("x", "en", ai_data={"example_sentences": ["A\nB"]})
    dialog = EditWordDialog(word, word_service)
    qtbot.addWidget(dialog)

    dialog._examples_input.setPlainText("Foreign one\nTürkçe bir\n\nForeign two\nTürkçe iki")
    dialog._save()

    saved = word_service.get_by_id(word.id)
    assert saved.example_sentences == ["Foreign one\nTürkçe bir", "Foreign two\nTürkçe iki"]


def test_edit_dialog_surfaces_save_failure(qtbot, word_service: WordService, monkeypatch):
    word = word_service.add_word("x", "en")
    dialog = EditWordDialog(word, word_service)
    qtbot.addWidget(dialog)

    monkeypatch.setattr(
        word_service, "update_word", lambda w: (_ for _ in ()).throw(RuntimeError("db yok"))
    )
    with qtbot.assertNotEmitted(dialog.word_saved):
        dialog._save()

    assert "Kaydedilemedi" in dialog._status_label.text()
    assert dialog.result() != EditWordDialog.DialogCode.Accepted  # kapanmadı
