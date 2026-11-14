#!/usr/bin/env python3
"""Step 1 (command line): decrypt the save in this folder into decrypted_save.json.
Needs: index + B4F59D3E...FA1 in this folder, and the XOR key (xor_key.bin / xor_key.hex)."""
import sys
import ab2core as core

try:
    r = core.decrypt_work()
    print(f"[OK] Created {core.JSON_NAME} ({r['chars']:,} characters). Next: py json_editor.py")
except core.CoreError as e:
    print("[X]", e); sys.exit(1)
