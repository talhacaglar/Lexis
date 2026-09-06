<div align="center">
  <h1>📚 Lexis</h1>
  <p><strong>Modern, kişiselleştirilmiş ve tamamen yerel sözlük uygulaması</strong><br>
  <sub>API anahtarı gerekmez · aralıklı tekrar ile kalıcı öğrenme</sub></p>

  <p>
    <a href="https://aur.archlinux.org/packages/lexis-git">
    </a>
    <a href="LICENSE">
    </a>
  </p>
</div>

<br>

> **English summary** — Lexis is a local-first desktop dictionary and vocabulary
> trainer, built for Turkish speakers learning foreign languages. It works with
> **no API key**: definitions, parts of speech, synonyms/antonyms, IPA and
> pronunciation audio come from [dictionaryapi.dev](https://dictionaryapi.dev)
> and Wiktionary, example sentences with translations from
> [Tatoeba](https://tatoeba.org), and translation fallback from MyMemory — all
> fetched with the Python standard library, no extra dependency. Everything you
> save stays on your machine in SQLite (`~/.lexis/lexis.db`); nothing is synced
> anywhere. Vocabulary review uses SM-2 spaced repetition. An optional Gemini
> key gives more fluent Turkish phrasing, but nothing breaks without one.
>
> That constraint is deliberate: language tools for Turkish speakers are almost
> all subscription apps or key-gated services, and a student who cannot pay for
> one should still get a real dictionary entry rather than a generated guess.
>
> **Install:** `yay -S lexis-git` on Arch, or `pip install -e .` from a clone
> (Python 3.10+, PyQt6). Full documentation below is in Turkish.

<br>

Lexis, yabancı dil öğrenenler ve kelime dağarcığını geliştirmek isteyenler için geliştirilmiş hafif, modern ve local-first bir masaüstü uygulamasıdır. Girilen kelimelerin türünü, anlamını, örnek cümlelerini, Türkçe çevirilerini, telaffuzunu, eş ve zıt anlamlılarını saniyeler içinde otomatik olarak getirir.

Amaç, yalnızca “bu kelime ne demek?” sorusuna cevap vermek değil; aynı zamanda kelimenin nerede, nasıl ve hangi bağlamda kullanıldığını daha anlaşılır hale getirmektir.

**Kurulumdan sonra hemen çalışır — API anahtarı gerekmez.** İçerik, anahtar istemeyen açık sözlük kaynaklarından (Wiktionary, dictionaryapi.dev, Tatoeba, MyMemory) derlenir. Dilerseniz ücretsiz bir Gemini anahtarı girerek daha akıcı Türkçe tanımlar ve kullanım notları alabilirsiniz.

Tüm veriler SQLite kullanılarak tamamen yerel olarak saklanır. Herhangi bir abonelik, ekstra sunucu ya da harici veri depolama ihtiyacı olmadan doğrudan cihazınız üzerinde çalışır. ✨

## ✨ Özellikler

- 📚 **Anahtarsız içerik:** Kutudan çıktığı gibi çalışır. Tanım, sözcük türü, eş/zıt anlamlılar, çevirili örnek cümleler ve **telaffuz** (IPA + ses) açık sözlüklerden gelir; uydurma değil, gerçek sözlük kaydıdır.
- 🤖 **İsteğe bağlı yapay zeka:** Gemini anahtarı girildiğinde içerik yapay zekâ ile üretilir: daha akıcı Türkçe ve kullanım notları.
- 🧠 **Aralıklı tekrar (spaced repetition):** SM-2 algoritması ile her kelimeyi tam unutmaya yakın zamanda karşınıza getirir. **Tekrar** dediğiniz kart oturumu terk etmeden geri gelir.
- 🔥 **Günlük seri ve aktivite grafiği:** Kesintisiz çalıştığınız gün sayısını ve son 7 günün tekrar dağılımını ana ekranda görürsünüz.
- ✎ **Elle düzenleme:** Tanımı, örnekleri, eş/zıt anlamlıları ve notları dilediğiniz gibi düzeltebilirsiniz.
- ↩️ **Geri alınabilir silme:** Yanlışlıkla sildiğiniz kelimeyi tek tıkla geri alırsınız.
- 🌓 **Aydınlık ve karanlık tema:** Tema anında değişir; aramanız ve konumunuz korunur.
- 🔒 **%100 yerel veri saklama:** Tüm kayıtlar (ve varsa API anahtarınız) cihazınızdaki `~/.lexis/lexis.db` veritabanında tutulur.
- 🏷️ **Etiket ve öğrenme durumu yönetimi:** Etiketlere göre filtreleyin (karttaki etikete tıklamanız yeterli); Yeni, Öğreniliyor ve Öğrenildi durumlarıyla ayırın.
- ⌨️ **Klavye kısayolları:** `Ctrl+N` kelime ekle · `Ctrl+P` çalış · `Ctrl+1/2` sayfalar · `Ctrl+,` ayarlar · `Ctrl+F` veya `/` ara · `Esc` geri. Çalışma modunda `Boşluk` cevabı açar, `1-4` değerlendirir.
- 📥 **İçe / dışa aktarma desteği:** Sözlüğünüzü CSV ve JSON formatlarında dışa aktarabilir veya içe aktarabilirsiniz.
- ⚡ **Akıcı masaüstü deneyimi:** Ağ ve dosya işlemleri arka planda çalışır; arayüz donmaz.

## 🛠 Kullanılan Teknolojiler

- **Dil:** Python 3.10+
- **Arayüz:** PyQt6
- **Veritabanı:** SQLite (`sqlite3`, WAL modu, sürümlü migration zinciri)
- **Açık sözlük kaynakları:** Wiktionary, dictionaryapi.dev, Tatoeba, MyMemory (stdlib `urllib` ile, ek bağımlılık yok)
- **AI entegrasyonu:** `google-genai` (Gemini, yapısal `response_schema`) — isteğe bağlı
- **Yapılandırma:** `pydantic-settings`
- **Test & lint:** `pytest`, `pytest-qt`, `pytest-cov`, `ruff`

## 🚀 Kurulum ve Çalıştırma

### 1) Arch Linux / Manjaro (AUR)

Arch tabanlı sistemlerde Lexis’i AUR üzerinden kolayca kurabilirsiniz:

```bash
yay -S lexis-git
```

Paru kullanıyorsanız:

```bash
paru -S lexis-git
```

### 2) Kaynak koddan çalıştırma

Linux, macOS ve Windows üzerinde kaynak koddan çalıştırmak için:

```bash
# Repoyu klonlayın
git clone https://github.com/talhacaglar/Lexis.git
cd Lexis

# Sanal ortam oluşturun
python -m venv .venv

# Sanal ortamı aktif edin
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate

# Bağımlılıkları yükleyin
pip install -e .

# Uygulamayı başlatın
lexis
```

## ⚙️ Yapılandırma

**Zorunlu bir yapılandırma yoktur** — uygulama kurulduğu gibi kelime eklemeye hazırdır.

### İçerik kaynakları

| Kaynak | Ne verir | Anahtar |
|---|---|---|
| dictionaryapi.dev | İngilizce tanım, tür, eş/zıt anlam, IPA + telaffuz sesi | gerekmez |
| Wiktionary | Diğer dillerde tanım ve sözcük türü | gerekmez |
| Tatoeba | Örnek cümleler ve Türkçe çevirileri | gerekmez |
| MyMemory | Tanımın Türkçeye çevirisi | gerekmez |
| Google Gemini | Akıcı Türkçe tanım, kullanım notu, örnekler | **isteğe bağlı** |

Anahtarsız kaynakların sınırları: İngilizce dışındaki diller Wiktionary'den gelir ve tanımlar makine çevirisiyle Türkçeleştirilir; nadir kelimeler için örnek cümle bulunmayabilir. Daha akıcı sonuç isterseniz Gemini anahtarı ekleyin.

### Gemini anahtarı eklemek (isteğe bağlı)

1. [Google AI Studio](https://aistudio.google.com/app/apikey) üzerinden ücretsiz API anahtarınızı oluşturun.
2. Lexis'i açıp sol menüden **Ayarlar** bölümüne gidin.
3. API anahtarınızı girip kaydedin.

Anahtar yalnızca yerel veritabanınızda (`~/.lexis/lexis.db`) saklanır; Google dışında hiçbir yere gönderilmez.

## 🧪 Geliştirme

```bash
# Geliştirme bağımlılıklarıyla kur
pip install -e ".[dev]"

# Testler (PyQt6 testleri başsız çalışır)
QT_QPA_PLATFORM=offscreen pytest

# Kapsam raporu
QT_QPA_PLATFORM=offscreen pytest --cov=lexis

# Lint + biçim
ruff check lexis/ tests/
ruff format --check lexis/ tests/
```

Her push ve pull request'te GitHub Actions üzerinde Python 3.10–3.13 için lint, biçim kontrolü ve testler (kapsam eşiğiyle birlikte) otomatik çalışır. `v*` etiketi atıldığında AppImage otomatik derlenip Release'e eklenir.

Aynı kontrolleri commit anında çalıştırmak için:

```bash
pip install pre-commit && pre-commit install
```

Testler ağa çıkmaz: açık sözlük ve Gemini çağrıları sahte yanıtlarla değiştirilir.

## 📸 Ekran Görüntüleri


---

## 🇬🇧 In English

**Lexis** is a lightweight, modern, local-first desktop dictionary for language learners. Type a word and get its definition, part of speech, pronunciation, example sentences with Turkish translations, synonyms and antonyms in seconds.

**No API key required.** Content is assembled from keyless open dictionaries (Wiktionary, dictionaryapi.dev, Tatoeba, MyMemory) — real lexicographic data, not generated guesses. Add a free Gemini key if you want more fluent Turkish definitions and usage notes.

Highlights:

- 📚 **Works out of the box** — keyless content including IPA and audio pronunciation.
- 🤖 **Optional AI** via Google Gemini (structured `response_schema` output).
- 🧠 **Spaced repetition (SM-2)** with a flashcard **practice mode**; cards you fail come back later in the same session.
- 🔥 **Streak tracking** and a 7-day activity chart.
- ✎ Manual editing, undoable delete, tag filtering, light/dark themes, CSV/JSON import & export.
- 🔒 **100% local** — all data (and your key, if any) live in `~/.lexis/lexis.db`. No accounts, no servers.
- ⌨️ Shortcuts: `Ctrl+N` add · `Ctrl+P` practice · `Ctrl+1/2` pages · `Ctrl+,` settings · `Ctrl+F` search · `Esc` back; in practice `Space` reveals, `1–4` grade.

**Quick start**

```bash
git clone https://github.com/talhacaglar/Lexis.git
cd Lexis
python -m venv .venv && source .venv/bin/activate
pip install -e .
lexis
```

That's it — start adding words. Optionally open **Settings** and paste a free [Google AI Studio](https://aistudio.google.com/app/apikey) key for AI-generated content. Built with Python 3.10+, PyQt6 and SQLite.
