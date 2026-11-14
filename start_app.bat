@echo off
REM Starts the editor window without building an .exe. Finds Python for you.
cd /d "%~dp0"
call setup_python.bat
if errorlevel 1 (pause & exit /b 1)
%PY% -m pip install --quiet --disable-pip-version-check pycryptodome
%PY% ab2_app.py
pause
