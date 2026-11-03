"""Shared paths and small helpers for RetroGrab."""
import json
import os
import shutil
import sys

APP_NAME = "RetroGrab"
APP_VERSION = "1.1.0"

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
IG_SESSION = os.path.join(DATA, "instagram_session.bin")    # encrypted with Windows DPAPI
LEGACY_COOKIES = os.path.join(DATA, "instagram_cookies.txt")  # plain text, used by 1.0.x - migrated
WEBVIEW_TEMP = os.path.join(DATA, "login_temp")               # deleted after each login
LEGACY_WEBVIEW = os.path.join(DATA, "webview")                # persistent profile used by 1.0.x - deleted
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


# ---------------------------------------------------------------- Instagram session
# The session (Instagram's login cookies - never the password) is encrypted with
# Windows DPAPI before it touches the disk. Only the same Windows user on the same
# PC can decrypt it; a copied file is useless anywhere else. It never leaves the PC
# except as cookies sent to instagram.com itself.
_ENTROPY = b"RetroGrab/instagram-session/v1"


def _dpapi(data, protect):
    import ctypes
    from ctypes import wintypes

    class BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    def blob(b):
        buf = ctypes.create_string_buffer(b, len(b))
        return BLOB(len(b), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), buf

    inp, _k1 = blob(data)
    ent, _k2 = blob(_ENTROPY)
    out = BLOB()
    crypt32 = ctypes.windll.crypt32
    fn = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    # (in, description, entropy, reserved, prompt, flags=CRYPTPROTECT_UI_FORBIDDEN, out)
    if not fn(ctypes.byref(inp), None, ctypes.byref(ent), None, None, 0x1, ctypes.byref(out)):
        raise OSError("Windows could not " + ("encrypt" if protect else "decrypt") + " the Instagram session")
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out.pbData)


def save_instagram_session(cookies):
    """cookies: list of {name, value, domain, path, expires, secure}"""
    blob = _dpapi(json.dumps(cookies).encode("utf-8"), protect=True)
    tmp = IG_SESSION + ".tmp"
    with open(tmp, "wb") as f:
        f.write(blob)
    os.replace(tmp, IG_SESSION)


def _migrate_legacy_cookies():
    """1.0.x kept a plain-text cookie file and a browser profile - encrypt / delete them."""
    if os.path.isdir(LEGACY_WEBVIEW):
        shutil.rmtree(LEGACY_WEBVIEW, ignore_errors=True)
    if not os.path.isfile(LEGACY_COOKIES):
        return
    cookies = []
    try:
        with open(LEGACY_COOKIES, encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) == 7 and not line.startswith("#"):
                    cookies.append({"domain": parts[0], "path": parts[2], "secure": parts[3] == "TRUE",
                                    "expires": int(parts[4] or 0), "name": parts[5], "value": parts[6]})
        if cookies:
            save_instagram_session(cookies)
    except Exception:
        pass
    try:
        os.remove(LEGACY_COOKIES)
    except OSError:
        pass
    shutil.rmtree(LEGACY_WEBVIEW, ignore_errors=True)


def load_instagram_session():
    _migrate_legacy_cookies()
    try:
        with open(IG_SESSION, "rb") as f:
            return json.loads(_dpapi(f.read(), protect=False).decode("utf-8"))
    except Exception:
        return []


def has_instagram_login():
    return any(c.get("name") == "sessionid" and c.get("value") for c in load_instagram_session())


def delete_instagram_session():
    for p in (IG_SESSION, LEGACY_COOKIES):
        try:
            os.remove(p)
        except OSError:
            pass
    shutil.rmtree(WEBVIEW_TEMP, ignore_errors=True)
    shutil.rmtree(LEGACY_WEBVIEW, ignore_errors=True)
