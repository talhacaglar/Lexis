<div align="center">
  <h1>📚 Lexis</h1>
  <p><strong>Yapay zeka destekli, modern ve kişiselleştirilmiş sözlük uygulaması</strong></p>

  <p>
    <img src="https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+" />
    <img src="https://img.shields.io/badge/PyQt6-UI_Framework-green?style=flat-square&logo=qt" alt="PyQt6" />
    <a href="https://aur.archlinux.org/packages/lexis-git">
      <img src="https://img.shields.io/badge/AUR-lexis--git-1793d1?style=flat-square&logo=arch-linux" alt="AUR Package" />
    </a>
  </p>
</div>

<br>

Lexis, yabancı dil öğrenenler ve kelime dağarcığını geliştirmek isteyenler için geliştirilmiş hafif, modern ve local-first bir masaüstü uygulamasıdır. Google Gemini AI desteği sayesinde girilen kelimelerin türünü, anlamını, örnek cümlelerini, Türkçe çevirilerini, eş ve zıt anlamlılarını ve kullanım notlarını saniyeler içinde otomatik olarak üretir.

Amaç, yalnızca “bu kelime ne demek?” sorusuna cevap vermek değil; aynı zamanda kelimenin nerede, nasıl ve hangi bağlamda kullanıldığını daha anlaşılır hale getirmektir.

Tüm veriler SQLite kullanılarak tamamen yerel olarak saklanır. Herhangi bir abonelik, ekstra sunucu ya da harici veri depolama ihtiyacı olmadan doğrudan cihazınız üzerinde çalışır. ✨

## ✨ Özellikler

- 🤖 **Yapay zeka destekli içerik üretimi:** Girilen kelimeler için otomatik anlam, kelime türü, örnek cümle, çeviri, eş anlamlı, zıt anlamlı ve kullanım notları oluşturur.
- 🌍 **Bağlam odaklı öğrenme:** Kelimeleri yalnızca tanım olarak değil, gerçek kullanım örnekleriyle birlikte anlamayı kolaylaştırır.
- 🌓 **Aydınlık ve karanlık tema desteği:** Tek tıkla tema değiştirebilir, daha konforlu bir kullanım deneyimi elde edebilirsiniz.
- 🔒 **%100 yerel veri saklama:** Tüm kayıtlar cihazınızdaki `~/.lexis/lexis.db` veritabanında tutulur.
- 🏷️ **Etiket ve öğrenme durumu yönetimi:** Kelimelere özel etiketler ekleyebilir; Yeni, Öğreniliyor ve Öğrenildi gibi durumlara göre filtreleme yapabilirsiniz.
- 📥 **İçe / dışa aktarma desteği:** Sözlüğünüzü CSV ve JSON formatlarında dışa aktarabilir veya içe aktarabilirsiniz.
- ⚡ **Akıcı masaüstü deneyimi:** PyQt6 ve QThread tabanlı yapı sayesinde AI işlemleri sırasında arayüz donmadan çalışmaya devam eder.

## 🛠 Kullanılan Teknolojiler

- **Dil:** Python 3.10+
- **Arayüz:** PyQt6
- **Veritabanı:** SQLite
- **ORM:** SQLModel & SQLAlchemy
- **AI entegrasyonu:** `google-genai`
- **Yapılandırma:** `pydantic-settings`

## 🚀 Kurulum ve Çalıştırma

### 1) Arch Linux / Manjaro (AUR)

Arch tabanlı sistemlerde Lexis’i AUR üzerinden kolayca kurabilirsiniz:

```bash
yay -S lexis-git
````

Paru kullanıyorsanız:

```bash
paru -S lexis-git
```

### 2) Kaynak koddan çalıştırma

Linux, macOS ve Windows üzerinde kaynak koddan çalıştırmak için:

```bash
# Repoyu klonlayın
git clone https://github.com/talhacaglar/lexis.git
cd lexis

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

AI özelliklerini kullanabilmek için bir Gemini API anahtarı gereklidir.

1. [Google AI Studio](https://aistudio.google.com/app/apikey) üzerinden ücretsiz API anahtarınızı oluşturun.
2. Lexis uygulamasını açın.
3. Sol menüden **Ayarlar** bölümüne gidin.
4. API anahtarınızı girip kaydedin.

Anahtar yalnızca yerel ortamınızda saklanır.

## 📸 Ekran Görüntüleri

<img width="1618" height="917" alt="image" src="https://github.com/user-attachments/assets/e9c8f180-a8ec-4bed-9f37-d751030b535b" />
<img width="1908" height="1044" alt="Lexis screenshot 1" src="https://github.com/user-attachments/assets/40040253-f286-4f39-af2d-529d046b2a3f" />
<img width="1908" height="1044" alt="Lexis screenshot 2" src="https://github.com/user-attachments/assets/86088142-e4cc-4a05-aac4-5da7f3713b89" />
<img width="1600" height="875" alt="Lexis screenshot 3" src="https://github.com/user-attachments/assets/00c6c47a-8d64-4efe-822f-0cf08722517c" />
```

İstersen bir sonraki mesajda bunun daha “global README” tarzında İngilizce versiyonunu da verebilirim.
