"""
Lexis — Word Service

Kelime yönetimi için uygulama/iş mantığı katmanı.
Repository ve AI servisini koordine eder.
"""

from __future__ import annotations

import logging

from lexis.domain.exceptions import ContentProviderError, DuplicateWordError
from lexis.domain.models import SUPPORTED_LANGUAGES, ReviewGrade, Word, WordStats, WordStatus
from lexis.persistence.word_repository import WordRepository
from lexis.services.ai_service import AIService
from lexis.services.open_dictionary import RICH_LANGUAGE, OpenDictionaryService

logger = logging.getLogger(__name__)

# Otomatik dil denemesinde Gemini için üst sınır. Açık sözlükte adaylar
# sınırsız denenir (sayfa önbelleği sayesinde ek aday ek ağ maliyeti
# getirmiyor); Gemini'de ise her aday ayrı bir ücretli istek ve birkaç saniye —
# sınırsız aday, bulunamayan kelimede kullanıcıyı dakikalarca bekletirdi.
MAX_AI_LANGUAGE_ATTEMPTS = 3


class WordService:
    """Kelime ekleme, güncelleme ve sorgulama iş mantığı."""

    def __init__(
        self,
        repository: WordRepository,
        ai_service: AIService,
        open_dictionary: OpenDictionaryService | None = None,
    ) -> None:
        self._repo = repository
        self._ai = ai_service
        # Anahtar girilmemişse içerik açık sözlüklerden derlenir; uygulama
        # kutudan çıktığı gibi çalışsın diye varsayılan sağlayıcı budur.
        self._open_dict = open_dictionary or OpenDictionaryService()

    # ── Sorgulama ─────────────────────────────────────────────────────────

    def get_all(
        self,
        search: str = "",
        language: str = "",
        status: WordStatus | None = None,
        favorites_only: bool = False,
        tag: str = "",
        sort_by: str = "created_at",
        sort_desc: bool = True,
        limit: int = 0,
        offset: int = 0,
    ) -> list[Word]:
        """
        Filtrelenmiş kelime listesi.

        limit > 0 verildiğinde sayfalama uygulanır; kütüphane büyüdüğünde
        tüm tabloyu belleğe çekmemek için kullanılır.
        """
        return self._repo.get_all(
            search=search,
            language=language,
            status=status,
            favorites_only=favorites_only,
            tag=tag,
            sort_by=sort_by,
            sort_desc=sort_desc,
            limit=limit,
            offset=offset,
        )

    def count(
        self,
        search: str = "",
        language: str = "",
        status: WordStatus | None = None,
        favorites_only: bool = False,
        tag: str = "",
    ) -> int:
        """get_all ile aynı filtrelere uyan toplam kayıt sayısı."""
        return self._repo.count(
            search=search,
            language=language,
            status=status,
            favorites_only=favorites_only,
            tag=tag,
        )

    def get_by_id(self, word_id: str) -> Word:
        return self._repo.get_by_id(word_id)

    def get_recent(self, limit: int = 12) -> list[Word]:
        return self._repo.get_recent(limit=limit)

    def get_recently_reviewed(self, limit: int = 6) -> list[Word]:
        return self._repo.get_recently_reviewed(limit=limit)

    def get_due_words(self, limit: int = 0) -> list[Word]:
        """Tekrar zamanı gelmiş kelimeleri (çalışma kuyruğu) döndürür."""
        return self._repo.get_due(limit=limit)

    def get_stats(self) -> WordStats:
        return self._repo.get_stats()

    def get_all_tags(self) -> list[str]:
        return self._repo.get_all_tags()

    # ── Ekleme & Güncelleme ───────────────────────────────────────────────

    def add_word(
        self,
        term: str,
        language: str = "en",
        ai_data: dict | None = None,
    ) -> Word:
        """
        Yeni kelime ekler.

        Args:
            term: Eklenecek kelime.
            language: Kelime dili ('en', 'de', vb.)
            ai_data: Önceden üretilmiş AI verisi. None ise boş Word oluşturulur.

        Raises:
            DuplicateWordError: Aynı kelime zaten mevcutsa.
        """
        term = term.strip()
        if self._repo.exists(term, language):
            raise DuplicateWordError(term, language)

        word = Word(term=term, language=language)

        if ai_data:
            self.apply_content(word, ai_data)

        return self._repo.create(word)

    def update_word(self, word: Word) -> Word:
        """Mevcut kelimeyi günceller."""
        return self._repo.update(word)

    def delete_word(self, word_id: str) -> None:
        """Kelimeyi siler."""
        self._repo.delete(word_id)

    def restore_word(self, word: Word) -> Word:
        """
        Silinmiş bir kelimeyi aynı id ile geri yükler ("geri al" için).

        Not: tekrar geçmişi (review_log) silme sırasında CASCADE ile gittiği
        için geri gelmez; kelimenin kendisi ve SM-2 durumu korunur.
        """
        return self._repo.create(word)

    def toggle_favorite(self, word_id: str) -> Word:
        """Favorilere ekler/çıkarır."""
        word = self._repo.get_by_id(word_id)
        word.is_favorite = not word.is_favorite
        return self._repo.update(word)

    def update_status(self, word_id: str, status: WordStatus) -> Word:
        """Kelime öğrenme durumunu günceller."""
        word = self._repo.get_by_id(word_id)
        word.status = status
        word.mark_reviewed()
        return self._repo.update(word)

    def review_word(self, word_id: str, grade: ReviewGrade) -> Word:
        """
        Bir tekrar oturumunda kullanıcının değerlendirmesini uygular.
        SM-2 ile sonraki tekrar tarihini hesaplar, kaydeder ve geçmişe yazar.
        """
        word = self._repo.get_by_id(word_id)
        word.apply_review(grade)
        updated = self._repo.update(word)
        self._repo.log_review(word.id, int(grade), word.interval_days)
        return updated

    def get_streak(self) -> int:
        """Kesintisiz çalışılan gün sayısı."""
        return self._repo.get_streak()

    def get_review_counts(self, days: int = 7) -> dict:
        """Son `days` gün için gün başına tekrar sayısı."""
        return self._repo.get_review_counts(days=days)

    def add_tag(self, word_id: str, tag: str) -> Word:
        """Kelimeye etiket ekler."""
        word = self._repo.get_by_id(word_id)
        tag = tag.strip().lower()
        if tag and tag not in word.tags:
            word.tags.append(tag)
            self._repo.update(word)
        return word

    def remove_tag(self, word_id: str, tag: str) -> Word:
        """Kelimeden etiket kaldırır."""
        word = self._repo.get_by_id(word_id)
        if tag in word.tags:
            word.tags.remove(tag)
            self._repo.update(word)
        return word

    def mark_reviewed(self, word_id: str) -> Word:
        """Kelimeyi çalışıldı olarak işaretler."""
        word = self._repo.get_by_id(word_id)
        word.mark_reviewed()
        return self._repo.update(word)

    # ── AI Üretim ─────────────────────────────────────────────────────────

    def generate_content(self, term: str, language: str = "en") -> dict:
        """
        Kelime içeriği üretir.

        Gemini anahtarı varsa onu kullanır (daha akıcı Türkçe ve kullanım notu);
        yoksa açık sözlük kaynaklarına düşer. Böylece uygulama anahtarsız da
        çalışır.

        Bu metot ağ çağrısı yapar ve doğrudan çağrılırsa UI'ı bloklar;
        TaskWorker üzerinden çağrılması gerekir.
        """
        provider = self._ai if self._ai.is_configured else self._open_dict
        return provider.generate_word_data(term, language)

    # Eski ad; UI ve testler kademeli geçsin diye korunuyor.
    generate_ai_content = generate_content

    def generate_auto(self, term: str) -> tuple[dict, str]:
        """
        Dili kendi belirleyip içerik üretir.

        Adaylar sırayla denenir: ilk tahminde pes etmek, çok dilli kelimelerde
        hatalı "bulunamadı" veriyordu (ör. "Baran" İngilizce'de sözlük kelimesi
        değil ama Lehçe'de "koç" demek — İngilizce denenip vazgeçiliyordu).

        Yalnızca "bu dilde yok" hatasında sonraki adaya geçilir; ağ/anahtar
        arızası gibi gerçek hatalarda hemen yükseltilir, yoksa çökmüş bir servis
        için aynı hata üç kez beklenirdi.

        Returns:
            (içerik, kullanılan dil kodu)

        Raises:
            ContentProviderError: Hiçbir adayda kayıt bulunamazsa.
        """
        candidates = self.detect_languages(term)
        if self._ai.is_configured:
            candidates = candidates[:MAX_AI_LANGUAGE_ATTEMPTS]

        last_error: ContentProviderError | None = None
        tried: list[str] = []

        for language in candidates:
            try:
                return self.generate_content(term, language), language
            except ContentProviderError as e:
                logger.info("'%s' %s dilinde bulunamadı, sonraki aday", term, language)
                tried.append(SUPPORTED_LANGUAGES.get(language, language))
                last_error = e

        if last_error is not None:
            # Yalnızca son adayın hatası değil: kullanıcı hangi dillerin
            # denendiğini görmeli, yoksa "İngilizce'de yok" mesajı diğer
            # dillerin hiç denenmediği izlenimini veriyordu.
            raise ContentProviderError(
                f"'{term}' denenen dillerin hiçbirinde ({', '.join(tried)}) bulunamadı."
            )
        raise ContentProviderError(f"'{term}' için sözlük kaydı bulunamadı.")

    def regenerate_ai_content(self, word_id: str) -> Word:
        """Mevcut kelimenin içeriğini yeniden üretir."""
        word = self._repo.get_by_id(word_id)
        data = self.generate_content(word.term, word.language)
        self.apply_content(word, data)
        return self._repo.update(word)

    @staticmethod
    def apply_content(word: Word, data: dict) -> Word:
        """
        Üretilen içeriği Word üzerine uygular.

        Eksik alanlar mevcut değeri korur: açık sözlük bazı alanları (ör.
        kullanım notu) boş bırakabilir, bu mevcut içeriği silmemeli.
        """
        word.definition = data.get("definition") or word.definition
        word.definition_short = data.get("definition_short") or word.definition_short
        word.part_of_speech = data.get("part_of_speech") or word.part_of_speech
        word.synonyms = data.get("synonyms") or word.synonyms
        word.antonyms = data.get("antonyms") or word.antonyms
        word.example_sentences = data.get("example_sentences") or word.example_sentences
        word.usage_notes = data.get("usage_notes") or word.usage_notes
        word.phonetic = data.get("phonetic") or word.phonetic
        word.audio_url = data.get("audio_url") or word.audio_url
        word.ai_generated = True
        return word

    def suggest_terms(self, term: str, language: str = "en") -> list[str]:
        """
        Yanlış yazılmış bir kelime için alternatif önerir.

        Öneriler daima açık sözlüklerden gelir: anahtarsız çalışır ve Gemini
        modunda da kullanılabilir.
        """
        return self._open_dict.suggest_terms(term, language)

    def complete_terms(self, prefix: str, language: str = "en") -> list[str]:
        """Yazılmakta olan kelimeyi tamamlar (açık sözlüklerden)."""
        return self._open_dict.complete_terms(prefix, language)

    def detect_languages(self, term: str) -> list[str]:
        """
        Kelimenin ait olabileceği dilleri olasılık sırasıyla döndürür.

        Gemini anahtarı olsa da açık sözlüğe sorulur: tahmin için üretken bir
        modele para/kota harcamanın anlamı yok.

        Açık sözlüğün sırasına kütüphane dil dağılımı hafif bir önsel olarak
        katılır: çok dilli bir kelimede kullanıcının en çok çalıştığı dil öne
        alınır. İngilizce baştaysa yerinde bırakılır — telaffuz/ses veren tek
        zengin kaynağa bağlı olma avantajı korunur (bkz. OpenDictionaryService).
        """
        candidates = self._open_dict.detect_languages(term)
        if len(candidates) < 2:
            return candidates

        counts = self._repo.get_language_counts()
        # 0. konum, İngilizce adaylar arasındaysa sabit tutulur; yalnızca gerisi
        # kullanıcının dağılımına göre yeniden sıralanır. Bu, "candidates[0] ==
        # en" değil "en in candidates" ile kontrol edilir: OpenDictionaryService
        # bazen İngilizce'yi bilinçli olarak geride bırakır (ör. "bonjour" gibi
        # ödünç selamlarda asıl dil öne alınır) — o zaman 0. konum artık "en"
        # değildir ama yine de korunmalı, yoksa İngilizce ağırlıklı bir
        # kütüphanede kütüphane önceliği bu kararı sessizce geçersiz kılıp
        # İngilizce'yi tekrar başa taşırdı. "en" aday listesinde hiç yoksa
        # (İngilizce sözlük kaydı bulunamadı) sabitleme gereksiz, tüm liste
        # serbestçe sıralanır. sorted kararlıdır: eşit sayımda özgün sıra
        # korunur, boş kütüphanede hiçbir şey değişmez.
        head = candidates[:1] if RICH_LANGUAGE in candidates else []
        rest = sorted(candidates[len(head) :], key=lambda code: counts.get(code, 0), reverse=True)
        return head + rest

    def detect_language(self, term: str) -> str:
        """En olası tek dili döndürür (bkz. detect_languages)."""
        return self.detect_languages(term)[0]

    def configure_ai(self, api_key: str | None) -> None:
        """
        AI istemcisini yeni API anahtarıyla yeniden yapılandırır.

        Boş anahtar Gemini'yi kapatır; içerik açık sözlükten gelmeye devam eder.
        """
        self._ai.configure(api_key)

    @property
    def ai_configured(self) -> bool:
        """Gemini anahtarı girilmiş mi? (İçerik üretimi buna bağlı değildir.)"""
        return self._ai.is_configured

    @property
    def content_source(self) -> str:
        """Şu an hangi kaynağın kullanılacağını bildirir (UI'da gösterilir)."""
        return "Gemini" if self._ai.is_configured else "Açık sözlük"
