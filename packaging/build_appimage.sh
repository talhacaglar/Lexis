#!/usr/bin/env bash
# build_appimage.sh - Lexis AppImage oluşturma scripti
# Kullanım: ./packaging/build_appimage.sh

# -u: tanımsız değişken hata versin, pipefail: pipe içindeki hata yutulmasın.
set -euo pipefail

APP_NAME="lexis"
APP_DIR="AppDir"
DIST_DIR="dist"

# appimagetool sabit bir sürüme pinlenir: "continuous" her indirmede değişebilir
# ve derlemeyi tekrarlanabilir olmaktan çıkarır.
APPIMAGETOOL_VERSION="${APPIMAGETOOL_VERSION:-1.9.0}"
APPIMAGETOOL_URL="https://github.com/AppImage/appimagetool/releases/download/${APPIMAGETOOL_VERSION}/appimagetool-x86_64.AppImage"

echo "🚀 $APP_NAME AppImage derlemesi başlıyor..."

# 1. Gerekli araçları hazırla
if command -v appimagetool &> /dev/null; then
    APPIMAGETOOL="appimagetool"
else
    echo "⚠️ appimagetool bulunamadı, indiriliyor (sürüm $APPIMAGETOOL_VERSION)..."
    curl -fsSL "$APPIMAGETOOL_URL" -o appimagetool
    chmod +x appimagetool
    APPIMAGETOOL="./appimagetool"
fi

if ! command -v pyinstaller &> /dev/null; then
    # Hata vermek yerine kur: AUR PKGBUILD zaten böyle yapıyor, script de
    # CI'da elle hazırlık gerektirmeden çalışsın.
    echo "📥 pyinstaller bulunamadı, kuruluyor..."
    python -m pip install --quiet pyinstaller
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
