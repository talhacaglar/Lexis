"""
Lexis — Domain Exceptions

Uygulama genelinde kullanılan domain-level hata sınıfları.
"""


class LexisError(Exception):
    """Tüm Lexis hatalarının temel sınıfı."""


class WordNotFoundError(LexisError):
    """Kelime veritabanında bulunamadığında fırlatılır."""
    def __init__(self, word_id: str):
        super().__init__(f"Kelime bulunamadı: {word_id}")
        self.word_id = word_id


class DuplicateWordError(LexisError):
    """Aynı kelime aynı dil için zaten mevcutsa fırlatılır."""
    def __init__(self, term: str, language: str):
        super().__init__(f"'{term}' ({language}) zaten sözlükte mevcut.")
        self.term = term
        self.language = language


class AIServiceError(LexisError):
    """AI servisiyle iletişim hatalarında fırlatılır."""
    def __init__(self, message: str, original: Exception | None = None):
        super().__init__(f"AI Servis Hatası: {message}")
        self.original = original


class APIKeyMissingError(LexisError):
    """Gemini API anahtarı eksik olduğunda fırlatılır."""
    def __init__(self):
        super().__init__(
            "Gemini API anahtarı bulunamadı. "
            "Lütfen Ayarlar ekranından API anahtarınızı girin."
        )


class DatabaseError(LexisError):
    """Veritabanı işlemlerinde fırlatılır."""
    def __init__(self, message: str, original: Exception | None = None):
        super().__init__(f"Veritabanı Hatası: {message}")
        self.original = original


class ImportError(LexisError):
    """İçe aktarma hatalarında fırlatılır."""


class ExportError(LexisError):
    """Dışa aktarma hatalarında fırlatılır."""
