@echo off
cd /d "%~dp0Source"
where pythonw >nul 2>nul
if errorlevel 1 (
    python retrograb.py
) else (
    start "" pythonw retrograb.py
)
