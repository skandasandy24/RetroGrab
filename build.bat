@echo off
cd /d "%~dp0Source"
python build.py
if errorlevel 1 (
    echo.
    echo [!] Build failed - run setup.bat first, then open a new window and try again.
) else (
    echo.
    echo Built!  Program: App\RetroGrab.exe    Shareable zip: Release\
)
pause
