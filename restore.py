#!/usr/bin/env python3
"""Put a backup of the game's save folder back (game must be closed).
  py restore.py            -> list backups
  py restore.py <name>     -> restore that backup (your current files are backed up first)"""
import sys
import ab2core as core

try:
    if len(sys.argv) < 2:
        for b in core.list_game_backups():
            print(f"{b['name']}   ({b['files']} files, {b['bytes']:,} bytes)")
        print("\nRestore one with:  py restore.py <name>")
    else:
        r = core.restore_game_backup(sys.argv[1])
        print(f"[OK] Restored {r['restored']}. Previous files saved as {r['safety_backup']}")
except core.CoreError as e:
    print("[X]", e); sys.exit(1)
