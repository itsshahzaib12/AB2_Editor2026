#!/bin/sh
# ONE command builds the app for THIS computer (macOS or Linux): sh build_app.sh
# (A Windows .exe can only be built on Windows, a Mac app only on a Mac, and so on.)
cd "$(dirname "$0")"
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys;sys.exit(0 if sys.version_info>=(3,8) else 1)'; then PY="$c"; break; fi
done
[ -z "$PY" ] && { echo "Python 3.8+ not found. Mac: brew install python (or python.org). Linux: sudo apt install python3 python3-pip."; exit 1; }
echo "[1/3] Installing build tools..."
"$PY" -m pip install --quiet --upgrade pyinstaller pycryptodome 2>/dev/null || "$PY" -m pip install --quiet --upgrade --user --break-system-packages pyinstaller pycryptodome || exit 1
echo "[2/3] Building (1-2 minutes)..."
"$PY" -m PyInstaller --noconfirm --clean --onefile --noconsole --name AB2-Save-Editor --add-data "ui:ui" --hidden-import Crypto.Cipher.AES ab2_app.py >build_log.txt 2>&1 || { echo "Build failed. See build_log.txt"; exit 1; }
echo "[3/3] Packing into AB2-Editor-Ready..."
mkdir -p AB2-Editor-Ready && cp dist/AB2-Save-Editor AB2-Editor-Ready/ && chmod +x AB2-Editor-Ready/AB2-Save-Editor
[ -d tutorial ] && { mkdir -p dist AB2-Editor-Ready; cp -r tutorial dist/; cp -r tutorial AB2-Editor-Ready/; }
[ -f xor_key.hex ] && cp xor_key.hex AB2-Editor-Ready/; [ -f xor_key.bin ] && cp xor_key.bin AB2-Editor-Ready/
rm -rf build
echo "Done: AB2-Editor-Ready/AB2-Save-Editor   (Mac: right-click > Open the first time)"
