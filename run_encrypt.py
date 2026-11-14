#!/usr/bin/env python3
"""Step 3 (command line): encrypt decrypted_save.json back into the game save (verified).
The previous encrypted file is kept in old_encrypted/. Then use run_all.py or the app to install it."""
import sys
import ab2core as core

try:
    r = core.encrypt_work()
    print(f"[OK] Wrote {core.SAVE_NAME[:12]}... ({r['bytes']:,} bytes, verified).")
except core.CoreError as e:
    print("[X]", e); sys.exit(1)
