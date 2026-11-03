"""Self-updater for the download engines.

yt-dlp, yt-dlp-ejs and gallery-dl are pure-Python, so a newer wheel (a zip file)
downloaded from PyPI can be imported directly by putting it on sys.path.
This lets the packaged .exe stay current without being rebuilt.
"""
import hashlib
import json
import os
import re
import sys
import urllib.request

from common import UPDATES, VENDOR, load_json, save_json

PACKAGES = {"yt-dlp": "yt_dlp", "yt-dlp-ejs": "yt_dlp_ejs", "gallery-dl": "gallery_dl"}
MANIFEST = os.path.join(UPDATES, "manifest.json")
UA = {"User-Agent": "RetroGrab-updater"}


def vtuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or "0"))


def bundled_versions():
    data = load_json(os.path.join(VENDOR, "versions.json"), {})
    if data:
        return data
    try:
        from importlib.metadata import version
        return {p: version(p) for p in PACKAGES}
    except Exception:
        return {}


def activate():
    """Call before importing yt_dlp / gallery_dl. Puts newer downloaded wheels first."""
    manifest = load_json(MANIFEST, {})
    bundled = bundled_versions()
    active = {}
    # Remove superseded wheels (safe now - nothing has imported them yet).
    keep = {os.path.normcase(e["file"]) for e in manifest.values()}
    try:
        for fn in os.listdir(UPDATES):
            p = os.path.join(UPDATES, fn)
            if fn.endswith(".whl") and os.path.normcase(p) not in keep:
                os.remove(p)
    except OSError:
        pass
    for pypi in PACKAGES:
        entry = manifest.get(pypi)
        if entry and os.path.isfile(entry["file"]) and vtuple(entry["version"]) > vtuple(bundled.get(pypi)):
            sys.path.insert(0, entry["file"])
            active[pypi] = entry["version"]
        else:
            active[pypi] = bundled.get(pypi, "?")
    return active


def _pypi(name, version=None):
    url = f"https://pypi.org/pypi/{name}/{version + '/' if version else ''}json"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)


def _fetch_wheel(name, meta, log):
    ver = meta["info"]["version"]
    wheel = next((u for u in meta["urls"] if u["packagetype"] == "bdist_wheel"
                  and u["filename"].endswith("py3-none-any.whl")), None)
    if not wheel:
        raise RuntimeError(f"No universal wheel for {name} {ver}")
    os.makedirs(UPDATES, exist_ok=True)
    dest = os.path.join(UPDATES, wheel["filename"])
    log(f"Downloading {wheel['filename']} ...")
    with urllib.request.urlopen(urllib.request.Request(wheel["url"], headers=UA), timeout=120) as r:
        blob = r.read()
    if hashlib.sha256(blob).hexdigest() != wheel["digests"]["sha256"]:
        raise RuntimeError(f"Checksum mismatch for {wheel['filename']}")
    with open(dest, "wb") as f:
        f.write(blob)
    return ver, dest


def update(current, log=print):
    """Download newer engine wheels. `current` = versions now in use. Returns list of updated names."""
    manifest = load_json(MANIFEST, {})
    updated = []

    ytdlp = _pypi("yt-dlp")
    targets = {"yt-dlp": ytdlp, "gallery-dl": _pypi("gallery-dl")}
    # yt-dlp pins an exact yt-dlp-ejs version - fetch exactly that one.
    pin = None
    for req in ytdlp["info"].get("requires_dist") or []:
        m = re.match(r"yt-dlp-ejs\s*==\s*([\w.]+)", req)
        if m:
            pin = m.group(1)
    targets["yt-dlp-ejs"] = _pypi("yt-dlp-ejs", pin)

    for name, meta in targets.items():
        latest = meta["info"]["version"]
        if vtuple(latest) <= vtuple(current.get(name)):
            log(f"{name} is up to date ({current.get(name)}).")
            continue
        ver, path = _fetch_wheel(name, meta, log)
        manifest[name] = {"version": ver, "file": path}
        updated.append(f"{name} {ver}")
        log(f"{name} updated to {ver}.")
    save_json(MANIFEST, manifest)
    return updated
