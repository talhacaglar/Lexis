#!/usr/bin/env bash
# build_appimage.sh - Lexis AppImage oluşturma scripti
# Kullanım: ./packaging/build_appimage.sh

set -e

APP_NAME="lexis"
APP_DIR="AppDir"
DIST_DIR="dist"

echo "🚀 $APP_NAME AppImage derlemesi başlıyor..."

# 1. Gerekli araçları kontrol et
if ! command -v appimagetool &> /dev/null; then
    echo "⚠️ appimagetool bulunamadı! İndiriliyor..."
    wget "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage" -O appimagetool
    chmod +x appimagetool
    APPIMAGETOOL="./appimagetool"
else
    APPIMAGETOOL="appimagetool"
fi

if ! command -v pyinstaller &> /dev/null; then
    echo "❌ pyinstaller bulunamadı. Lütfen sanal ortamı aktif edin veya pyinstaller'ı kurun:"
    echo "   pip install pyinstaller"
    exit 1
fi

# 2. Önceki build loglarını temizle
rm -rf build/ $DIST_DIR/$APP_NAME $APP_DIR

# 3. PyInstaller ile derle (onedir modunda)
echo "📦 PyInstaller ile derleniyor..."
pyinstaller --name="$APP_NAME" \
            --windowed \
            --onedir \
            --noconfirm \
            --hidden-import="lexis.ui.views" \
            --hidden-import="lexis.ui.widgets" \
            --hidden-import="lexis.workers" \
            --clean \
            lexis/main.py

# 4. AppDir yapısını oluştur
echo "📂 AppDir oluşturuluyor..."
mkdir -p "$APP_DIR/usr/bin"
mkdir -p "$APP_DIR/usr/share/applications"
mkdir -p "$APP_DIR/usr/share/icons/hicolor/scalable/apps"
mkdir -p "$APP_DIR/usr/share/icons/hicolor/128x128/apps"

# PyInstaller çıktılarını AppDir içine kopyala
cp -r $DIST_DIR/$APP_NAME/* "$APP_DIR/usr/bin/"

# 5. AppImage dosyalarını kopyala
# Desktop dosyası
cp packaging/lexis.desktop "$APP_DIR/"
cp packaging/lexis.desktop "$APP_DIR/usr/share/applications/"

# İkon (Hem kök dizine hem hicolor dizinine)
if [ -f "packaging/icons/lexis.svg" ]; then
    cp packaging/icons/lexis.svg "$APP_DIR/lexis.svg"
    cp packaging/icons/lexis.svg "$APP_DIR/usr/share/icons/hicolor/scalable/apps/"
else
    touch "$APP_DIR/lexis.svg" # Placeholder
fi

if [ -f "packaging/icons/lexis.png" ]; then
    cp packaging/icons/lexis.png "$APP_DIR/lexis.png"
    cp packaging/icons/lexis.png "$APP_DIR/usr/share/icons/hicolor/128x128/apps/"
fi

# AppRun scripti
cp packaging/AppRun "$APP_DIR/"
chmod +x "$APP_DIR/AppRun"

# 6. appimagetool ile paketle
echo "🖼️ AppImage üretiliyor..."
# Eğer Linux deploy qt vs gerekiyorsa (PyQt alt kütüphaneleri için) burada linuxdeployqt kullanılabilir.
# Basit bir appimagetool çağrısı:
$APPIMAGETOOL "$APP_DIR" "$APP_NAME-x86_64.AppImage"

echo "✅ Başarılı! AppImage dosyası oluşturuldu: $APP_NAME-x86_64.AppImage"
