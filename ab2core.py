#!/usr/bin/env python3
"""
ab2core.py - everything the tools share: crypto, paths, backups, safety checks, diff, restore.

No game code is touched. This only reads/writes the save files in the game's save folder
(after backing them up) and never contacts any server.

The XOR key is NOT included in this project. Put it next to the program as xor_key.bin
(256 raw bytes) or xor_key.hex (512 hex characters), or set AB2_XOR_KEY.
"""
import datetime
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys

# ----------------------------------------------------------------------------
# constants
# ----------------------------------------------------------------------------
SAVE_NAME = "B4F59D3E9582F13D98B85102B4003E377A9434837B71846F44C05637D2613FA1"
INDEX_NAME = "index"
JSON_NAME = "decrypted_save.json"
MAGIC = b"\xab\xba"
HEADER_LEN = 36                       # newer game builds prefix every file with 36 bytes
PACKAGE = "1ED5AEA5.4160926B82DB_p2gbknwb5d8r2"

OLD_JSON_DIR = "old_json"
OLD_ENC_DIR = "old_encrypted"
GAME_BACKUP_DIR = "game_backups"


class CoreError(Exception):
    """A problem we can explain to the user in one sentence."""


# ----------------------------------------------------------------------------
# paths
# ----------------------------------------------------------------------------
def base_dir():
    """Folder of the program (next to the .exe when packaged)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def p(*parts):
    return os.path.join(base_dir(), *parts)


def settings_path():
    return os.path.join(base_dir(), "settings.json")


def load_settings():
    try:
        with open(settings_path(), "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def save_setting(key, value):
    d = load_settings()
    d[key] = value
    with open(settings_path(), "w", encoding="utf-8") as f:
        json.dump(d, f)


def default_game_dir():
    """Windows Store location. Other systems have no known default: the user picks the folder."""
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA") or os.path.expanduser(r"~\AppData\Local")
        return os.path.join(local, "Packages", PACKAGE, "LocalState", "save")
    return ""


def game_dir():
    env = os.environ.get("AB2_GAME_DIR")
    if env:
        return env
    return load_settings().get("game_dir") or default_game_dir()


def set_game_dir(path):
    path = os.path.expanduser(str(path).strip().strip('"'))
    if not path or not os.path.isdir(path):
        raise CoreError("That folder does not exist: " + path)
    save_setting("game_dir", path)
    return path


# ----------------------------------------------------------------------------
# backups: numbered + dated
# ----------------------------------------------------------------------------
def _stamp():
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def next_number(folder, stem):
    os.makedirs(folder, exist_ok=True)
    pat = re.compile(rf"^{re.escape(stem)}_(\d{{3,5}})_")
    nums = [int(m.group(1)) for f in os.listdir(folder) for m in [pat.match(f)] if m]
    return max(nums, default=0) + 1


def backup_file(src, folder, stem, ext):
    """Copy src to folder/stem_NNN_date.ext. Returns the new path."""
    n = next_number(folder, stem)
    dst = os.path.join(folder, f"{stem}_{n:03d}_{_stamp()}{ext}")
    shutil.copyfile(src, dst)
    return dst


def atomic_write(path, data):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    last = None
    for _ in range(10):                  # Windows can briefly lock files
        try:
            os.replace(tmp, path)
            return
        except PermissionError as e:
            last = e
            import time
            time.sleep(0.2)
    try:
        os.remove(tmp)
    except OSError:
        pass
    raise CoreError(f"Could not write {os.path.basename(path)} (is the game still running?): {last}")


# ----------------------------------------------------------------------------
# XOR key
# ----------------------------------------------------------------------------
def _clean_hex(s):
    s = "".join(s.split())
    if len(s) == 512 and all(c in "0123456789abcdefABCDEF" for c in s):
        return bytes.fromhex(s)
    return None


def load_key():
    """Return the 256-byte XOR key, or raise CoreError explaining where to put it."""
    env = os.environ.get("AB2_XOR_KEY") or os.environ.get("AB2E_XOR_KEY")
    if env:
        k = _clean_hex(env)
        if k:
            return k
    for name in ("xor_key.bin", "xor_key.hex"):
        path = p(name)
        if os.path.isfile(path):
            raw = open(path, "rb").read()
            if name.endswith(".bin") and len(raw) == 256:
                return raw
            k = _clean_hex(raw.decode("ascii", "ignore"))
            if k:
                return k
    raise CoreError("XOR key not found. Put xor_key.bin (256 bytes) or xor_key.hex "
                    "(512 hex characters) next to this program. It is not included in the project.")


def has_key():
    try:
        load_key()
        return True
    except CoreError:
        return False


def save_key_hex(hex_text):
    k = _clean_hex(hex_text)
    if not k:
        raise CoreError("That is not a valid key (it must be 512 hex characters / 256 bytes).")
    _write_key(k)
    return True


def _write_key(k):
    """Store the key as xor_key.hex and remove any older xor_key.bin, so the key you just
    gave is the one that is used (an old file can no longer silently win)."""
    with open(p("xor_key.hex"), "w") as f:
        f.write(k.hex())
    try:
        os.remove(p("xor_key.bin"))
    except OSError:
        pass


def check_key_against_game():
    """True if the current key opens the game's own index + save, False if not, None if no game files."""
    gi, gs = os.path.join(game_dir(), INDEX_NAME) if game_dir() else "", None
    try:
        gs = _game_save_path()
    except Exception:
        return None
    if not (os.path.isfile(gi) and gs and os.path.isfile(gs)):
        return None
    try:
        decrypt_bytes(open(gs, "rb").read(), open(gi, "rb").read(), load_key())
        return True
    except CoreError:
        return False


def save_key_bytes(raw):
    if len(raw) == 256:
        k = raw
    else:
        k = _clean_hex(raw.decode("ascii", "ignore"))
    if not k:
        raise CoreError("That file is not a valid key (256 bytes or 512 hex characters).")
    _write_key(k)
    return True


# ----------------------------------------------------------------------------
# crypto (AES-256-CBC, key/IV come from the 'index' file)
# ----------------------------------------------------------------------------
def _aes_cbc(key, iv, data, encrypt):
    try:
        from Crypto.Cipher import AES                      # pycryptodome
        c = AES.new(key, AES.MODE_CBC, iv=iv)
        return c.encrypt(data) if encrypt else c.decrypt(data)
    except ImportError:
        pass
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    except ImportError:
        raise CoreError("A crypto library is missing. Run:  pip install pycryptodome")
    c = Cipher(algorithms.AES(key), modes.CBC(iv))
    op = c.encryptor() if encrypt else c.decryptor()
    return op.update(data) + op.finalize()


def parse_index(index_bytes, xor_key):
    """Return (header, iv, aes_key). header is b'' for old builds, 36 bytes for new ones."""
    for off in (0, HEADER_LEN):
        if index_bytes[off:off + 2] == MAGIC:
            body = bytearray(index_bytes[off:])
            for i in range(4, len(body)):
                body[i] ^= xor_key[(i - 4) % len(xor_key)]
            num, c1, c2 = struct.unpack("<hhh", bytes(body[2:8]))
            if num == 1 and c1 + c2 + 8 == len(body):
                return bytes(index_bytes[:off]), bytes(body[8:8 + c1]), bytes(body[8 + c1:8 + c1 + c2])
    raise CoreError("The 'index' file is not valid (or the XOR key is wrong).")


def decrypt_bytes(save_bytes, index_bytes, xor_key):
    header, iv, key = parse_index(index_bytes, xor_key)
    data = save_bytes[len(header):] if header and save_bytes.startswith(header) else save_bytes
    if not data or len(data) % 16:
        raise CoreError("The save file is not the expected size. Copy 'index' and the save "
                        "from the game folder again, at the same time.")
    raw = _aes_cbc(key, iv, data, False)
    pad = raw[-1]
    if not (1 <= pad <= 16 and raw[-pad:] == bytes([pad]) * pad):
        raise CoreError("Decryption failed: 'index' and the save are not a matching pair "
                        "(the game makes a new 'index' when it starts a fresh save).")
    text = raw[:-pad].decode("utf-8", "strict").replace("\x00", "")
    try:
        json.loads(text)
    except ValueError:
        raise CoreError("Decrypted data is not valid JSON (wrong key or index).")
    return text


def encrypt_text(text, index_bytes, xor_key):
    json.loads(text)                                            # must be valid JSON
    header, iv, key = parse_index(index_bytes, xor_key)
    raw = b"".join(c.encode("utf-8") + b"\x00" for c in text)
    n = 16 - (len(raw) % 16)
    raw += bytes([n]) * n
    return header + _aes_cbc(key, iv, raw, True)


# ----------------------------------------------------------------------------
# game state checks
# ----------------------------------------------------------------------------
def game_folder_ok():
    return os.path.isdir(game_dir())


def game_running():
    """True / False, or None if we cannot tell."""
    if find_game_processes():
        return True
    try:
        if os.name == "nt":
            out = subprocess.run(["tasklist"], capture_output=True, text=True, timeout=10,
                                 creationflags=0x08000000).stdout.lower()
        else:
            return False          # non-Windows: find_game_processes() above already looked (zombies ignored)
    except Exception:
        return None
    return any(w in out for w in _GAME_WORDS)


_GAME_WORDS = ("angrybirds", "angry birds", "angry_birds", "baba.exe")


def find_game_processes():
    """[(name, pid)] of processes that look like Angry Birds 2. Only these names are matched."""
    found = []
    try:
        if os.name == "nt":
            out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=10,
                                 creationflags=0x08000000).stdout
            import csv
            for row in csv.reader(out.splitlines()):
                if len(row) >= 2 and any(w in row[0].lower() for w in _GAME_WORDS):
                    found.append((row[0], int(row[1])))
        else:
            out = subprocess.run(["ps", "-A", "-o", "pid=,stat=,comm="], capture_output=True, text=True, timeout=10).stdout
            for line in out.splitlines():
                parts = line.strip().split(None, 2)
                if len(parts) == 3 and not parts[1].startswith("Z") and any(w in parts[2].lower() for w in _GAME_WORDS):
                    found.append((parts[2], int(parts[0])))
    except Exception:
        pass
    return found


def close_game():
    """Force-close every process that looks like Angry Birds 2. Returns the names that were closed."""
    import time
    procs = find_game_processes()
    if not procs:
        return {"closed": [], "still_running": bool(game_running())}
    for name, pid in procs:
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, timeout=15,
                               creationflags=0x08000000)
            else:
                os.kill(pid, 9)
        except Exception:
            pass
    time.sleep(1.2)
    return {"closed": sorted({n for n, _ in procs}), "still_running": bool(game_running())}


def files_in_game_dir():
    d = game_dir()
    if not os.path.isdir(d):
        return []
    out = []
    for f in sorted(os.listdir(d)):
        fp = os.path.join(d, f)
        if os.path.isfile(fp):
            out.append({"name": f, "size": os.path.getsize(fp),
                        "modified": datetime.datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%Y-%m-%d %H:%M:%S")})
    return out


def _game_save_path():
    d = game_dir()
    if not os.path.isdir(d):
        raise CoreError("The game's save folder was not found. Start the game once, then close it.")
    for f in os.listdir(d):                       # the file name may be shown shortened in tools
        if f.upper().startswith(SAVE_NAME[:40]):
            return os.path.join(d, f)
    raise CoreError("The game's save file (B4F59D3E...) is not in the save folder yet.")


def index_matches():
    """None if either index is missing, else True/False."""
    a, b = p(INDEX_NAME), os.path.join(game_dir(), INDEX_NAME)
    if not (os.path.isfile(a) and os.path.isfile(b)):
        return None
    return open(a, "rb").read() == open(b, "rb").read()


# ----------------------------------------------------------------------------
# workflow steps
# ----------------------------------------------------------------------------
def backup_game_folder():
    d = game_dir()
    if not os.path.isdir(d):
        raise CoreError("The game's save folder was not found.")
    n = next_number(p(GAME_BACKUP_DIR), "game_backup")
    dst = os.path.join(p(GAME_BACKUP_DIR), f"game_backup_{n:03d}_{_stamp()}")
    os.makedirs(dst)
    for f in os.listdir(d):
        fp = os.path.join(d, f)
        if os.path.isfile(fp):
            shutil.copyfile(fp, os.path.join(dst, f))
    return dst


def pull_from_game():
    """Back up the whole game save folder, then copy index + save into the work folder."""
    if game_running():
        raise CoreError("The game seems to be running. Close it completely, then try again.")
    save = _game_save_path()
    gidx = os.path.join(game_dir(), INDEX_NAME)
    if not os.path.isfile(gidx):
        raise CoreError("The game's 'index' file is missing.")
    dst = backup_game_folder()
    shutil.copyfile(gidx, p(INDEX_NAME))
    shutil.copyfile(save, p(SAVE_NAME))
    return {"backup": dst, "save_bytes": os.path.getsize(p(SAVE_NAME))}


def decrypt_work():
    key = load_key()
    if not (os.path.isfile(p(INDEX_NAME)) and os.path.isfile(p(SAVE_NAME))):
        raise CoreError("Nothing loaded yet. Do step 'Backup & load' first.")
    text = decrypt_bytes(open(p(SAVE_NAME), "rb").read(), open(p(INDEX_NAME), "rb").read(), key)
    if os.path.isfile(p(JSON_NAME)):
        backup_file(p(JSON_NAME), p(OLD_JSON_DIR), "decrypted_save", ".json")
    atomic_write(p(JSON_NAME), text.encode("utf-8"))
    # the pristine decrypted version is the baseline for the before/after comparison
    atomic_write(p("baseline.json"), text.encode("utf-8"))
    return {"chars": len(text)}


def encrypt_work():
    key = load_key()
    if not os.path.isfile(p(JSON_NAME)):
        raise CoreError("There is no decrypted_save.json yet.")
    idx = open(p(INDEX_NAME), "rb").read()
    text = open(p(JSON_NAME), "r", encoding="utf-8").read()
    data = encrypt_text(text, idx, key)
    if json.loads(decrypt_bytes(data, idx, key)) != json.loads(text):          # verify round trip
        raise CoreError("Verification failed: the encrypted file does not decrypt back to your JSON.")
    if os.path.isfile(p(SAVE_NAME)):
        backup_file(p(SAVE_NAME), p(OLD_ENC_DIR), "encrypted_save", ".bak")
    atomic_write(p(SAVE_NAME), data)
    return {"bytes": len(data)}


def push_to_game(force_running=False):
    """Safety checks, back up the game folder, then replace ONLY the save file."""
    if not force_running and game_running():
        raise CoreError("The game seems to be running. Close it completely first.")
    if index_matches() is False:
        raise CoreError("The game's 'index' is different from the one this save was made with. "
                        "The game would not be able to read it. Use 'Backup & load' again.")
    if index_matches() is None:
        raise CoreError("The 'index' file is missing here or in the game folder.")
    if not os.path.isfile(p(SAVE_NAME)):
        raise CoreError("There is no encrypted save to install yet.")
    target = _game_save_path()
    backup = backup_game_folder()
    data = open(p(SAVE_NAME), "rb").read()
    atomic_write(target, data)
    if open(target, "rb").read() != data:
        raise CoreError("The file in the game folder does not match what was written.")
    return {"backup": backup, "bytes": len(data), "target": os.path.basename(target)}


# ----------------------------------------------------------------------------
# restore + undo
# ----------------------------------------------------------------------------
def list_game_backups():
    root = p(GAME_BACKUP_DIR)
    if not os.path.isdir(root):
        return []
    out = []
    for name in sorted(os.listdir(root), reverse=True):
        fp = os.path.join(root, name)
        if os.path.isdir(fp):
            files = [f for f in os.listdir(fp) if os.path.isfile(os.path.join(fp, f))]
            size = sum(os.path.getsize(os.path.join(fp, f)) for f in files)
            out.append({"name": name, "files": len(files), "bytes": size})
    return out


RESTORE_CODE = "222"
WORK_FILES = (INDEX_NAME, SAVE_NAME, JSON_NAME, "baseline.json")


def reset_work_files():
    """Move this program's working copies (index, encrypted save, decrypted JSON, baseline) into a
    numbered folder so nothing edited earlier can be mixed with a restored save by accident."""
    moved = [f for f in WORK_FILES if os.path.isfile(p(f))]
    if not moved:
        return None
    n = 1
    while os.path.exists(p("work_reset_%03d" % n)):
        n += 1
    dest = p("work_reset_%03d" % n)
    os.makedirs(dest)
    for f in moved:
        shutil.move(p(f), os.path.join(dest, f))
    return dest


def restore_game_backup(name, code=""):
    """Put an earlier backup back as the game's whole save folder, exactly as it was."""
    if str(code).strip() != RESTORE_CODE:
        raise CoreError("Type %s to confirm the restore." % RESTORE_CODE)
    if os.path.sep in name or name.startswith(".") or "/" in name or "\\" in name:
        raise CoreError("Invalid backup name.")
    src = os.path.join(p(GAME_BACKUP_DIR), name)
    if not os.path.isdir(src):
        raise CoreError("That backup was not found.")
    if game_running():
        raise CoreError("The game seems to be running. Close it completely first.")
    d = game_dir()
    if not d or not os.path.isdir(d):
        raise CoreError("The game's save folder was not found.")
    files = [f for f in os.listdir(src) if os.path.isfile(os.path.join(src, f))]
    if INDEX_NAME not in files or SAVE_NAME not in files:
        raise CoreError("That backup has no index + save pair, so it cannot be restored safely.")
    safety = backup_game_folder()                  # always keep what is there right now
    # make the folder match the backup exactly: no leftover file from a different state
    for f in os.listdir(d):
        fp = os.path.join(d, f)
        if os.path.isfile(fp) and f not in files:
            os.remove(fp)
    for f in files:
        atomic_write(os.path.join(d, f), open(os.path.join(src, f), "rb").read())
    for f in files:                                # verify byte for byte
        if open(os.path.join(d, f), "rb").read() != open(os.path.join(src, f), "rb").read():
            raise CoreError("Verification failed for " + f + ". Your previous files are in " + os.path.basename(safety))
    reset = reset_work_files()
    return {"restored": name, "safety_backup": safety, "files": len(files),
            "work_reset": os.path.basename(reset) if reset else None}


def undo_last_edit():
    """Put back the most recent numbered copy of decrypted_save.json."""
    folder = p(OLD_JSON_DIR)
    files = sorted(f for f in os.listdir(folder)) if os.path.isdir(folder) else []
    if not files:
        raise CoreError("There is no earlier version to go back to.")
    last = files[-1]
    shutil.copyfile(os.path.join(folder, last), p(JSON_NAME))
    return {"restored_from": last}


# ----------------------------------------------------------------------------
# reading + comparing
# ----------------------------------------------------------------------------
def _nested(d, key):
    v = d.get(key)
    if isinstance(v, str) and v[:1] in "{[":
        try:
            return json.loads(v)
        except ValueError:
            return None
    return v


def summarize(path=None):
    """Plain-language view of the values people care about."""
    path = path or p(JSON_NAME)
    if not os.path.isfile(path):
        raise CoreError("No decrypted save yet.")
    d = json.load(open(path, "r", encoding="utf-8"))
    w = _nested(d, "PD_Wallet") or {}
    prog = _nested(d, "PD_PlayerProgress") or {}
    cards = (_nested(d, "PD_CardSpecCollection") or {}).get("CardSpecifications", [])
    guests = (_nested(d, "PD_GuestBirdCollection") or {}).get("CardSpecifications", [])
    parts = (_nested(d, "PD_CostumeData") or {}).get("OwnedParts", [])
    spells = (_nested(d, "PD_NewSpellCollection") or {}).get("Spells", [])
    meta = _nested(d, "PD_Metadata") or {}
    return {
        "wallet": w,
        "campaign_level": prog.get("LevelPlayerIsAt"),
        "core_birds": [{"name": c.get("CardTemplateName"), "level": c.get("Level")} for c in cards],
        "guest_birds": [{"name": c.get("CardTemplateName"), "level": c.get("Level")} for c in guests],
        "hat_parts": len(parts),
        "spells": {s.get("Name"): s.get("Count") for s in spells},
        "account_id_short": (meta.get("Id") or "")[:8],
        "last_save": meta.get("LastSaveDate"),
    }


def _flat(o, prefix=""):
    out = {}
    if isinstance(o, str) and o[:1] in "{[":
        try:
            return _flat(json.loads(o), prefix)
        except ValueError:
            pass
    if isinstance(o, dict):
        for k, v in o.items():
            out.update(_flat(v, f"{prefix}/{k}"))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            out.update(_flat(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = o
    return out


def diff_saves(before_path=None, after_path=None):
    """Return the main before/after differences in plain language."""
    before_path = before_path or p("baseline.json")
    after_path = after_path or p(JSON_NAME)
    if not (os.path.isfile(before_path) and os.path.isfile(after_path)):
        raise CoreError("Nothing to compare yet.")
    a = _flat(json.load(open(before_path, "r", encoding="utf-8")))
    b = _flat(json.load(open(after_path, "r", encoding="utf-8")))
    lines = []
    for k in sorted(set(a) | set(b)):
        if a.get(k) != b.get(k):
            lines.append((k, a.get(k), b.get(k)))
    wallet = [(k.split("/")[-1], x, y) for k, x, y in lines if k.startswith("/PD_Wallet/")]
    birds = [(k, x, y) for k, x, y in lines if k.endswith("/Level") and ("CardSpec" in k)]
    names = {}
    for k in b:
        m = re.match(r"(/PD_(?:Card|Guest)\w*/CardSpecifications\[\d+\])/CardTemplateName", k)
        if m:
            names[m.group(1)] = b[k]
    for k in a:
        m = re.match(r"(/PD_(?:Card|Guest)\w*/CardSpecifications\[\d+\])/CardTemplateName", k)
        if m:
            names.setdefault(m.group(1), a[k])
    bird_changes = []
    for k, x, y in birds:
        base = k.rsplit("/Level", 1)[0]
        bird_changes.append({"name": names.get(base, base), "before": x, "after": y})
    hats_before = sum(1 for k in a if k.startswith("/PD_CostumeData/OwnedParts[") and k.endswith("/SetId"))
    hats_after = sum(1 for k in b if k.startswith("/PD_CostumeData/OwnedParts[") and k.endswith("/SetId"))
    campaign = next(((x, y) for k, x, y in lines if k == "/PD_PlayerProgress/LevelPlayerIsAt"), None)
    return {
        "wallet": [{"field": f, "before": x, "after": y} for f, x, y in wallet],
        "birds": bird_changes,
        "hats": {"before": hats_before, "after": hats_after},
        "campaign": {"before": campaign[0], "after": campaign[1]} if campaign else None,
        "other_changed_values": len(lines),
    }


TUT_EXTS = (".mp4", ".webm", ".m4v", ".mov", ".ogv")


def tutorial_dirs():
    out = [os.path.join(base_dir(), "tutorial")]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        out.append(os.path.join(meipass, "tutorial"))
    return out


def tutorial_file():
    """Path of tutorial/tut.<ext> if the owner added one, else None."""
    for d in tutorial_dirs():
        for ext in TUT_EXTS:
            fp = os.path.join(d, "tut" + ext)
            if os.path.isfile(fp):
                return fp
    return None


def status():
    """Everything the UI needs to draw the first screen."""
    gd = game_dir()
    return {
        "base_dir": base_dir(),
        "game_dir": gd,
        "game_dir_found": bool(gd) and os.path.isdir(gd),
        "os": ("windows" if os.name == "nt" else "mac" if sys.platform == "darwin" else "linux"),
        "game_running": game_running(),
        "has_key": has_key(),
        "index_here": os.path.isfile(p(INDEX_NAME)),
        "save_here": os.path.isfile(p(SAVE_NAME)),
        "json_here": os.path.isfile(p(JSON_NAME)),
        "index_matches": index_matches(),
        "game_files": files_in_game_dir(),
        "backups": len(list_game_backups()),
        "tutorial": (os.path.basename(tutorial_file()) if tutorial_file() else None),
    }
