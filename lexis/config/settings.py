"""
Lexis — Configuration

Konfigürasyon iki katmanlıdır:

1. Ortam değişkenleri / .env  → ilk varsayılanlar (pydantic-settings).
2. Veritabanı (app_settings)  → kullanıcının uygulama içinden değiştirdiği
   kalıcı tercihler (API anahtarı, tema). Bu katman env'i geçersiz kılar.

Eskiden API anahtarı çalışma dizinindeki `.env` dosyasına yazılıyordu; bu,
uygulama farklı bir dizinden (AppImage/AUR) başlatıldığında tercihlerin
kaybolmasına yol açıyordu. Artık tercihler `~/.lexis/lexis.db` içinde tutulur.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from lexis.persistence.database import Database


class Settings(BaseSettings):
    """Uygulama konfigürasyonu."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Gemini API
    gemini_api_key: str | None = None

    # Veritabanı
    database_path: str | None = None

    # Loglama
    log_level: str = "INFO"

    # Tema (dark | light)
    app_theme: str = "dark"

    @property
    def db_path(self) -> Path:
        """Veritabanı dosyasının tam yolunu döndürür."""
        if self.database_path:
            return Path(self.database_path)
        # Varsayılan: ~/.lexis/lexis.db
        default_dir = Path.home() / ".lexis"
        default_dir.mkdir(parents=True, exist_ok=True)
        return default_dir / "lexis.db"

    @property
    def has_api_key(self) -> bool:
        return bool(self.gemini_api_key and self.gemini_api_key.strip())


# ── Kalıcı tercih anahtarları (app_settings tablosu) ──────────────────────
_KEY_API = "gemini_api_key"
_KEY_THEME = "app_theme"

# Singleton settings örneği + bağlı veritabanı
_settings: Settings | None = None
_db: Database | None = None


def _apply_persisted(s: Settings) -> None:
    """DB'de saklı tercihleri (varsa) settings üzerine uygular."""
    if _db is None:
        return
    stored_key = _db.get_setting(_KEY_API, "")
    if stored_key:
        s.gemini_api_key = stored_key
    stored_theme = _db.get_setting(_KEY_THEME, "")
    if stored_theme in ("dark", "light"):
        s.app_theme = stored_theme


def get_settings() -> Settings:
    """Singleton settings getter (DB tercihleri uygulanmış)."""
    global _settings
    if _settings is None:
        _settings = Settings()
        _apply_persisted(_settings)
    return _settings


def reload_settings() -> Settings:
    """Ayarları env'den yeniden yükler ve DB tercihlerini uygular."""
    global _settings
    _settings = Settings()
    _apply_persisted(_settings)
    return _settings


def bind_database(db: Database) -> None:
    """
    Settings katmanını veritabanına bağlar. Uygulama açılışında, DB
    oluşturulduktan hemen sonra çağrılır.

    İlk çalıştırmada env'den (.env) gelen değerler DB'ye taşınır; böylece
    eski .env tabanlı kurulumlar sorunsuz geçiş yapar.
    """
    global _db
    _db = db
    s = get_settings()

    # Env'den gelen mevcut değerleri ilk kez DB'ye taşı (migration).
    if not db.get_setting(_KEY_API, "") and s.has_api_key:
        db.set_setting(_KEY_API, s.gemini_api_key or "")
    if not db.get_setting(_KEY_THEME, ""):
        db.set_setting(_KEY_THEME, s.app_theme)

    _apply_persisted(s)


def save_api_key(api_key: str) -> None:
    """API anahtarını kalıcı olarak (DB) saklar."""
    api_key = api_key.strip()
    os.environ["GEMINI_API_KEY"] = api_key
    if _db is not None:
        _db.set_setting(_KEY_API, api_key)
    reload_settings()


def save_theme(theme_name: str) -> None:
    """Tema tercihini (dark/light) kalıcı olarak (DB) saklar."""
    if theme_name not in ("dark", "light"):
        theme_name = "dark"
    os.environ["APP_THEME"] = theme_name
    if _db is not None:
        _db.set_setting(_KEY_THEME, theme_name)
    reload_settings()
