"""Проверка: установка сборки, сохранение настроек при обновлении и откате. Запуск: .venv/bin/python test_install.py <mrpack>"""
import os, sys, shutil, zipfile, json, tempfile
import mf_launcher as L

T = os.path.expanduser("~/.cache/mf-launcher-test")
L.BASE, L.GAME, L.CACHE = T, os.path.join(T, "game"), os.path.join(T, "cache")
L.CFG_FILE, L.STATE_FILE = os.path.join(T, "launcher.json"), os.path.join(T, "pack-state.json")
src = os.path.abspath(sys.argv[1])
say = lambda s: None

# версия B = та же сборка, но в ней другой options.txt, новый конфиг и без одного файла
b = os.path.join(T, "B.mrpack"); os.makedirs(T, exist_ok=True)
with zipfile.ZipFile(src) as zi, zipfile.ZipFile(b, "w") as zo:
    names = zi.namelist()
    gone = next(n for n in names if n.startswith("overrides/config/") and n.endswith(".json"))
    for n in names:
        if n == gone: continue
        d = zi.read(n)
        if n == "overrides/options.txt": d += b"\nmf_test_from_pack_B:1"
        zo.writestr(n, d)
    zo.writestr("overrides/config/mf-test-new.txt", "new in B")

A = {"tag": "pack-A", "name": "A", "url": "file://" + src}
B = {"tag": "pack-B", "name": "B", "url": "file://" + b}
G = lambda r: os.path.join(L.GAME, r)

vid, kept = L.install_pack(A, print, say)
assert os.path.exists(os.path.join(L.GAME, "versions", vid, vid + ".json")), vid
mods = sorted(os.listdir(G("mods"))); print("A:", vid, len(mods), "mods")

# игрок меняет управление и вводит данные «входа» (файлы, которых нет в сборке)
with open(G("options.txt"), "a") as f: f.write("\nkey_key.jump:key.keyboard.k")
os.makedirs(G("config/mf-browser"), exist_ok=True); open(G("config/mf-browser/cookies"), "w").write("login")
open(G("mods/friend-own-mod.jar"), "w").write("x")

vid2, kept = L.install_pack(B, print, say)
opt = open(G("options.txt")).read()
assert "key.keyboard.k" in opt and "mf_test_from_pack_B" not in opt, "управление затёрто"
assert "options.txt" in kept
assert open(G("config/mf-browser/cookies")).read() == "login"
assert os.path.exists(G("config/mf-test-new.txt")) and not os.path.exists(G(gone[len("overrides/"):]))
assert os.path.exists(G("mods/friend-own-mod.jar"))
print("B: ок, сохранено:", kept)

L.install_pack(A, print, say)          # откат
assert "key.keyboard.k" in open(G("options.txt")).read()
assert not os.path.exists(G("config/mf-test-new.txt")) and os.path.exists(G(gone[len("overrides/"):]))
assert sorted(set(os.listdir(G("mods"))) - {"friend-own-mod.jar"}) == mods
print("откат на A: ок")
