#!/usr/bin/env python3
"""
ab2_app.py - AB2 Save Editor with a friendly window (runs in your browser, on this PC only).

Start it by double-clicking AB2-Save-Editor.exe, or:  py ab2_app.py
Everything stays on your computer: a tiny server listens on 127.0.0.1 only, protected by a
random one-time token, and it shuts down when you close the page.
"""
import base64
import contextlib
import io
import json
import os
import secrets
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# A windowed .exe has no console: make print() harmless.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import ab2core as core
import json_editor as ed

TOKEN = secrets.token_urlsafe(18)
LAST_PING = {"t": None}
UI_FILE = "index.html"


def ui_path():
    root = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "ui", UI_FILE)


# ----------------------------------------------------------------------------
# API actions. Each returns a dict; raise core.CoreError for a user-facing problem.
# ----------------------------------------------------------------------------
def api_status(_):
    s = core.status()
    s["unrestricted"] = UNLOCK["on"]
    s["limits"] = {"normal": LIMITS, "unlimited": UNLIMITED}
    return s


def api_set_key(body):
    if body.get("hex"):
        core.save_key_hex(body["hex"])
    elif body.get("b64"):
        core.save_key_bytes(base64.b64decode(body["b64"]))
    else:
        raise core.CoreError("No key received.")
    ok = core.check_key_against_game()
    if ok is False:
        for n in ("xor_key.hex", "xor_key.bin"):
            try:
                os.remove(core.p(n))
            except OSError:
                pass
        raise core.CoreError("This key does not open your game's save, so it was not kept. Check it and try again.")
    return {"has_key": core.has_key(), "verified": ok}


def api_load(_):
    """Back up the game folder, copy index + save here, decrypt, and summarise."""
    core.reset_work_files()                       # never mix an earlier edit with a fresh load
    pulled = core.pull_from_game()
    core.decrypt_work()
    return {"backup": os.path.basename(pulled["backup"]), "summary": core.summarize()}


def api_view(_):
    return {"summary": core.summarize()}


def _int(v, lo, hi, default):
    try:
        n = int(float(v))
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


# Normal limits (modest). Unrestricted mode lifts them, but only after the 3-step warning below.
LIMITS = {
    "wallet": {k: ed.MAX_CURRENCY for k in ("Gems", "SecondaryCurrency", "FreeBirdTokens",
                                           "TOFExpressTickets", "TOFEntryTickets", "ArenaTickets")},
    "spell": 20, "bird_level": len(ed.LEVEL_TOKENS) - 1, "campaign": ed.MAX_LEVEL_CAP,
}
UNLIMITED = {"wallet": ed.MAX_CURRENCY, "spell": 999, "bird_level": 9999, "campaign": ed.MAX_LEVEL_CAP}
UNLOCK = {"step": 0, "on": False}
PHRASE = "its on my own"


def _norm(s):
    return "".join(ch for ch in str(s).lower().replace("'", "").replace("\u2019", "") if ch.isalpha() or ch == " ").split()


def api_unlock(body):
    """Three warnings. Step 3 needs the exact phrase typed. The page cannot skip steps."""
    step = int(body.get("step", 0))
    if body.get("off"):
        UNLOCK.update(step=0, on=False)
        return {"on": False, "step": 0}
    if step != UNLOCK["step"] + 1:
        UNLOCK["step"] = 0
        raise core.CoreError("Start again from the first warning.")
    if step == 3 and _norm(body.get("phrase", "")) != _norm(PHRASE):
        raise core.CoreError("That is not the phrase. Type exactly: " + PHRASE)
    UNLOCK["step"] = step
    UNLOCK["on"] = step == 3
    return {"on": UNLOCK["on"], "step": step}


def api_set_folder(body):
    return {"game_dir": core.set_game_dir(body.get("path", ""))}


def api_close_game(_):
    return core.close_game()


def build_preset(body):
    u = UNLOCK["on"]
    w = body.get("wallet", {})
    base = ed.SAFE_PRESET["wallet"]
    wallet = {k: _int(w.get(k), 0, ed.MAX_CURRENCY, base[k]) for k in base}
    spells_in = body.get("spells", {})
    sp_max = UNLIMITED["spell"] if u else LIMITS["spell"]
    spells = {k: _int(spells_in.get(k), 0, sp_max, ed.SAFE_PRESET["spells"][k]) for k in ed.SAFE_PRESET["spells"]}
    tiers = [t for t in body.get("hat_tiers", []) if t in ed.TIER_NAMES]
    camp = body.get("campaign_level")
    lv_max = UNLIMITED["bird_level"] if u else LIMITS["bird_level"]
    return {
        "wallet": wallet,
        "campaign_level": _int(camp, 1, ed.MAX_LEVEL_CAP, None) if camp not in (None, "", 0) else None,
        "spells": spells,
        "core_bird_level": _int(body.get("core_bird_level"), 1, lv_max, 30),
        "guest_bird_level": _int(body.get("guest_bird_level"), 1, lv_max, 15),
        "hat_tiers": tiers,
    }


def api_edit(body):
    path = core.p(core.JSON_NAME)
    if not os.path.isfile(path):
        raise core.CoreError("Load your save first (step 2).")
    preset = build_preset(body)
    core.backup_file(path, core.p(core.OLD_JSON_DIR), "decrypted_save", ".json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    save = ed.Save(data)
    ed.REPORT.clear()
    with contextlib.redirect_stdout(io.StringIO()):
        ed.apply_preset(save, preset, use_jitter=bool(body.get("natural_numbers", True)))
        ed.remove_bogus_birds(save)
    save.commit()
    core.atomic_write(path, json.dumps(data, separators=(",", ":")).encode("utf-8"))
    return {"report": list(ed.REPORT), "summary": core.summarize()}


def api_undo(_):
    r = core.undo_last_edit()
    return {"restored_from": r["restored_from"], "summary": core.summarize()}


def api_review(_):
    """Encrypt + verify, then show what changed."""
    enc = core.encrypt_work()
    return {"bytes": enc["bytes"], "diff": core.diff_saves(), "summary": core.summarize()}


def api_install(body):
    return core.push_to_game()


def api_backups(_):
    return {"backups": core.list_game_backups()}


def api_restore(body):
    return core.restore_game_backup(str(body.get("name", "")), body.get("code", ""))


def api_open_folder(_):
    path = core.base_dir()
    try:
        if os.name == "nt":
            os.startfile(path)                       # noqa
        elif sys.platform == "darwin":
            import subprocess
            subprocess.Popen(["open", path])
        else:
            import subprocess
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass
    return {"path": path}


def api_ping(_):
    LAST_PING["t"] = time.time()
    return {}


def api_quit(_):
    threading.Thread(target=lambda: (time.sleep(0.3), os._exit(0)), daemon=True).start()
    return {}


ACTIONS = {
    "status": api_status, "set_key": api_set_key, "load": api_load, "view": api_view,
    "edit": api_edit, "undo": api_undo, "review": api_review, "install": api_install,
    "backups": api_backups, "restore": api_restore, "open_folder": api_open_folder,
    "ping": api_ping, "quit": api_quit, "unlock": api_unlock, "close_game": api_close_game, "set_folder": api_set_folder,
}


# ----------------------------------------------------------------------------
# tiny local web server
# ----------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    server_version = "AB2Editor"

    def log_message(self, *a):
        pass

    def _host_ok(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost")

    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self._host_ok():
            return self._send(403, "forbidden", "text/plain")
        path, _, query = self.path.partition("?")
        if path == "/tutorial-video" and f"t={TOKEN}" in query:
            return self._video()
        if path != "/" or f"t={TOKEN}" not in query:
            return self._send(403, "Open the editor from the program window.", "text/plain")
        try:
            html = open(ui_path(), "r", encoding="utf-8").read().replace("__TOKEN__", TOKEN)
        except OSError:
            return self._send(500, "UI file missing.", "text/plain")
        LAST_PING["t"] = time.time()
        self._send(200, html, "text/html")

    def _video(self):
        fp = core.tutorial_file()
        if not fp:
            return self._send(404, "No tutorial video yet.", "text/plain")
        size = os.path.getsize(fp)
        ctype = {".mp4": "video/mp4", ".m4v": "video/mp4", ".webm": "video/webm", ".mov": "video/mp4", ".ogv": "video/ogg"}.get(os.path.splitext(fp)[1].lower(), "video/mp4")
        start, end, code = 0, size - 1, 200
        rng = self.headers.get("Range", "")
        if rng.startswith("bytes="):
            a, _, b = rng[6:].partition("-")
            try:
                start = int(a) if a else max(0, size - int(b))
                end = int(b) if (a and b) else size - 1
                end = min(end, size - 1)
                code = 206
            except ValueError:
                start, end, code = 0, size - 1, 200
        if start > end or start >= size:
            self.send_response(416); self.send_header("Content-Range", f"bytes */{size}"); self.end_headers(); return
        length = end - start + 1
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if code == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            with open(fp, "rb") as f:
                f.seek(start)
                left = length
                while left > 0:
                    chunk = f.read(min(262144, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        if not self._host_ok() or self.headers.get("X-Token") != TOKEN:
            return self._send(403, json.dumps({"ok": False, "error": "Not allowed."}))
        name = self.path.rstrip("/").rsplit("/", 1)[-1]
        fn = ACTIONS.get(name)
        if not fn:
            return self._send(404, json.dumps({"ok": False, "error": "Unknown action."}))
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > 2_000_000:
                raise core.CoreError("Request too large.")
            body = json.loads(self.rfile.read(n) or b"{}")
            result = fn(body)
            self._send(200, json.dumps({"ok": True, "data": result}))
        except core.CoreError as e:
            self._send(200, json.dumps({"ok": False, "error": str(e)}))
        except Exception as e:                                   # never crash the window
            self._send(200, json.dumps({"ok": False, "error": f"Unexpected problem: {e}"}))


def watchdog():
    """Quit when the page has been closed for a while."""
    while True:
        time.sleep(3)
        t = LAST_PING["t"]
        if t is not None and time.time() - t > 25:
            os._exit(0)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", int(os.environ.get("AB2_PORT", "0"))), Handler)
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}/?t={TOKEN}"
    threading.Thread(target=watchdog, daemon=True).start()
    if "--no-browser" not in sys.argv:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    print("AB2 Save Editor is running. Open:", url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
