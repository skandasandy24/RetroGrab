"""Builds RetroGrab.exe.

Usage:  python build.py        (run from D:\\RETRO GRAB\\Source)

Layout it produces (relative to the project root, one level above Source):
    App\\RetroGrab.exe + App\\_internal   <- the program (App\\data is kept between builds)
    Release\\RetroGrab-<ver>-win64.zip   <- clean copy to share (no personal data)

Bundled helper programs live in Source\\vendor. If a file is already there it is
kept, otherwise it is copied from this PC (PATH / Program Files):
    ffmpeg.exe + ffprobe.exe (+ any DLLs next to them)  - merging & converting
    node.exe / deno.exe / qjs.exe (any one)               - needed for YouTube
"""
import json
import os
import shutil
import subprocess
import sys
import zipfile
from importlib.metadata import version

HERE = os.path.dirname(os.path.abspath(__file__))          # ...\Source
ROOT = os.path.dirname(HERE)                               # ...\RETRO GRAB
APP = os.path.join(ROOT, "App")
RELEASE = os.path.join(ROOT, "Release")
VENDOR = os.path.join(HERE, "vendor")
WORK = os.path.join(HERE, "build")                         # temporary, deleted after
sys.path.insert(0, HERE)
from common import APP_VERSION  # noqa: E402

README = (
    "RetroGrab - YouTube / Instagram / Spotify downloader\r\n"
    "=====================================================\r\n\r\n"
    "1. Unzip this whole folder somewhere (e.g. Documents or D:\\). Don't run it from inside the zip.\r\n"
    "2. Double-click RetroGrab.exe. (Right-click it > Send to > Desktop to make a shortcut.)\r\n"
    "3. If Windows says 'Windows protected your PC', click 'More info' -> 'Run anyway'.\r\n"
    "   (It appears because the app isn't signed by a big company - normal for small apps.)\r\n\r\n"
    "Everything stays inside this folder:\r\n"
    "   Downloads\\   your videos, photos and songs (changeable in the app)\r\n"
    "   data\\        settings, history and your Instagram login\r\n\r\n"
    "Instagram: click 'Log in to Instagram...' on the Instagram tab once.\r\n"
    "If YouTube or Instagram stop working: Tools > Check for updates, then restart the app.\r\n\r\n"
    "Only download what you have the right to.\r\n")


def vendor_tools():
    os.makedirs(VENDOR, exist_ok=True)
    if not os.path.isfile(os.path.join(VENDOR, "ffmpeg.exe")):
        src = shutil.which("ffmpeg")
        if not src:
            sys.exit("ffmpeg not found - put ffmpeg.exe and ffprobe.exe in Source\\vendor")
        d = os.path.dirname(src)
        for fn in os.listdir(d):
            if fn.lower() in ("ffmpeg.exe", "ffprobe.exe") or fn.lower().endswith(".dll"):
                shutil.copy2(os.path.join(d, fn), VENDOR)
        print("copied ffmpeg from", d)
    if not any(os.path.isfile(os.path.join(VENDOR, x)) for x in ("deno.exe", "node.exe", "qjs.exe")):
        for exe in ("deno", "node", "qjs"):
            src = shutil.which(exe)
            if src:
                shutil.copy2(src, VENDOR)
                print("copied", src)
                break
        else:
            sys.exit("No JavaScript runtime found - put deno.exe, node.exe or qjs.exe in Source\\vendor")
    versions = {p: version(p) for p in ("yt-dlp", "yt-dlp-ejs", "gallery-dl")}
    with open(os.path.join(VENDOR, "versions.json"), "w") as f:
        json.dump(versions, f, indent=2)
    print("engine versions:", versions)


def pyinstaller():
    env = dict(os.environ, PYINSTALLER_CONFIG_DIR=os.path.join(WORK, "cache"))
    args = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed",
        "--name", "RetroGrab", "--icon", os.path.join(HERE, "assets", "retrograb.ico"),
        "--add-data", f"{os.path.join(HERE, 'assets')}{os.pathsep}assets",
        "--add-data", f"{VENDOR}{os.pathsep}vendor",
        "--collect-all", "yt_dlp_ejs",
        "--collect-submodules", "gallery_dl",
        "--collect-submodules", "yt_dlp",
        "--hidden-import", "mutagen.id3", "--hidden-import", "mutagen.mp4",
        "--exclude-module", "PIL", "--exclude-module", "numpy", "--exclude-module", "matplotlib",
        "--distpath", os.path.join(WORK, "dist"), "--workpath", os.path.join(WORK, "work"),
        "--specpath", WORK,
        os.path.join(HERE, "retrograb.py"),
    ]
    subprocess.run(args, check=True, cwd=HERE, env=env)
    return os.path.join(WORK, "dist", "RetroGrab")


def install_app(built):
    """Replace the program files in App\\ but keep App\\data (settings, history, login)."""
    import time
    os.makedirs(APP, exist_ok=True)
    internal = os.path.join(APP, "_internal")
    old = os.path.join(APP, "_internal.old")
    if os.path.isdir(old):
        shutil.rmtree(old, ignore_errors=True)
    if os.path.isdir(internal):
        # A folder can't be renamed while a running RetroGrab has files open in it,
        # so this both detects a running app and moves the old files out of the way
        # without deleting anything yet.
        for attempt in range(5):
            try:
                os.rename(internal, old)
                break
            except OSError:
                if attempt == 4:
                    sys.exit("RetroGrab (or its login window) is running - close it, then run the build again.")
                time.sleep(2)
    for name in ("RetroGrab.exe", "README.txt"):
        p = os.path.join(APP, name)
        if os.path.isfile(p):
            os.remove(p)
    for name in os.listdir(built):
        src = os.path.join(built, name)
        (shutil.copytree if os.path.isdir(src) else shutil.copy2)(src, os.path.join(APP, name))
    shutil.rmtree(old, ignore_errors=True)
    with open(os.path.join(APP, "README.txt"), "w", encoding="utf-8") as f:
        f.write(README)
    print("installed to", APP)


def make_zip(built):
    os.makedirs(RELEASE, exist_ok=True)
    for fn in os.listdir(RELEASE):
        if fn.endswith(".zip"):
            os.remove(os.path.join(RELEASE, fn))
    out = os.path.join(RELEASE, f"RetroGrab-{APP_VERSION}-win64.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for root, _, files in os.walk(built):
            for fn in files:
                p = os.path.join(root, fn)
                z.write(p, os.path.join("RetroGrab", os.path.relpath(p, built)))
        z.writestr("RetroGrab/README.txt", README)
    print(f"zip: {out}  ({os.path.getsize(out) / 1048576:.0f} MB)")


if __name__ == "__main__":
    vendor_tools()
    built = pyinstaller()
    install_app(built)
    make_zip(built)
    shutil.rmtree(WORK, ignore_errors=True)
    print("done")
