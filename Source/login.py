"""Instagram login window (runs in its own process).

Opens instagram.com in a small Edge WebView2 window. The user logs in on
Instagram's real page; RetroGrab never sees the password. Once Instagram sets
its session cookie, the cookies are saved in Netscape format for yt-dlp and
gallery-dl, and the window closes itself.
"""
import os
import time
from email.utils import parsedate_to_datetime

from common import COOKIES, WEBVIEW_PROFILE

LOGIN_URL = "https://www.instagram.com/accounts/login/"


def _expiry(morsel):
    """Expiry as epoch seconds. Session cookies (no/invalid date) get 180 days."""
    fallback = int(time.time()) + 180 * 86400
    raw = morsel.get("expires")
    try:
        ts = int(parsedate_to_datetime(raw).timestamp()) if raw else 0
    except Exception:
        ts = 0
    return ts if ts > time.time() else fallback


def _write_cookies(cookies):
    lines = ["# Netscape HTTP Cookie File", "# Saved by RetroGrab - this is your Instagram login.", ""]
    for jar in cookies:
        for name, m in jar.items():
            domain = m.get("domain") or ".instagram.com"
            if not domain.startswith("."):
                domain = "." + domain
            secure = "TRUE" if m.get("secure") else "FALSE"
            lines.append("\t".join([domain, "TRUE", m.get("path") or "/", secure,
                                    str(_expiry(m)), name, m.value]))
    tmp = COOKIES + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, COOKIES)


def run():
    import webview

    window = webview.create_window("Log in to Instagram - RetroGrab", LOGIN_URL, width=460, height=760)
    result = {"ok": False}

    def watch():
        deadline = time.time() + 20 * 60
        while time.time() < deadline:
            time.sleep(1.5)
            try:
                cookies = window.get_cookies()
            except Exception:
                continue
            if any(name == "sessionid" and m.value for jar in cookies for name, m in jar.items()):
                time.sleep(2)  # let Instagram finish setting the rest
                try:
                    cookies = window.get_cookies()
                except Exception:
                    pass
                _write_cookies(cookies)
                result["ok"] = True
                window.destroy()
                return

    webview.start(watch, private_mode=False, storage_path=WEBVIEW_PROFILE)
    return 0 if result["ok"] else 1
