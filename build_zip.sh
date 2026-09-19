#!/bin/sh
# Собирает dist/project_utm_crs-<версия>.zip для «Модули → Установить из ZIP».
set -e
cd "$(dirname "$0")"
VERSION=$(sed -n 's/^version=//p' project_utm_crs/metadata.txt)
mkdir -p dist
ZIP="dist/project_utm_crs-$VERSION.zip"
rm -f "$ZIP"
zip -qr "$ZIP" project_utm_crs -x '*__pycache__*' '*.pyc' '*.DS_Store'
echo "$ZIP"
