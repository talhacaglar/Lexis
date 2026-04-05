#!/usr/bin/env bash
# Lexis kurulum scripti

set -e

echo "🔤 Lexis kurulumu başlıyor..."

# Sanal ortam oluştur
python -m venv .venv
echo "✓ Sanal ortam oluşturuldu"

# Bağımlılıkları kur
.venv/bin/pip install -e ".[dev]" --quiet
echo "✓ Bağımlılıklar kuruldu"

# .env dosyasını oluştur (yoksa)
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✓ .env dosyası oluşturuldu — lütfen GEMINI_API_KEY değerinizi girin"
else
    echo "ℹ .env dosyası zaten mevcut"
fi

echo ""
echo "✅ Kurulum tamamlandı!"
echo ""
echo ".env dosyasını düzenlemek için:"
echo "  nvim .env"
echo ""
echo "Başlatmak için:"
echo "  Bash/Zsh: source .venv/bin/activate && lexis"
echo "  fish:     source .venv/bin/activate.fish; and lexis"
echo "  Doğrudan: ./.venv/bin/lexis"
