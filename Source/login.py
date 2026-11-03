"""Instagram login window (runs in its own process).

What happens, in order:
1. A small Microsoft Edge (WebView2) window opens instagram.com's own login page,
   in InPrivate mode, so nothing is remembered by the browser itself.
2. You log in on Instagram's real page. RetroGrab never reads, sees or stores
   your username or password; they go only to instagram.com.
3. When Instagram sets its session cookie, RetroGrab copies the instagram.com
   cookies, encrypts them with Windows DPAPI (see common.py) into
   data\\instagram_session.bin, and closes the window.
4. The temporary browser folder is deleted.

The session is only ever sent back to instagram.com when you download.
Log out in RetroGrab deletes it. "Log out of all devices" in Instagram's own
settings also makes it useless immediately.
"""
import os
import shutil
import time
from email.utils import parsedate_to_datetime

from common import WEBVIEW_TEMP, save_instagram_session

LOGIN_URL = "https://www.instagram.com/accounts/login/"


def _expiry(morsel):
    """Expiry as epoch seconds. Session cookies (no/invalid date) get 90 days."""
    fallback = int(time.time()) + 90 * 86400
    raw = morsel.get("expires")
    try:
        ts = int(parsedate_to_datetime(raw).timestamp()) if raw else 0
    except Exception:
        ts = 0
    return ts if ts > time.time() else fallback


def _to_dicts(cookie_jars):
    out = []
    for jar in cookie_jars:
        for name, m in jar.items():
            domain = m.get("domain") or ".instagram.com"
            if "instagram.com" not in domain:
                continue  # keep only Instagram's own cookies
            out.append({"name": name, "value": m.value, "domain": domain if domain.startswith(".") else "." + domain,
                        "path": m.get("path") or "/", "secure": bool(m.get("secure")), "expires": _expiry(m)})
    return out


def run():
    import webview

    shutil.rmtree(WEBVIEW_TEMP, ignore_errors=True)
    window = webview.create_window("Log in to Instagram - RetroGrab", LOGIN_URL, width=460, height=760)
    result = {"ok": False}

    def watch():
        deadline = time.time() + 20 * 60
        while time.time() < deadline:
            time.sleep(1.5)
            try:
                jars = window.get_cookies()
            except Exception:
                continue
            if any(name == "sessionid" and m.value for jar in jars for name, m in jar.items()):
                time.sleep(2)  # let Instagram finish setting the rest
                try:
                    jars = window.get_cookies()
                except Exception:
                    pass
                save_instagram_session(_to_dicts(jars))
                result["ok"] = True
                window.destroy()
                return

    try:
        webview.start(watch, private_mode=True, storage_path=WEBVIEW_TEMP)
    finally:
        for _ in range(10):  # WebView2 may hold its folder for a moment after closing
            shutil.rmtree(WEBVIEW_TEMP, ignore_errors=True)
            if not os.path.exists(WEBVIEW_TEMP):
                break
            time.sleep(0.5)
    return 0 if result["ok"] else 1
