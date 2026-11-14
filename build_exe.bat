@echo off
REM ONE double-click does everything: finds/installs Python, installs the tools, builds the .exe,
REM and puts it in the folder  AB2-Editor-Ready  (next to this file). No GitHub needed.
cd /d "%~dp0"
call setup_python.bat
if errorlevel 1 (pause & exit /b 1)
echo.
echo  [1/3] Installing build tools...
%PY% -m pip install --quiet --upgrade --disable-pip-version-check pyinstaller pycryptodome
if errorlevel 1 (echo  Could not install the tools. Check your internet and run this again. & pause & exit /b 1)
echo  [2/3] Building the app (1-2 minutes)...
%PY% -m PyInstaller --noconfirm --clean --onefile --noconsole --name AB2-Save-Editor --add-data "ui;ui" --hidden-import Crypto.Cipher.AES ab2_app.py >build_log.txt 2>&1
if not exist "dist\AB2-Save-Editor.exe" (echo  Build failed. See build_log.txt & pause & exit /b 1)
echo  [3/3] Packing it into AB2-Editor-Ready...
if not exist "AB2-Editor-Ready" mkdir "AB2-Editor-Ready"
copy /y "dist\AB2-Save-Editor.exe" "AB2-Editor-Ready\" >nul
if exist tutorial xcopy /e /i /y "tutorial" "AB2-Editor-Ready\tutorial" >nul
if exist tutorial xcopy /e /i /y "tutorial" "dist\tutorial" >nul
if exist xor_key.hex copy /y xor_key.hex "AB2-Editor-Ready\" >nul
if exist xor_key.bin copy /y xor_key.bin "AB2-Editor-Ready\" >nul
rmdir /s /q build 2>nul
echo.
echo  Done!  Your app:  AB2-Editor-Ready\AB2-Save-Editor.exe
echo  (If your xor_key was next to this file it was copied too. Otherwise the app asks for it on first start.)
echo  Windows SmartScreen may warn about a program you built yourself. That is normal.
start "" "AB2-Editor-Ready"
pause
