"""
Lexis — Tests: Dashboard (streak, aktivite grafiği, Türkçe tarih)
"""

from datetime import date, datetime, timedelta

import pytest

pytest.importorskip("PyQt6.QtWidgets")

from PyQt6.QtWidgets import QLabel  # noqa: E402

from lexis.domain.models import ReviewGrade, Word, utcnow  # noqa: E402
from lexis.persistence.word_repository import WordRepository  # noqa: E402
from lexis.services.word_service import WordService  # noqa: E402
from lexis.ui.views.dashboard_view import (  # noqa: E402
    ACTIVITY_DAYS,
    DashboardView,
    StatCard,
    _format_date_tr,
)
from lexis.ui.widgets.activity_chart import ActivityChart  # noqa: E402


@pytest.fixture
def dashboard(qtbot, word_service: WordService) -> DashboardView:
    """Bağımsız dashboard (MainWindow'un modal ekleme akışına bağlanmaz)."""
    view = DashboardView(word_service)
    view.resize(1200, 800)
    qtbot.addWidget(view)
    return view


def _stat_values(dashboard) -> dict[str, str]:
    """Kart etiketi → gösterilen değer (ör. {"Günlük Seri": "🔥 3"})."""
    out: dict[str, str] = {}
    for card in dashboard.findChildren(StatCard):
        value = card.findChild(QLabel, "statValue")
        label = card.findChild(QLabel, "statLabel")
        if value is not None and label is not None:
            out[label.text()] = value.text()
    return out


# ── Streak ────────────────────────────────────────────────────────────────


def test_streak_card_shows_zero_without_reviews(dashboard):
    dashboard.refresh()
    assert _stat_values(dashboard)["Günlük Seri"] == "0"


def test_streak_card_counts_today(dashboard, word_service: WordService):
    word = word_service.add_word("bugun", "en")
    word_service.review_word(word.id, ReviewGrade.GOOD)

    dashboard.refresh()

    assert _stat_values(dashboard)["Günlük Seri"] == "🔥 1"


def test_streak_card_counts_consecutive_days(dashboard, word_service: WordService, tmp_db):
    word = word_service.add_word("seri", "en")
    now = utcnow()
    with tmp_db.connection() as conn:
        for offset in range(3):
            conn.execute(
                "INSERT INTO review_log (id, word_id, grade, reviewed_at, interval_days) "
                "VALUES (?, ?, ?, ?, ?)",
                (f"r{offset}", word.id, 4, (now - timedelta(days=offset)).isoformat(), 1),
            )
        conn.commit()

    dashboard.refresh()

    assert _stat_values(dashboard)["Günlük Seri"] == "🔥 3"


# ── Aktivite grafiği ──────────────────────────────────────────────────────


def test_activity_chart_gets_seven_days(dashboard):
    dashboard.refresh()
    assert len(dashboard._activity_chart._counts) == ACTIVITY_DAYS


def test_activity_summary_when_idle(dashboard):
    dashboard.refresh()
    assert "henüz çalışılmadı" in dashboard._activity_summary.text()


def test_activity_summary_counts_reviews(dashboard, word_service: WordService):
    word = word_service.add_word("calis", "en")
    word_service.review_word(word.id, ReviewGrade.GOOD)
    word_service.review_word(word.id, ReviewGrade.GOOD)

    dashboard.refresh()

    assert dashboard._activity_summary.text() == "2 tekrar"
    assert dashboard._activity_chart._counts[date.today()] == 2


def test_activity_chart_paints_without_error(qtbot):
    """Grafik QPainter ile çizilir; veri varken de yokken de patlamamalı."""
    chart = ActivityChart()
    qtbot.addWidget(chart)
    chart.resize(400, 132)
    chart.show()
    qtbot.waitExposed(chart)

    chart.set_counts({})  # veri yok
    chart.repaint()

    today = date.today()
    chart.set_counts({today - timedelta(days=i): i for i in range(6, -1, -1)})
    chart.repaint()

    assert "7 günde" in chart.toolTip()


def test_activity_chart_handles_all_zero_days(qtbot):
    """Tepe değeri 0 olduğunda sıfıra bölme olmamalı."""
    chart = ActivityChart()
    qtbot.addWidget(chart)
    chart.resize(400, 132)
    chart.show()
    qtbot.waitExposed(chart)

    chart.set_counts({date.today() - timedelta(days=i): 0 for i in range(7)})
    chart.repaint()  # patlamamalı


# ── Türkçe tarih ──────────────────────────────────────────────────────────


def test_date_is_formatted_in_turkish():
    """strftime sistem yereline bağlıydı ve Türkçe arayüzde 'July' basıyordu."""
    text = _format_date_tr(datetime(2026, 7, 17))
    assert text == "17 Temmuz 2026, Cuma"


def test_dashboard_shows_turkish_date(dashboard):
    assert "Temmuz" in dashboard._date_label.text() or any(
        month in dashboard._date_label.text()
        for month in (
            "Ocak",
            "Şubat",
            "Mart",
            "Nisan",
            "Mayıs",
            "Haziran",
            "Temmuz",
            "Ağustos",
            "Eylül",
            "Ekim",
            "Kasım",
            "Aralık",
        )
    )


# ── Çalışma kuyruğu ───────────────────────────────────────────────────────


def test_practice_button_counts_unreviewed_words(dashboard, repo: WordRepository):
    """
    Yeni kelimeler due_today'e girmez ama çalışma kuyruğundadır; buton
    kuyruğun tamamını saymalı.
    """
    repo.create_many([Word(term=f"k{i}", language="en") for i in range(3)])

    dashboard.refresh()

    assert "(3)" in dashboard._practice_btn.text()
    assert dashboard._practice_btn.isEnabled()


def test_practice_button_disabled_when_library_empty(dashboard):
    dashboard.refresh()
    assert not dashboard._practice_btn.isEnabled()
