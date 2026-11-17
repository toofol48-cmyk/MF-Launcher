#!/bin/bash
# Выложить текущую сборку из Prism («Не мой сервер») новой версией для MF-Launcher.
#   ./publish.sh "что нового"
# Личное (входы, карта, сервера, миры) не попадает — исключения в ~/Code/mods/_tmp/export_pack.py
set -e
REPO=toofol48-cmyk/MF-Launcher
V=$(date +%Y.%m.%d-%H%M)
D=$(mktemp -d)
MF_OUT="$D" MF_VERSION="$V" MF_MRPACK_ONLY=1 python3 ~/Code/mods/_tmp/export_pack.py
mv "$D/Не мой сервер.mrpack" "$D/nms-$V.mrpack"
gh release create "pack-$V" "$D/nms-$V.mrpack" --repo "$REPO" --title "Сборка $V" --notes "${1:-Обновление сборки}"
rm -rf "$D"
echo "Готово: версия $V — друзьям предложит обновиться при запуске лаунчера"
