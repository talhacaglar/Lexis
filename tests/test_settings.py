"""
Lexis — Tests: Settings persistence (DB-backed)
"""

import pytest

from lexis.config import settings as settings_mod
from lexis.persistence.database import Database


@pytest.fixture
def bound_db(tmp_path, monkeypatch):
    """Geçici DB'ye bağlı, izole edilmiş settings modülü."""
    # Singleton ve bağlı DB'yi izole et
    monkeypatch.setattr(settings_mod, "_settings", None)
    monkeypatch.setattr(settings_mod, "_db", None)
    db = Database(tmp_path / "settings.db")
    settings_mod.bind_database(db)
    yield db
    monkeypatch.setattr(settings_mod, "_settings", None)
    monkeypatch.setattr(settings_mod, "_db", None)


def test_save_api_key_persists_to_db(bound_db: Database):
    settings_mod.save_api_key("AIza-TEST-KEY")
    # DB'de saklandı
    assert bound_db.get_setting("gemini_api_key") == "AIza-TEST-KEY"
    # Settings üzerinden okunabiliyor
    assert settings_mod.get_settings().gemini_api_key == "AIza-TEST-KEY"
    assert settings_mod.get_settings().has_api_key is True


def test_save_theme_persists_to_db(bound_db: Database):
    settings_mod.save_theme("light")
    assert bound_db.get_setting("app_theme") == "light"
    assert settings_mod.get_settings().app_theme == "light"


def test_invalid_theme_falls_back_to_dark(bound_db: Database):
    settings_mod.save_theme("neon")
    assert settings_mod.get_settings().app_theme == "dark"


def test_db_value_survives_reload(bound_db: Database):
    settings_mod.save_api_key("PERSISTED")
    # env'den yeniden yüklense bile DB değeri korunur
    reloaded = settings_mod.reload_settings()
    assert reloaded.gemini_api_key == "PERSISTED"
