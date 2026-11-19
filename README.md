# MF-Launcher

A small open-source Minecraft: Java Edition launcher for a private group of friends who play our Fabric modpack ("Не мой сервер").

> **MF-Launcher is an independent, unofficial, third-party application. It is not affiliated with, endorsed or approved by Mojang Studios, Microsoft or Minecraft.** "Minecraft" is a trademark of Mojang Synergies AB; it is used here only to say which game the launcher starts.

**What it does**
- **Requires a legitimate Minecraft: Java Edition account.** The only way to play is to sign in with your own Microsoft account. There is no offline / username-only mode, no alternative authentication service and no authlib-injector.
- **Sign-in flow:** OAuth 2.0 authorization code + PKCE in the player's system browser (official Microsoft sign-in page) → redirect to `http://localhost:43123/callback` on the player's PC → Xbox Live (`user.auth.xboxlive.com`) → XSTS → `login_with_xbox` → **ownership check** via `entitlements/mcstore` (and `minecraft/profile`). If the account does not own Minecraft: Java Edition, the game is not started. Ownership is checked again on every launch.
- **Account data:** the launcher never sees the password. Only the refresh token is stored, locally on the player's PC (`%APPDATA%\MF-Launcher` / `~/.local/share/MF-Launcher`); nothing is sent anywhere except Microsoft/Mojang services. No telemetry, no ads, free, no commercial use.
- **Game files:** Minecraft itself is downloaded from Mojang's official servers (version manifest + libraries/assets), not redistributed by us. Fabric loader comes from Fabric's servers.
- **Modpack:** installs our Fabric modpack ("Не мой сервер") from GitHub Releases (`pack-*`, `.mrpack`). Players can update or roll back; their own settings are kept.
- **No capes:** the launcher does not sell, distribute or enable any capes. Only capes the signed-in player legitimately owns (shown by the game itself) are visible.
- Azure app ID: `b782a2f5-5fb7-4468-8ea3-5e9c57b76e03` (registered by the author, used only by this launcher). Source code: this repository.

Built with [minecraft-launcher-lib](https://codeberg.org/JakobDev/minecraft-launcher-lib), Python/Tk, PyInstaller.

**Download:** [Releases](../../releases) → `MF-Launcher.exe` (Windows) or `MF-Launcher` (Linux).

---

## По-русски

Простой лаунчер сборки «Не мой сервер»: вход через Microsoft (нужна лицензия Minecraft: Java Edition), выбор версии сборки, «Играть». Неофициальный, с Mojang/Microsoft не связан.

- **Обновления:** при запуске лаунчер предлагает новую версию сборки; в списке можно выбрать любую старую (откат).
- **Настройки не теряются:** файл сборки перезаписывается, только если игрок его не менял. Управление (`options.txt`), входы в Google/YouTube (`config/mf-browser`, `mf-google`, `mf-tube`), свои моды, миры и сервера остаются.
- Принудительно обновить конфиг у всех: положить его путь в `mf-force.txt` в корне сборки.

Папка игры: `%APPDATA%\MF-Launcher\game` (Windows), `~/.local/share/MF-Launcher/game` (Linux).

**Выложить новую версию сборки:** `./publish.sh "что нового"` — берёт сборку из Prism, личное не включает.
**Выпустить новый лаунчер:** `git tag launcher-vN && git push --tags` — GitHub соберёт exe и Linux-файл.
