#!/bin/sh
# Mac / Linux launcher. Needs Python 3.8+ (Mac: brew install python, or python.org; Linux: your package manager).
cd "$(dirname "$0")"
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys;sys.exit(0 if sys.version_info>=(3,8) else 1)'; then PY="$c"; break; fi
done
[ -z "$PY" ] && { echo "Python 3.8+ not found. Install it, or download the ready-made app from the Releases page."; exit 1; }
"$PY" -m pip install --quiet --disable-pip-version-check pycryptodome 2>/dev/null || "$PY" -m pip install --quiet --user --break-system-packages pycryptodome
exec "$PY" ab2_app.py
