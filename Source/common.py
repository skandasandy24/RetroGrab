"""Shared paths and small helpers for RetroGrab."""
import json
import os
import shutil
import sys

APP_NAME = "RetroGrab"
APP_VERSION = "1.0.2"

FROZEN = getattr(sys, "frozen", False)
BASE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
VENDOR = os.path.join(BASE, "vendor")
ASSETS = os.path.join(BASE, "assets")

# Portable: everything is kept next to the program.
#   packaged:  <folder with RetroGrab.exe>\data   and  ...\Downloads
#   source:    Source\.devdata
APP_DIR = os.path.dirname(sys.executable) if FROZEN else os.path.dirname(os.path.abspath(__file__))


def _writable_dir(path):
    try:
        os.makedirs(path, exist_ok=True)
        probe = os.path.join(path, ".write_test")
        with open(probe, "w") as f:
            f.write("ok")
        os.remove(probe)
        return True
    except OSError:
        return False


DATA = os.path.join(APP_DIR, "data" if FROZEN else ".devdata")
if not _writable_dir(DATA):  # e.g. unzipped into Program Files - fall back to the user profile
    DATA = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), APP_NAME)
    os.makedirs(DATA, exist_ok=True)

UPDATES = os.path.join(DATA, "updates")
COOKIES = os.path.join(DATA, "instagram_cookies.txt")
WEBVIEW_PROFILE = os.path.join(DATA, "webview")
SETTINGS_FILE = os.path.join(DATA, "settings.json")
HISTORY_FILE = os.path.join(DATA, "history.json")
DEFAULT_FOLDER = os.path.join(APP_DIR, "Downloads")


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception:
        pass


def _vendor_or_path(exe):
    local = os.path.join(VENDOR, exe)
    if os.path.isfile(local):
        return local
    return shutil.which(exe)


def ffmpeg_location():
    """Folder containing ffmpeg.exe (bundled first, then system PATH)."""
    exe = _vendor_or_path("ffmpeg.exe")
    return os.path.dirname(exe) if exe else None


def js_runtimes():
    """JavaScript runtime for YouTube, preferring bundled ones."""
    for name, exe in (("deno", "deno.exe"), ("node", "node.exe"), ("quickjs", "qjs.exe")):
        local = os.path.join(VENDOR, exe)
        if os.path.isfile(local):
            return {name: {"path": local}}
    for name, exe in (("deno", "deno.exe"), ("node", "node.exe"), ("quickjs", "qjs.exe")):
        found = shutil.which(exe)
        if found:
            return {name: {"path": found}}
    return {"deno": {}}


def has_instagram_login():
    try:
        with open(COOKIES, encoding="utf-8") as f:
            return "sessionid" in f.read()
    except OSError:
        return False
