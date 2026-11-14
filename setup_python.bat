@echo off
REM Finds a working Python (py, python, python3, or a standard install folder) and sets %PY%.
REM If none exists it offers to install one with winget. Called by start_app.bat and build_exe.bat.
set "PY="
call :try "py -3"
call :try "python"
call :try "python3"
if not defined PY call :search
if defined PY goto :found

echo.
echo  Python was not found on this PC.
echo  Easiest fix: you do NOT need Python at all. Download the ready-made AB2-Save-Editor.exe
echo  from the Releases page of this project on GitHub and just double-click it.
echo.
where winget >nul 2>nul
if errorlevel 1 goto :manual
choice /m " Install Python automatically now (uses winget, about 1 minute)"
if errorlevel 2 goto :manual
winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
call :search
if not defined PY call :try "py -3"
if not defined PY (
  echo.
  echo  Python was installed but this window cannot see it yet.
  echo  Close this window and double-click the same file again.
  exit /b 1
)
goto :found

:manual
echo  Or install Python yourself: https://www.python.org/downloads/  (tick "Add python.exe to PATH").
start "" https://www.python.org/downloads/
exit /b 1

:found
%PY% -m pip --version >nul 2>nul || %PY% -m ensurepip --upgrade >nul 2>nul
exit /b 0

:try
if defined PY exit /b 0
%~1 -c "import sys; sys.exit(0 if sys.version_info>=(3,8) else 1)" >nul 2>nul
if not errorlevel 1 set "PY=%~1"
exit /b 0

:search
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*" "%ProgramFiles%\Python3*" "%ProgramFiles(x86)%\Python3*") do (
  if exist "%%~D\python.exe" if not defined PY set PY="%%~D\python.exe"
)
exit /b 0
