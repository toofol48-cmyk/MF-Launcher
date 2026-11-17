#!/bin/bash
# Перезапуск игры из MF-Launcher с новейшей версией сборки (для обновлений модов без ручных кликов).
cd "$(dirname "$0")"
P=$(pgrep -u "$USER" -n gnome-shell)
eval "$(tr '\0' '\n' < /proc/$P/environ | grep -E '^(DISPLAY|XAUTHORITY|WAYLAND_DISPLAY|XDG_RUNTIME_DIR|DBUS_SESSION_BUS_ADDRESS|LANG)=' | sed 's/^/export /')"
.venv/bin/python - <<'E'
import time, os, mf_launcher as L
pid = L.game_pid()
if pid:
    L.stop_game(pid)
    for _ in range(60):
        if not L.game_pid(): break
        time.sleep(1)
cfg = L.load(L.CFG_FILE, {})
state = L.load(L.STATE_FILE, {})
v = L.list_versions()[0]
L.PACK_KEY = cfg.get("pack_key", "")
full = bool(L.PACK_KEY)
if v["tag"] != state.get("tag") or full and not state.get("full"):
    vid, kept = L.install_pack(v, lambda s: None, lambda p: None, full)
    print("сборка", v["tag"], "полная" if full else "без пароля", "сохранено:", len(kept))
else:
    vid = state["version"]
acc, tok = L.session(cfg["account"])
cfg["account"] = acc; L.save(L.CFG_FILE, cfg)
L.launch(vid, acc, tok, cfg.get("ram", 4))
print("игра запущена")
E
