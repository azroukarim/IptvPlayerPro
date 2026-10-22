#!/usr/bin/env bash
# ------------------------------------------------------------
# make_zip_package.sh
#   – يجمع ملفات المصدر في أرشيف ZIP جاهز للنقل إلى جهاز Enigma2
# ------------------------------------------------------------

set -euo pipefail

PKG_NAME="IPTVPlayerPro"
VERSION="1.4.0"
SRC_ROOT="$(pwd)/src/$PKG_NAME"

if [[ ! -d "$SRC_ROOT" ]]; then
    echo "ERROR: مصدر الإضافة غير موجود: $SRC_ROOT"
    exit 1
fi

ZIP_FILE="${PKG_NAME}_${VERSION}.zip"

# احذف الأرشيف القديم إذا كان موجودًا
if [[ -f "$ZIP_FILE" ]]; then
    rm -f "$ZIP_FILE"
fi

# إنشاء الأرشيف مع استبعاد ملفات __pycache__ لتقليل الحجم
zip -r "$ZIP_FILE" \
    "src/$PKG_NAME" \
    "plugin.png" \
    "plugin.py" \
    -x "*__pycache__/*"

echo "✅ تم إنشاء $ZIP_FILE (حجم $(du -h \"$ZIP_FILE\" | cut -f1))"
