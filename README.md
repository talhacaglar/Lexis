<div align="center">
  <h1>📚 Lexis</h1>
  <p><strong>Yapay Zeka Destekli, Modern ve Kişiselleştirilmiş Sözlük Uygulaması</strong></p>
  
  <p>
    <a href="https://github.com/talhacaglar/lexis/blob/main/LICENSE">
      <img src="https://img.shields.io/github/license/talhacaglar/lexis?color=7C6EE8&style=flat-square" alt="License"/>
    </a>
    <img src="https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+"/>
    <img src="https://img.shields.io/badge/PyQt6-UI_Framework-green?style=flat-square&logo=qt" alt="PyQt6"/>
    <img src="https://img.shields.io/badge/AUR-lexis--git-1793d1?style=flat-square&logo=arch-linux" alt="AUR Package"/>
  </p>
</div>

<br>

**Lexis**, yabancı dil öğrenenler ve sözcük dağarcığını geliştirmek isteyenler için tasarlanmış bağımsız (self-hosted) ve hafif bir masaüstü uygulamasıdır. Google'ın yeni nesil **Gemini AI** altyapısını kullanarak girdiğiniz herhangi bir kelimenin türünü, detaylı tanımını, örnek cümlelerini, eş/zıt anlamlılarını ve kullanım notlarını saniyeler içinde otomatik olarak üretir.

Tüm verileriniz yerel bilgisayarınızda SQLite formatında güvende tutulur; başka hiçbir bulut servisine, aboneliğe veya webhook akışına ihtiyacınız yoktur! ✨

## ✨ Özellikler

- 🤖 **Yapay Zeka ile Otomatik İçerik:** Kelimeyi girin, gerisini Gemini AI'a bırakın. Kelimenin bağlamsal tanımından Türkçe çevirisine dek her şey otomatik oluşsun.
- 🌓 **Aydınlık & Karanlık Mod:** Tek bir tıklamayle sisteminize en uygun ve göz yormayan modern arayüze geçiş yapın. (Anında "Hot-Reload" ile)
- 🔒 **%100 Yerel Veri (Local-First):** Kelimeleriniz kendi cihazınızdaki `~/.lexis/lexis.db` SQLite veritabanında yaşar.
- 🏷️ **Etiket & Öğrenme Durumu Yönetimi:** Kelimelere özel etiketler atayın, *Yeni, Öğreniliyor, Öğrenildi* gibi durum etiketleriyle kelimeleri filtreleyin.
- 📥 **İçe / Dışa Aktarma (Export/Import):** Saniyeler içinde tüm sözlüğünüzü CSV ve JSON formatında yedekleyin veya başka cihazlara aktarın.
- ⚡ **Asenkron Mimari:** PyQt6 ve QThread bazlı altyapı sayesinde API'den cevap beklerken dahi arayüz kesinlikle donmaz.

## 🛠 Kullanılan Teknolojiler

- **Dil:** Python 3.10+
- **Arayüz (GUI):** PyQt6
- **Veritabanı:** SQLite (SQLModel & SQLAlchemy üzerinden ORM)
- **AI Entegrasyonu:** `google-genai` (Resmi ve Güncel Google SDK)
- **Konfigürasyon:** `pydantic-settings` (Tip-güvenli `.env` yönetimi)

## 🚀 Kurulum & Çalıştırma

### 1- Arch Linux / Manjaro Kullanıcıları (AUR Üzerinden En Kolay Yol)
Eğer Arch tabanlı bir sistem kullanıyorsanız, programı hiçbir bağımlılıkla uğraşmadan tek bir komutla makinenize kurabilirsiniz:
```bash
yay -S lexis-git
```
*Veya sisteminizde paket derleyicisi olarak paru varsa: `paru -S lexis-git`*

### 2- Kaynak Koddan Çalıştırma (Tüm Linux, macOS, Windows Sistemler)

Sisteminize Python yükledikten sonra terminalden sırasıyla:

```bash
# Repoyu bilgisayarınıza indirin
git clone https://github.com/talhacaglar/lexis.git
cd lexis

# Sanal ortam (virtual environment) oluşturup aktif edin
python -m venv .venv
source .venv/bin/activate  # (Windows için: .venv\Scripts\activate)

# Bağımlılıkları yükleyin
pip install -e .

# Uygulamayı başlatın
lexis
```

## ⚙️ Yapılandırma 
Uygulamayı indirdikten sonra, AI özelliklerinin çalışabilmesi için bir **Gemini API Anahtarına** ihtiyacınız vardır. (Google üzerinden almak **ücretsizdir**.)
1. [Google AI Studio](https://aistudio.google.com/app/apikey) adresinden bedava API anahtarınızı oluşturun.
2. Lexis uygulamasını açın -> Sol menüden `Ayarlar` diyin.
3. API anahtarınızı yapıştırıp Kaydet tuşuna basın. (Anahtar sadece lokalinizdeki `.env` dosyasına kaydedilecektir.)

## 📸 Ekran Görüntüleri 
*(Gelecekte buraya uygulamanın ekran görüntülerini ekleyebilirsiniz.)*
<!-- 
![Karanlık Mod Dashboard](./docs/dark_dashboard.png)
![Aydınlık Mod Kelime Kartı](./docs/light_word.png)
-->

## 📝 Lisans
Bu proje **MIT Lisansı** altında açık kaynak olarak paylaşılmıştır. Dilediğiniz gibi kullanabilir, değiştirebilir ve dağıtabilirsiniz. Detaylar için `LICENSE` dosyasına göz atabilirsiniz.
