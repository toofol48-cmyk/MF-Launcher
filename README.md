# MF-Launcher

A small open-source Minecraft: Java Edition launcher for a private group of friends who play our Fabric modpack ("Не мой сервер").

**What it does**
- Sign in with your own Microsoft account (OAuth 2.0 authorization code + PKCE in the system browser; no passwords or client secrets handled, tokens stored only locally on the player's PC), or play offline.
- Installs Minecraft, Fabric and the modpack; modpack versions are GitHub Releases (`pack-*`, `.mrpack` format). Players can update or roll back to any older version.
- Keeps players' settings across updates: a pack file is replaced only if the player hasn't changed it.
- Launches the game. That's all — no ads, no telemetry, no commercial use.

Microsoft/Minecraft services used: Xbox Live sign-in → `login_with_xbox`, `entitlements/mcstore`, `minecraft/profile` (via [minecraft-launcher-lib](https://codeberg.org/JakobDev/minecraft-launcher-lib)).

**Download:** [Releases](../../releases) → `MF-Launcher.exe` (Windows) or `MF-Launcher` (Linux).

---

## По-русски

Простой лаунчер сборки «Не мой сервер»: вход (лицензия / без лицензии), выбор версии сборки, «Играть».

- **Обновления:** при запуске лаунчер предлагает новую версию сборки; в списке можно выбрать любую старую (откат).
- **Настройки не теряются:** файл сборки перезаписывается, только если игрок его не менял. Управление (`options.txt`), входы в Google/YouTube (`config/mf-browser`, `mf-google`, `mf-tube`), свои моды, миры и сервера остаются.
- Принудительно обновить конфиг у всех: положить его путь в `mf-force.txt` в корне сборки.

Папка игры: `%APPDATA%\MF-Launcher\game` (Windows), `~/.local/share/MF-Launcher/game` (Linux).

**Выложить новую версию сборки:** `./publish.sh "что нового"` — берёт сборку из Prism, личное не включает.
**Выпустить новый лаунчер:** `git tag launcher-vN && git push --tags` — GitHub соберёт exe и Linux-файл.
