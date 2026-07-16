"""
Lexis — Tests: Toast bildirimleri, geri alınabilir silme ve hata görünürlüğü
"""

import pytest

pytest.importorskip("PyQt6.QtWidgets")

from PyQt6.QtWidgets import QApplication, QLabel, QMessageBox  # noqa: E402

from lexis.domain.models import ReviewGrade, Word  # noqa: E402
from lexis.persistence.word_repository import WordRepository  # noqa: E402
from lexis.services.export_service import ExportService  # noqa: E402
from lexis.services.word_service import WordService  # noqa: E402
from lexis.ui.theme import apply_theme, set_theme  # noqa: E402
from lexis.ui.widgets.toast import ToastManager  # noqa: E402
from lexis.ui.windows.main_window import MainWindow  # noqa: E402


@pytest.fixture
def window(qtbot, word_service: WordService, export_service: ExportService):
    set_theme("dark")
    apply_theme(QApplication.instance())
    w = MainWindow(word_service=word_service, export_service=export_service)
    qtbot.addWidget(w)
    return w


@pytest.fixture
def confirm_yes(monkeypatch):
    """Silme onay diyaloğunu otomatik 'Evet'ler."""
    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes
    )


# ── ToastManager ──────────────────────────────────────────────────────────

def _toast_text(toast) -> str:
    return toast.findChild(QLabel, "toastText").text()


def test_toast_shows_message(window):
    toast = window.toasts.show("merhaba")
    assert _toast_text(toast) == "merhaba"


def test_toast_levels_set_property(window):
    assert window.toasts.error("hata").property("level") == "error"
    assert window.toasts.success("oldu").property("level") == "success"


def test_toast_stack_is_capped(window):
    for i in range(6):
        window.toasts.show(f"bildirim {i}")
    assert len(window.toasts._toasts) <= ToastManager.MAX_VISIBLE


def test_toast_action_runs_once(window):
    calls = []
    toast = window.toasts.show(
        "silindi", action_label="Geri al", on_action=lambda: calls.append(1)
    )

    toast._trigger_action()
    toast._trigger_action()  # hızlı çift tıklama

    assert calls == [1]


def test_toast_action_failure_does_not_crash(window):
    def boom():
        raise RuntimeError("patladı")

    toast = window.toasts.show("x", action_label="Dene", on_action=boom)
    toast._trigger_action()  # istisna yutulur, uygulama ayakta kalır


# ── Geri alınabilir silme ─────────────────────────────────────────────────

def test_delete_word_offers_undo(window, repo: WordRepository, sample_word: Word, confirm_yes):
    repo.create(sample_word)

    window._delete_word(sample_word.id)

    assert repo.get_all() == []
    assert len(window.toasts._toasts) == 1
    assert "silindi" in _toast_text(window.toasts._toasts[0])


def test_undo_restores_word_with_same_id(window, repo: WordRepository, sample_word: Word, confirm_yes):
    repo.create(sample_word)
    window._delete_word(sample_word.id)
    assert repo.get_all() == []

    window.toasts._toasts[0]._trigger_action()  # "Geri al"

    restored = repo.get_all()
    assert len(restored) == 1
    assert restored[0].id == sample_word.id
    assert restored[0].term == "ephemeral"
    assert restored[0].tags == ["vocabulary", "adjective"]


def test_undo_preserves_srs_state(window, repo: WordRepository, word_service: WordService, confirm_yes):
    """Geri alınan kelime SM-2 ilerlemesini korumalı."""
    word = word_service.add_word("kalici", "en")
    word_service.review_word(word.id, ReviewGrade.GOOD)
    before = word_service.get_by_id(word.id)

    window._delete_word(word.id)
    window.toasts._toasts[0]._trigger_action()

    after = word_service.get_by_id(word.id)
    assert after.repetitions == before.repetitions
    assert after.interval_days == before.interval_days
    assert after.ease_factor == before.ease_factor


def test_delete_cancelled_keeps_word(window, repo: WordRepository, sample_word: Word, monkeypatch):
    repo.create(sample_word)
    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No
    )

    window._delete_word(sample_word.id)

    assert len(repo.get_all()) == 1


def test_delete_missing_word_shows_error(window, confirm_yes):
    window._delete_word("olmayan-id")
    assert window.toasts._toasts[0].property("level") == "error"


# ── Sessiz hataların kaldırılması ─────────────────────────────────────────

def test_failed_favorite_toggle_surfaces_error(window, repo: WordRepository, sample_word: Word, monkeypatch):
    repo.create(sample_word)
    monkeypatch.setattr(
        window._service, "toggle_favorite", lambda _id: (_ for _ in ()).throw(RuntimeError("db yok"))
    )

    window._toggle_favorite(sample_word.id)

    assert window.toasts._toasts[0].property("level") == "error"


def test_failed_review_does_not_advance_card(window, repo: WordRepository, monkeypatch):
    """
    Değerlendirme kaydedilemezse kart ilerlememeli; eskiden sessizce
    ilerleyip tekrarı kaybediyordu.
    """
    repo.create_many([Word(term="bir", language="en"), Word(term="iki", language="en")])
    practice = window._practice
    practice.start_session()
    practice._reveal()

    first_term = practice._term_label.text()
    monkeypatch.setattr(
        window._service, "review_word", lambda *a: (_ for _ in ()).throw(RuntimeError("db yok"))
    )

    practice._grade(ReviewGrade.GOOD)

    assert practice._term_label.text() == first_term  # kart yerinde kaldı
    assert practice._reviewed == 0
    assert window.toasts._toasts[0].property("level") == "error"


def test_failed_word_load_navigates_back(window, monkeypatch):
    monkeypatch.setattr(
        window._service, "get_by_id", lambda _id: (_ for _ in ()).throw(RuntimeError("yok"))
    )

    window._detail.load_word("olmayan-id")

    assert window.toasts._toasts[0].property("level") == "error"
