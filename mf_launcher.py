#!/usr/bin/env python3
"""MF-Launcher — простой лаунчер сборки «Не мой сервер».
Версии сборки = релизы GitHub с тегом pack-* (файл .mrpack). Настройки игрока не трогаются:
файл из сборки перезаписывается, только если игрок его не менял (сверка с тем, что ставили в прошлый раз)."""
import hashlib, http.server, io, json, os, queue, shutil, subprocess, sys, threading, urllib.parse, urllib.request, uuid, webbrowser, zipfile
import tkinter as tk
from tkinter import messagebox, ttk
import minecraft_launcher_lib as mll

REPO = "toofol48-cmyk/MF-Launcher"          # где лежат релизы сборки
TITLE = "Не мой сервер"
MS_CLIENT_ID = ""                    # Azure-приложение, одобренное Mojang; пусто = вход по лицензии выключен
MS_REDIRECT = "http://localhost:43123/callback"
UA = {"User-Agent": "MF-Launcher"}

BASE = os.path.join(os.environ["APPDATA"], "MF-Launcher") if os.name == "nt" else os.path.expanduser("~/.local/share/MF-Launcher")
GAME = os.path.join(BASE, "game")
CACHE = os.path.join(BASE, "cache")
CFG_FILE = os.path.join(BASE, "launcher.json")
STATE_FILE = os.path.join(BASE, "pack-state.json")


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f: return json.load(f)
    except (OSError, ValueError): return default

def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(path + ".tmp", path)

def sha1_file(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def http_get(url, timeout=60):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout)


# ─── Версии сборки (релизы GitHub) ───────────────────────────────────────
def list_versions():
    """[{tag, name, notes, url}] от новой к старой."""
    data = json.load(http_get(f"https://api.github.com/repos/{REPO}/releases?per_page=100", 20))
    out = []
    for r in data:
        asset = next((a for a in r.get("assets", []) if a["name"].endswith(".mrpack")), None)
        if r["tag_name"].startswith("pack-") and asset and not r.get("draft"):
            out.append({"tag": r["tag_name"], "name": r["tag_name"][5:], "notes": r.get("body") or "",
                        "url": asset["browser_download_url"]})
    return out


def download(url, dest, sha1=None, progress=None):
    """Скачать с проверкой sha1; кэш по sha1 — откат на старую версию без повторной загрузки."""
    if sha1:
        cached = os.path.join(CACHE, "files", sha1)
        if os.path.exists(cached):
            return cached
        dest = cached
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    h = hashlib.sha1()
    with http_get(url, 120) as r, open(dest + ".part", "wb") as f:
        total, done = int(r.headers.get("Content-Length") or 0), 0
        for b in iter(lambda: r.read(1 << 16), b""):
            f.write(b); h.update(b); done += len(b)
            if progress and total: progress(done / total)
    if sha1 and h.hexdigest() != sha1:
        os.remove(dest + ".part")
        raise RuntimeError(f"Файл повреждён при загрузке: {url}")
    os.replace(dest + ".part", dest)
    return dest


def install_pack(ver, status, progress):
    """Ставит версию сборки поверх папки игры. Возвращает id версии для запуска."""
    status(f"Загрузка сборки {ver['name']}…")
    mrpack = download(ver["url"], os.path.join(CACHE, "packs", ver["tag"] + ".mrpack"), progress=progress)
    z = zipfile.ZipFile(mrpack)
    index = json.loads(z.read("modrinth.index.json"))
    mc, loader = index["dependencies"]["minecraft"], index["dependencies"]["fabric-loader"]

    # что должно лежать в папке игры: путь -> (sha1, откуда взять)
    want = {}
    for f in index["files"]:
        if f.get("env", {}).get("client") != "unsupported":
            want[f["path"]] = (f["hashes"]["sha1"], ("url", f["downloads"][0]))
    for n in z.namelist():
        if n.startswith(("overrides/", "client-overrides/")) and not n.endswith("/"):
            rel = n.split("/", 1)[1]
            want[rel] = (hashlib.sha1(z.read(n)).hexdigest(), ("zip", n))
    force = set(z.read("overrides/mf-force.txt").decode().split()) if "overrides/mf-force.txt" in z.namelist() else set()

    old = load(STATE_FILE, {}).get("files", {})
    kept, items = [], list(want.items())
    for i, (rel, (sha, (kind, src))) in enumerate(items):
        progress(i / len(items))
        status(f"Файлы сборки: {i + 1}/{len(items)}")
        path = os.path.join(GAME, *rel.split("/"))
        if os.path.exists(path):
            cur = sha1_file(path)
            if cur == sha:
                continue
            # игрок менял этот файл (настройки) — не трогаем, кроме модов и файлов из mf-force.txt
            if cur != old.get(rel) and not rel.startswith("mods/") and rel not in force:
                kept.append(rel)
                continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if kind == "url":
            shutil.copyfile(download(src, None, sha), path)
        else:
            with open(path, "wb") as f: f.write(z.read(src))
    # убрать то, что было в прошлой версии сборки и пропало из новой (если игрок не менял)
    for rel, sha in old.items():
        path = os.path.join(GAME, *rel.split("/"))
        if rel not in want and os.path.exists(path) and (rel.startswith("mods/") or sha1_file(path) == sha):
            os.remove(path)

    status(f"Minecraft {mc} + Fabric {loader}…")
    vid = f"fabric-loader-{loader}-{mc}"
    vjson = os.path.join(GAME, "versions", vid, vid + ".json")
    if not os.path.exists(vjson):
        prof = http_get(f"https://meta.fabricmc.net/v2/versions/loader/{mc}/{loader}/profile/json").read()
        os.makedirs(os.path.dirname(vjson), exist_ok=True)
        with open(vjson, "wb") as f: f.write(prof)
    cb = {"setStatus": status, "setProgress": lambda v: cb.__setitem__("cur", v) or progress(v / max(cb.get("max", 1), 1)),
          "setMax": lambda m: cb.__setitem__("max", m)}
    mll.install.install_minecraft_version(vid, GAME, callback=cb)

    save(STATE_FILE, {"tag": ver["tag"], "version": vid, "files": {r: s for r, (s, _) in want.items()}})
    return vid, kept


# ─── Вход ────────────────────────────────────────────────────────────────
def offline_account(name):
    # тот же UUID, что даёт ванильный сервер в офлайн-режиме
    return {"type": "offline", "name": name, "id": uuid.UUID(bytes=_offline_uuid(name)).hex}

def _offline_uuid(name):
    b = bytearray(hashlib.md5(("OfflinePlayer:" + name).encode()).digest())
    b[6] = (b[6] & 0x0F) | 0x30; b[8] = (b[8] & 0x3F) | 0x80
    return bytes(b)


def microsoft_login():
    """Браузер -> localhost:43123 ловит код -> аккаунт с refresh-токеном."""
    url, state, verifier = mll.microsoft_account.get_secure_login_data(MS_CLIENT_ID, MS_REDIRECT)
    got = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            got["url"] = "http://localhost:43123" + self.path
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
            self.wfile.write("<h2>Готово, вернись в MF-Launcher</h2>".encode())
        def log_message(self, *a): pass

    srv = http.server.HTTPServer(("127.0.0.1", 43123), H)
    srv.timeout = 300
    webbrowser.open(url)
    for _ in range(20):                       # браузер может дёрнуть /favicon.ico — ждём именно ответ входа
        srv.handle_request()                  # каждое ожидание до 5 минут
        if "code=" in got.get("url", "") or "error=" in got.get("url", "") or "url" not in got:
            break
        got.pop("url")
    srv.server_close()
    code = mll.microsoft_account.parse_auth_code_url(got.get("url", ""), state)
    r = mll.microsoft_account.complete_login(MS_CLIENT_ID, None, MS_REDIRECT, code, verifier)
    return {"type": "ms", "name": r["name"], "id": r["id"], "refresh": r["refresh_token"]}


def session(acc):
    """Свежий токен для запуска (лицензия) или пустой (без лицензии)."""
    if acc["type"] != "ms":
        return acc, "0"
    r = mll.microsoft_account.complete_refresh(MS_CLIENT_ID, None, MS_REDIRECT, acc["refresh"])
    acc = dict(acc, name=r["name"], id=r["id"], refresh=r["refresh_token"])
    return acc, r["access_token"]


def launch(vid, acc, token, ram_gb):
    opts = {"username": acc["name"], "uuid": acc["id"], "token": token, "gameDirectory": GAME,
            "launcherName": "MF-Launcher", "launcherVersion": "1",
            "jvmArguments": [f"-Xmx{ram_gb}G", f"-Xms{min(ram_gb, 1)}G"]}
    cmd = mll.command.get_minecraft_command(vid, GAME, opts)
    flags = 0x08000000 if os.name == "nt" else 0          # Windows: без чёрного окна консоли
    log = open(os.path.join(BASE, "last-launch.log"), "w", encoding="utf-8")
    return subprocess.Popen(cmd, cwd=GAME, stdout=log, stderr=subprocess.STDOUT, creationflags=flags)


# ─── Окно ────────────────────────────────────────────────────────────────
BG, PANEL, FG, DIM, ACCENT = "#17191c", "#22262b", "#e8e8e8", "#8a9099", "#3fa34d"

class App:
    def __init__(self):
        self.cfg = load(CFG_FILE, {"ram": 4})
        self.versions, self.busy, self.q = [], False, queue.Queue()
        r = self.root = tk.Tk()
        r.title("MF-Launcher"); r.configure(bg=BG); r.geometry("440x380"); r.resizable(False, False)
        from tkinter import font as tkfont
        fam = next((f for f in ("Segoe UI", "Noto Sans", "Cantarell", "DejaVu Sans") if f in tkfont.families()), "TkDefaultFont")
        self.F = lambda size=10, bold=False: (fam, size, "bold") if bold else (fam, size)
        r.option_add("*Font", self.F())
        st = ttk.Style(r); st.theme_use("clam")
        st.configure("TCombobox", fieldbackground=PANEL, background=PANEL, foreground=FG, arrowcolor=FG)
        st.map("TCombobox", fieldbackground=[("readonly", PANEL)], foreground=[("readonly", FG)])
        st.configure("TProgressbar", troughcolor=PANEL, background=ACCENT, bordercolor=BG)
        r.option_add("*TCombobox*Listbox.background", PANEL); r.option_add("*TCombobox*Listbox.foreground", FG)

        tk.Label(r, text=TITLE, bg=BG, fg=FG, font=self.F(20, True)).pack(pady=(18, 2))
        tk.Label(r, text="MF-Launcher", bg=BG, fg=DIM).pack()
        self.acc_box = tk.Frame(r, bg=BG); self.acc_box.pack(pady=14, fill="x", padx=30)

        row = tk.Frame(r, bg=BG); row.pack(fill="x", padx=30)
        tk.Label(row, text="Версия сборки", bg=BG, fg=DIM).pack(side="left")
        self.ram = ttk.Combobox(row, state="readonly", width=6, values=[f"{g} ГБ" for g in (2, 3, 4, 6, 8, 12)])
        self.ram.set(f"{self.cfg.get('ram', 4)} ГБ"); self.ram.pack(side="right")
        tk.Label(row, text="Память", bg=BG, fg=DIM).pack(side="right", padx=6)
        self.ver = ttk.Combobox(r, state="readonly"); self.ver.pack(fill="x", padx=30, pady=4)
        self.ver.bind("<<ComboboxSelected>>", lambda e: self.show_notes())
        self.notes = tk.Label(r, text="", bg=BG, fg=DIM, wraplength=380, justify="left", anchor="w", height=2)
        self.notes.pack(fill="x", padx=30)

        self.play = tk.Button(r, text="ИГРАТЬ", command=self.on_play, bg=ACCENT, fg="white", activebackground="#4cbb5b",
                              font=self.F(15, True), relief="flat", bd=0, cursor="hand2")
        self.play.pack(fill="x", padx=30, pady=(10, 6), ipady=6)
        self.bar = ttk.Progressbar(r, maximum=1.0); self.bar.pack(fill="x", padx=30)
        self.status = tk.Label(r, text="", bg=BG, fg=DIM, wraplength=380); self.status.pack(pady=4)

        self.draw_account()
        self.run(self.load_versions)
        r.after(100, self.poll)

    # фоновые задачи: всё, что качает или ждёт, — не в потоке окна
    def run(self, fn, *a):
        self.busy = True; self.play.config(state="disabled")
        def work():
            try: fn(*a)
            except Exception as e: self.ui(lambda: messagebox.showerror("MF-Launcher", str(e) or type(e).__name__))
            finally: self.ui(self.done)
        threading.Thread(target=work, daemon=True).start()

    def ui(self, fn): self.q.put(fn)
    def set_status(self, s): self.ui(lambda: self.status.config(text=s))
    def set_progress(self, v): self.ui(lambda: self.bar.config(value=v))
    def done(self): self.busy = False; self.play.config(state="normal")

    def poll(self):
        while not self.q.empty(): self.q.get()()
        self.root.after(100, self.poll)

    # ─── аккаунт ───
    def draw_account(self):
        for w in self.acc_box.winfo_children(): w.destroy()
        acc = self.cfg.get("account")
        if acc:
            kind = "лицензия" if acc["type"] == "ms" else "без лицензии"
            tk.Button(self.acc_box, text="Выйти", command=self.logout, bg=PANEL, fg=FG, relief="flat").pack(side="right")
            tk.Label(self.acc_box, text=f"{acc['name']}  ·  {kind}", bg=BG, fg=FG, font=self.F(11), anchor="w").pack(side="left", fill="x", expand=True)
            return
        self.nick = tk.Entry(self.acc_box, bg=PANEL, fg=FG, insertbackground=FG, relief="flat", font=self.F(11))
        self.nick.insert(0, self.cfg.get("last_nick", "")); self.nick.pack(fill="x", ipady=4)
        b = tk.Frame(self.acc_box, bg=BG); b.pack(fill="x", pady=(6, 0))
        b.columnconfigure((0, 1), weight=1, uniform="b")
        tk.Button(b, text="Войти без лицензии", command=self.login_offline, bg=PANEL, fg=FG, relief="flat").grid(row=0, column=0, sticky="ew", padx=(0, 3))
        tk.Button(b, text="Войти в лицензию", command=self.login_ms, bg=PANEL, fg=FG, relief="flat").grid(row=0, column=1, sticky="ew", padx=(3, 0))

    def login_offline(self):
        n = self.nick.get().strip()
        if not (3 <= len(n) <= 16 and all(c.isascii() and (c.isalnum() or c == "_") for c in n)):
            return messagebox.showwarning("MF-Launcher", "Ник: 3–16 символов, латиница, цифры и _")
        self.cfg.update(account=offline_account(n), last_nick=n); save(CFG_FILE, self.cfg); self.draw_account()

    def login_ms(self):
        if not MS_CLIENT_ID:
            return messagebox.showinfo("MF-Launcher", "Вход в лицензию пока не подключён — заходи без лицензии.")
        def go():
            self.set_status("Войди в аккаунт Microsoft в браузере…")
            acc = microsoft_login()
            self.cfg["account"] = acc; save(CFG_FILE, self.cfg)
            self.ui(self.draw_account); self.set_status("")
        self.run(go)

    def logout(self):
        self.cfg.pop("account", None); save(CFG_FILE, self.cfg); self.draw_account()

    # ─── версии ───
    def label(self, v):
        cur = load(STATE_FILE, {}).get("tag")
        tags = [v["name"]]
        if v is self.versions[0]: tags.append("новейшая")
        if v["tag"] == cur: tags.append("установлена")
        return tags[0] + (f"  ({', '.join(tags[1:])})" if tags[1:] else "")

    def load_versions(self):
        self.set_status("Проверяю версии сборки…")
        try:
            vs = list_versions()
        except Exception:
            vs = []
        def show():
            cur = load(STATE_FILE, {}).get("tag")
            self.versions = vs
            if not vs:
                self.status.config(text="Нет связи с GitHub" + (" — можно играть в установленную" if cur else ""))
                self.ver.config(values=[cur[5:] + "  (установлена)"] if cur else []); self.ver.current(0) if cur else None
                return
            self.ver.config(values=[self.label(v) for v in vs])
            i = next((k for k, v in enumerate(vs) if v["tag"] == cur), 0)
            self.ver.current(i); self.show_notes(); self.status.config(text="")
            if cur and i > 0 and vs[0]["tag"] != self.cfg.get("skipped"):
                if messagebox.askyesno("Обновление", f"Вышла новая версия сборки {vs[0]['name']}.\n\n{vs[0]['notes'][:400]}\n\nОбновить?\n(настройки и входы сохранятся)"):
                    self.ver.current(0); self.show_notes()
                else:
                    self.cfg["skipped"] = vs[0]["tag"]; save(CFG_FILE, self.cfg)
        self.ui(show)

    def show_notes(self):
        i = self.ver.current()
        self.notes.config(text=self.versions[i]["notes"][:200] if 0 <= i < len(self.versions) else "")

    # ─── играть ───
    def on_play(self):
        acc = self.cfg.get("account")
        if not acc:
            return messagebox.showwarning("MF-Launcher", "Сначала войди: введи ник и нажми «Войти без лицензии»")
        self.cfg["ram"] = int(self.ram.get().split()[0]); save(CFG_FILE, self.cfg)
        i = self.ver.current()
        target = self.versions[i] if 0 <= i < len(self.versions) else None
        self.run(self.play_worker, acc, target)

    def play_worker(self, acc, target):
        state = load(STATE_FILE, {})
        if target and target["tag"] != state.get("tag"):
            vid, kept = install_pack(target, self.set_status, self.set_progress)
            self.ui(lambda: self.ver.config(values=[self.label(v) for v in self.versions]))
        elif state.get("version"):
            vid = state["version"]
        else:
            raise RuntimeError("Сборка не установлена, а GitHub недоступен. Проверь интернет.")
        self.set_status("Вход…")
        acc, token = session(acc)
        self.cfg["account"] = acc; save(CFG_FILE, self.cfg)
        self.set_status("Запуск игры…"); self.set_progress(1.0)
        launch(vid, acc, token, self.cfg["ram"])
        self.set_status("Игра запущена — лаунчер можно закрыть")


if __name__ == "__main__":
    os.makedirs(GAME, exist_ok=True)
    App().root.mainloop()
