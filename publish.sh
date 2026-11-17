#!/bin/bash
# Выложить текущую сборку из Prism («Не мой сервер») новой версией для MF-Launcher.
#   ./publish.sh "что нового"
# Личное (входы, карта, сервера, миры) не попадает — исключения в ~/Code/mods/_tmp/export_pack.py
set -e
REPO=toofol48-cmyk/MF-Launcher
V=$(date +%Y.%m.%d-%H%M)
D=$(mktemp -d)
P=~/Загрузки/relay-upload/mf-files                  # Fresh и A&S — не на GitHub, а на посредник (папка mf-files/ на хостинге)
before=$(ls "$P" 2>/dev/null | sort)
MF_OUT="$D" MF_PRIVATE_OUT="$P" MF_VERSION="$V" MF_MRPACK_ONLY=1 python3 ~/Code/mods/_tmp/export_pack.py
new=$(comm -13 <(echo "$before") <(ls "$P" | sort))
if [ -n "$new" ]; then echo "!!! Сначала залей на хостинг посредника в mf-files/ новые файлы:"; echo "$new"; read -p "Залил? Enter — выложить версию, Ctrl+C — отмена "; fi
mv "$D/Не мой сервер.mrpack" "$D/nms-$V.mrpack"
gh release create "pack-$V" "$D/nms-$V.mrpack" --repo "$REPO" --title "Сборка $V" --notes "${1:-Обновление сборки}"
rm -rf "$D"
echo "Готово: версия $V — друзьям предложит обновиться при запуске лаунчера"
