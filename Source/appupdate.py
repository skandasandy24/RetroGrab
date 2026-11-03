"""RetroGrab self-update: checks GitHub Releases and can install a new version in place.

Check:   GET https://api.github.com/repos/<repo>/releases/latest   (no login, no personal data sent)
Install: download the release zip -> verify its SHA-256 (published by GitHub) -> unzip to
         data\\updates\\app -> a small batch file waits for RetroGrab to close, copies the new
         program files over the old ones (data\\ and Downloads\\ are never touched) and
         starts the new version.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import urllib.request
import zipfile

from common import APP_DIR, APP_VERSION, DATA, FROZEN

REPO = "skandasandy24/RetroGrab"
RELEASES_PAGE = f"https://github.com/{REPO}/releases/latest"
WORK = os.path.join(DATA, "updates", "app")
UA = {"User-Agent": f"RetroGrab/{APP_VERSION} (update check)", "Accept": "application/vnd.github+json"}


def vtuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or "0")[:4])


def check(current=APP_VERSION):
    """Returns info about a newer release, or None if this is the latest."""
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/releases/latest", headers=UA)
    with urllib.request.urlopen(req, timeout=15) as r:
        rel = json.load(r)
    version = (rel.get("tag_name") or "").lstrip("vV")
    if vtuple(version) <= vtuple(current):
        return None
    asset = next((a for a in rel.get("assets") or [] if a["name"].lower().endswith(".zip")), None)
    return {
        "version": version,
        "title": rel.get("name") or f"RetroGrab {version}",
        "notes": (rel.get("body") or "").strip(),
        "page": rel.get("html_url") or RELEASES_PAGE,
        "zip_url": asset and asset["browser_download_url"],
        "zip_size": asset and asset.get("size"),
        "sha256": (asset.get("digest") or "").split(":", 1)[-1] if asset and str(asset.get("digest", "")).startswith(
            "sha256:") else None,
    }


def can_install(info):
    """In-place install needs the packaged .exe, a zip asset and a writable program folder."""
    if not (FROZEN and info.get("zip_url")):
        return False
    try:
        probe = os.path.join(APP_DIR, ".update_test")
        with open(probe, "w") as f:
            f.write("ok")
        os.remove(probe)
        return True
    except OSError:
        return False


def download(info, progress=lambda done, total: None, cancelled=lambda: False):
    """Download + verify + unzip. Returns the folder holding the new RetroGrab.exe."""
    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK, exist_ok=True)
    zpath = os.path.join(WORK, "update.zip")
    h = hashlib.sha256()
    req = urllib.request.Request(info["zip_url"], headers={"User-Agent": UA["User-Agent"]})
    with urllib.request.urlopen(req, timeout=60) as r, open(zpath, "wb") as f:
        total = int(r.headers.get("Content-Length") or info.get("zip_size") or 0)
        done = 0
        while True:
            if cancelled():
                raise RuntimeError("Update cancelled.")
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            h.update(chunk)
            done += len(chunk)
            progress(done, total)
    if info.get("sha256") and h.hexdigest().lower() != info["sha256"].lower():
        raise RuntimeError("The download is damaged (checksum mismatch). Please try again.")

    new = os.path.join(WORK, "new")
    with zipfile.ZipFile(zpath) as z:
        for name in z.namelist():  # refuse paths that would escape the folder
            if name.startswith(("/", "\\")) or ".." in name.replace("\\", "/").split("/"):
                raise RuntimeError("Unexpected file in update package.")
        z.extractall(new)
    os.remove(zpath)
    for root, _dirs, files in os.walk(new):
        if "RetroGrab.exe" in files and os.path.isdir(os.path.join(root, "_internal")):
            return root
    raise RuntimeError("The update package doesn't contain RetroGrab.exe.")


def install_and_restart(new_dir):
    """Write and start the helper that swaps files once this process has exited."""
    bat = os.path.join(WORK, "apply_update.bat")
    script = f"""@echo off
chcp 65001 >nul
set "APPDIR={APP_DIR}"
set "NEW={new_dir}"
:wait
tasklist /FI "PID eq {os.getpid()}" 2>nul | find "{os.getpid()}" >nul
if not errorlevel 1 (
    ping -n 2 127.0.0.1 >nul
    goto wait
)
robocopy "%NEW%\\_internal" "%APPDIR%\\_internal" /MIR /R:5 /W:1 /NFL /NDL /NJH /NJS /NP >nul
copy /Y "%NEW%\\RetroGrab.exe" "%APPDIR%\\RetroGrab.exe" >nul
if exist "%NEW%\\README.txt" copy /Y "%NEW%\\README.txt" "%APPDIR%\\README.txt" >nul
start "" "%APPDIR%\\RetroGrab.exe"
rmdir /S /Q "%NEW%"
"""
    with open(bat, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(script)
    subprocess.Popen(["cmd.exe", "/c", bat], cwd=WORK, close_fds=True,
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    # the caller now closes RetroGrab; the helper finishes the swap and restarts it
