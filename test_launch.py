"""Запуск игры из тестовой папки (после test_install.py), ждём загрузку модов и закрываем."""
import os, time
import mf_launcher as L
T = os.path.expanduser("~/.cache/mf-launcher-test")
L.BASE, L.GAME = T, os.path.join(T, "game")
L.STATE_FILE = os.path.join(T, "pack-state.json")
vid = L.load(L.STATE_FILE, {})["version"]
acc, tok = L.session(L.offline_account("MFTest"))
p = L.launch(vid, acc, tok, 3)
log = os.path.join(T, "last-launch.log")
for i in range(150):
    time.sleep(1)
    s = open(log, errors="replace").read()
    if p.poll() is not None or "Sound engine started" in s or "Created: " in s and "textures" in s:
        break
print("exit" if p.poll() is not None else "running", i, "s")
s = open(log, errors="replace").read()
for l in s.splitlines():
    if any(k in l for k in ("Loading Minecraft", "Loading ", "Sound engine", "Setting user", "ERROR", "Exception", "mods")):
        print(l[:160])
p.terminate(); time.sleep(3); p.kill()
