"""
Lexis — Tests: Ayarlar ekranında Gemini anahtarı yönetimi

Gemini isteğe bağlı olduğuna göre girilen anahtardan vazgeçmek de mümkün olmalı.
"""

import pytest

pytest.importorskip("PyQt6.QtWidgets")

from lexis.services.export_service import ExportService  # noqa: E402
from lexis.services.word_service import WordService  # noqa: E402
from lexis.ui.views.settings_view import SettingsView  # noqa: E402


@pytest.fixture
def settings_view(
    qtbot, word_service: WordService, export_service: ExportService, monkeypatch
) -> SettingsView:
    # Anahtar DB'ye değil belleğe yazılsın; test kullanıcının ~/.lexis'ine dokunmamalı.
    saved: dict[str, str] = {}
    monkeypatch.setattr(
        "lexis.ui.views.settings_view.save_api_key",
        lambda key: saved.__setitem__("key", key),
    )
    view = SettingsView(word_service, export_service)
    qtbot.addWidget(view)
    view._saved = saved
    return view


def test_clearing_key_field_removes_the_key(settings_view, word_service: WordService):
    """
    Alan temizlenip kaydedilince anahtar silinmeli.

    Eskiden "API anahtarı boş olamaz." hatası verilip kayıt reddediliyordu:
    bir kez anahtar girildiğinde açık sözlük moduna dönmenin yolu yoktu.
    """
    settings_view._api_key_input.setText("")
    settings_view._save_api_key()

    assert settings_view._saved["key"] == ""
    assert word_service.ai_configured is False
    assert word_service.content_source == "Açık sözlük"


def test_clearing_key_reports_success_not_error(settings_view):
    """Silme işlemi başarı olarak bildirilmeli, hata olarak değil."""
    settings_view._api_key_input.setText("")
    settings_view._save_api_key()

    assert settings_view._api_status.property("level") == "success"
    assert "silindi" in settings_view._api_status.text().lower()
