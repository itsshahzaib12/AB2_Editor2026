#!/usr/bin/env python3
"""
run_all.py - does everything for you and only stops to ask about the edit.

  check -> back up the game folder -> load + decrypt -> [your edit] -> encrypt + verify
        -> show what changed -> ask to confirm -> install into the game

Close the game first. Prefer a window? Run ab2_app.py instead.
"""
import os
import subprocess
import sys

import ab2core as core


def ask(q, default=None):
    try:
        a = input(q).strip().lower()
    except EOFError:
        sys.exit(1)
    return a or (default or "")


def die(msg):
    print("\n[X] " + msg)
    sys.exit(1)


def main():
    print("== AB2 Save Editor ==")
    try:
        core.load_key()
        if not core.game_folder_ok():
            die(f"Save folder not found: {core.game_dir()}")
        if core.game_running():
            die("The game seems to be running. Close it completely, then run this again.")
        print("[1/6] Backing up the game folder and loading your save...")
        r = core.pull_from_game()
        print("      backup:", r["backup"])
        core.decrypt_work()
        s = core.summarize()
        w = s["wallet"]
        print(f"      loaded: gems {w.get('Gems'):,}, campaign level {s['campaign_level']}, hat parts {s['hat_parts']}")
    except core.CoreError as e:
        die(str(e))

    print("\n[2/6] Your edit")
    print("   1) Modest preset (small, plausible numbers)")
    print("   2) Custom wizard (type your own values)")
    print("   3) No edit (just re-encrypt)")
    c = ask("Choose 1, 2 or 3 [1]: ", "1")
    here = os.path.dirname(os.path.abspath(__file__))
    if c in ("1", "2"):
        cmd = [sys.executable, os.path.join(here, "json_editor.py")] + (["--auto"] if c == "1" else [])
        if subprocess.call(cmd, cwd=here) != 0:
            die("The editor did not finish. Nothing was installed.")

    try:
        print("\n[3/6] Encrypting and verifying...")
        core.encrypt_work()
        print("[4/6] What changed:")
        d = core.diff_saves()
        for x in d["wallet"]:
            print(f"      {x['field']}: {x['before']} -> {x['after']}")
        if d["campaign"]:
            print(f"      campaign level: {d['campaign']['before']} -> {d['campaign']['after']}")
        print(f"      birds changed: {len(d['birds'])}, hat parts: {d['hats']['before']} -> {d['hats']['after']}")
        print("\n  Editing can get an account reset or banned. Keep numbers modest.")
        if ask("[5/6] Install into the game now? (y/N): ") != "y":
            print("Stopped. Nothing was installed. Your backup is safe.")
            return
        print("[6/6] Installing...")
        r = core.push_to_game()
        print(f"[OK] Installed ({r['bytes']:,} bytes). Backup: {r['backup']}")
        print("Start the game (it needs the internet to pass loading). If it breaks: py restore.py")
    except core.CoreError as e:
        die(str(e))


if __name__ == "__main__":
    main()
