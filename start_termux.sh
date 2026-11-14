#!/data/data/com.termux/files/usr/bin/sh
# Android (Termux) launcher. Needs a ROOTED phone or a folder with copied game files. Untested.
cd "$(dirname "$0")"
pkg install -y python python-cryptography >/dev/null 2>&1
echo "Open the link below in your phone browser:"
exec python ab2_app.py --no-browser
