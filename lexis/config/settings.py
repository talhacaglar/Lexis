"""
Lexis — Configuration

pydantic-settings kullanılarak ortam değişkenleri ve .env dosyasından
tip-güvenli konfigürasyon yükleme.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Uygulama konfigürasyonu."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Gemini API
    gemini_api_key: Optional[str] = None

    # Veritabanı
    database_path: Optional[str] = None

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


# Singleton settings örneği
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Thread-safe singleton settings getter."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Ayarları yeniden yükler (API key güncelleme sonrası)."""
    global _settings
    _settings = Settings()
    return _settings


def save_api_key(api_key: str) -> None:
    """
    API anahtarını .env dosyasına yazar.
    Uygulamanın çalıştığı dizinde .env dosyası oluşturur/günceller.
    """
    env_path = Path(".env")

    # Mevcut .env içeriğini oku
    lines: list[str] = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    # GEMINI_API_KEY satırını bul ve güncelle
    key_found = False
    new_lines = []
    for line in lines:
        if line.startswith("GEMINI_API_KEY="):
            new_lines.append(f"GEMINI_API_KEY={api_key}\n")
            key_found = True
        else:
            new_lines.append(line)

    if not key_found:
        new_lines.append(f"\nGEMINI_API_KEY={api_key}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    # Ortam değişkenini de güncelle
    os.environ["GEMINI_API_KEY"] = api_key
    reload_settings()


def save_theme(theme_name: str) -> None:
    """Tema tercihini (dark/light) .env dosyasına yazar."""
    env_path = Path(".env")
    lines: list[str] = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    found = False
    new_lines = []
    for line in lines:
        if line.startswith("APP_THEME="):
            new_lines.append(f"APP_THEME={theme_name}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        # Eğer dosya sonunda \n yoksa ekle
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"
        new_lines.append(f"APP_THEME={theme_name}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    os.environ["APP_THEME"] = theme_name
    reload_settings()
