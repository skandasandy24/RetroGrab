@echo off
setlocal
cd /d "%~dp0"
echo ============================================
echo   RetroGrab setup (only needed to run/build
echo   from source - the Release .exe needs none)
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [!] Python was not found.
    echo     Install Python 3.10 or newer from https://www.python.org/downloads/
    echo     and tick "Add python.exe to PATH" during install. Then run setup.bat again.
    pause
    exit /b 1
)

echo [1/3] Installing Python packages...
python -m pip install --upgrade -r requirements.txt
if errorlevel 1 (
    echo [!] Installing packages failed - see the messages above.
    pause
    exit /b 1
)

echo.
echo [2/3] Checking ffmpeg (merging video+audio, converting to MP3)...
where ffmpeg >nul 2>nul
if errorlevel 1 (
    echo       Not found - installing with winget...
    winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
) else (
    echo       ffmpeg OK
)

echo.
echo [3/3] Checking a JavaScript runtime (needed for YouTube)...
set "HAVEJS="
where deno >nul 2>nul && set "HAVEJS=1"
where node >nul 2>nul && set "HAVEJS=1"
if not defined HAVEJS (
    echo       Not found - installing Deno with winget...
    winget install -e --id DenoLand.Deno --accept-source-agreements --accept-package-agreements
) else (
    echo       JavaScript runtime OK
)

echo.
echo Done! Close this window and open a NEW one (so Windows finds ffmpeg/deno), then:
echo    run.bat    - start RetroGrab from source
echo    build.bat  - make App\RetroGrab.exe and a shareable zip in Release\
pause
