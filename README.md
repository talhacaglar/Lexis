# Lexis — Kişisel Sözlük & Kelime Öğrenme Uygulaması

> Yabancı dil öğrenenler için yapay zeka destekli, tam bağımsız, modern masaüstü sözlük uygulaması.

---

## ✨ Özellikler

- **Yapay Zeka Destekli İçerik** — Gemini ile anlam, eş/zıt anlamlılar, örnek cümleler, kullanım notu üretimi
- **Kişisel Sözlük** — Tüm kelimeler yerel SQLite veritabanında saklanır, internet gerekmez
- **Öğrenme Durumu Takibi** — Yeni / Öğreniyorum / Öğrendim / Tekrar Gerek
- **Etiketleme & Filtreleme** — Dilediğiniz gibi kategorize edin
- **Favoriler** — Önemli kelimeleri işaretleyin
- **Arama** — Anlık arama ve çok boyutlu filtreleme
- **İçe/Dışa Aktarma** — JSON & CSV desteği
- **14 Dil Desteği** — İngilizce, Almanca, Fransızca, İspanyolca ve daha fazlası
- **Türkçe Arayüz** — Tamamen Türkçe kullanıcı deneyimi

---

## 🚀 Kurulum

### Gereksinimler

- Python 3.10 veya üzeri
- pip veya uv paket yöneticisi

### 1. Repoyu Klonlayın

```bash
git clone https://github.com/kullanici/lexis.git
cd lexis
```

### 2. Sanal Ortam Oluşturun

```bash
python -m venv .venv
source .venv/bin/activate   # bash/zsh
source .venv/bin/activate.fish  # fish
# .venv\Scripts\activate    # Windows
```

### 3. Bağımlılıkları Kurun

```bash
pip install -e .
# Geliştirici bağımlılıkları için:
pip install -e ".[dev]"
```

### 4. API Anahtarını Yapılandırın

```bash
cp .env.example .env
nvim .env
# GEMINI_API_KEY değerini girin
```

Veya uygulamayı başlattıktan sonra **Ayarlar** ekranından API anahtarınızı girebilirsiniz.

> **API Anahtarı nereden alınır?**
> [Google AI Studio](https://aistudio.google.com/app/apikey) adresinden ücretsiz olarak alabilirsiniz.

### 5. Uygulamayı Başlatın

```bash
lexis
# veya:
python -m lexis.main
# veya aktivasyon olmadan:
./.venv/bin/lexis
```

---

## 📁 Proje Yapısı

```
lexis/
├── pyproject.toml              # Proje konfigürasyonu
├── .env.example                # Örnek environment dosyası
├── README.md
│
├── lexis/                      # Ana Python paketi
│   ├── main.py                 # Entry point
│   │
│   ├── config/
│   │   └── settings.py         # pydantic-settings konfigürasyonu
│   │
│   ├── domain/                 # Framework bağımsız iş modelleri
│   │   ├── models.py           # Word, WordStatus, WordStats
│   │   └── exceptions.py       # Domain hataları
│   │
│   ├── persistence/            # Veri erişim katmanı
│   │   ├── database.py         # SQLite bağlantısı
│   │   └── word_repository.py  # CRUD işlemleri
│   │
│   ├── services/               # Uygulama/iş mantığı katmanı
│   │   ├── ai_service.py       # Gemini API wrapper
│   │   ├── word_service.py     # Kelime yönetim servisi
│   │   └── export_service.py   # Import/Export
│   │
│   ├── workers/
│   │   └── ai_worker.py        # QThread AI worker
│   │
│   └── ui/                     # GUI katmanı (PyQt6)
│       ├── theme.py            # Renk sistemi & QSS stylesheet
│       ├── app.py              # Uygulama bootstrap
│       ├── windows/
│       │   └── main_window.py  # Ana pencere
│       ├── views/
│       │   ├── dashboard_view.py
│       │   ├── library_view.py
│       │   ├── word_detail_view.py
│       │   └── settings_view.py
│       └── widgets/
│           ├── word_card.py
│           ├── add_word_dialog.py
│           ├── loading_overlay.py
│           └── tag_badge.py
│
└── tests/
    ├── conftest.py
    ├── test_repositories.py
    └── test_word_service.py
```

---

## 🧪 Testleri Çalıştırma

```bash
pytest tests/ -v
```

---

## 🗄 Veritabanı Konumu

Varsayılan olarak veritabanı `~/.lexis/lexis.db` konumunda oluşturulur.
`.env` dosyasında `DATABASE_PATH` değişkeniyle değiştirebilirsiniz.

---

## 📤 Import / Export

- **Dışa Aktar**: Ayarlar ekranından JSON veya CSV olarak tüm kelimeleri dışa aktarın.
- **İçe Aktar**: Daha önce aktardığınız dosyayı geri yükleyin. Mevcut kelimeler atlanır.

---

## ⚙️ Konfigürasyon

| Değişken | Açıklama | Varsayılan |
|---|---|---|
| `GEMINI_API_KEY` | Google Gemini API anahtarı | — |
| `DATABASE_PATH` | Veritabanı dosya yolu | `~/.lexis/lexis.db` |
| `LOG_LEVEL` | Loglama seviyesi | `INFO` |

---

## 🛠 Geliştirme

```bash
# Bağımlılıkları kur
pip install -e ".[dev]"

# Testleri çalıştır
pytest tests/ -v

# Uygulamayı başlat
python -m lexis.main
```

---

## 📄 Lisans

MIT
