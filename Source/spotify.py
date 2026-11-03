"""Spotify support: read public track/album/playlist info, then match songs on YouTube.

Spotify's own audio is DRM-protected and is never touched. Only the public
metadata (title, artists, length, cover art) is read from Spotify's embed page.
"""
import json
import re
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"}

URL_RE = re.compile(r"(?:open\.spotify\.com/(?:intl-[\w-]+/)?|spotify:)(track|album|playlist)[/:]([A-Za-z0-9]{22})")

BAD_WORDS = ["live", "cover", "remix", "karaoke", "instrumental", "sped up", "slowed", "reverb",
             "8d", "nightcore", "acoustic", "mashup", "bass boosted", "reaction", "tutorial"]


def parse_url(url):
    m = URL_RE.search(url)
    return (m.group(1), m.group(2)) if m else (None, None)


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read()


def _entity(kind, sid):
    html = _get(f"https://open.spotify.com/embed/{kind}/{sid}").decode("utf-8", "replace")
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        raise RuntimeError("Spotify page format changed - couldn't read song info.")
    try:
        return json.loads(m.group(1))["props"]["pageProps"]["state"]["data"]["entity"]
    except (KeyError, TypeError):
        raise RuntimeError("That Spotify link is private, removed, or not available in your region.")


def _best_image(entity):
    imgs = (entity.get("visualIdentity") or {}).get("image") or []
    if imgs:
        return max(imgs, key=lambda i: i.get("maxWidth") or 0)["url"]
    srcs = (entity.get("coverArt") or {}).get("sources") or []
    return srcs[0]["url"] if srcs else None


def _split_artists(s):
    return [a.strip() for a in (s or "").replace("\xa0", " ").split(",") if a.strip()]


def get_tracks(url):
    """Return (collection_name or None, [track dicts])."""
    kind, sid = parse_url(url)
    if not kind:
        raise RuntimeError("Not a Spotify track, album or playlist link.")
    e = _entity(kind, sid)
    if kind == "track":
        year = ((e.get("releaseDate") or {}).get("isoString") or "")[:4]
        return None, [{
            "id": e["id"], "title": e.get("title") or e.get("name"),
            "artists": [a["name"] for a in e.get("artists") or []],
            "duration": (e.get("duration") or 0) / 1000, "album": None,
            "year": year, "number": None, "cover": _best_image(e),
        }]

    name = e.get("title") or e.get("name")
    cover = _best_image(e) if kind == "album" else None
    tracks = []
    for i, t in enumerate(e.get("trackList") or [], 1):
        tracks.append({
            "id": (t.get("uri") or "").rsplit(":", 1)[-1], "title": t.get("title"),
            "artists": _split_artists(t.get("subtitle")), "duration": (t.get("duration") or 0) / 1000,
            "album": name if kind == "album" else None, "year": "",
            "number": i if kind == "album" else None, "cover": cover,
        })
    return name, tracks


def track_cover(track_id):
    """Cover art for a single track via Spotify's public oEmbed endpoint."""
    try:
        data = json.loads(_get("https://open.spotify.com/oembed?url=" + urllib.parse.quote(
            f"https://open.spotify.com/track/{track_id}")))
        return data.get("thumbnail_url")
    except Exception:
        return None


def download_bytes(url):
    try:
        return _get(url)
    except Exception:
        return None


def _words(s):
    return set(re.findall(r"[a-z0-9]+", (s or "").lower()))


def score(entry, track):
    """Higher is better. Compares a YouTube search result with the Spotify track."""
    yt_title = (entry.get("title") or "").lower()
    channel = (entry.get("channel") or entry.get("uploader") or "").lower()
    sp_title = (track["title"] or "").lower()
    s = 0.0

    dur = entry.get("duration")
    if dur and track["duration"]:
        diff = abs(dur - track["duration"])
        s -= min(diff, 120)
        if diff > 25:
            s -= 40
    else:
        s -= 15

    for w in BAD_WORDS:
        if re.search(rf"\b{re.escape(w)}\b", yt_title) and w not in sp_title:
            s -= 30
    if channel.endswith(" - topic"):
        s += 20
    if "official audio" in yt_title or "audio" in yt_title:
        s += 8
    if "official video" in yt_title or "music video" in yt_title:
        s -= 4  # videos often have intros/outros

    want = _words(sp_title)
    if want:
        s += 25 * len(want & _words(yt_title)) / len(want)
    artists = [a.lower() for a in track["artists"]]
    if artists and any(a in yt_title or a in channel for a in artists):
        s += 15
    return s


def search_query(track):
    return f"{', '.join(track['artists'][:2])} - {track['title']}"


def tag_file(path, track, cover_bytes):
    """Write title/artist/album/cover into the audio file."""
    ext = path.lower().rsplit(".", 1)[-1]
    artists = ", ".join(track["artists"])
    if ext == "mp3":
        from mutagen.id3 import APIC, ID3, TALB, TDRC, TIT2, TPE1, TPE2, TRCK, ID3NoHeaderError
        try:
            tags = ID3(path)
        except ID3NoHeaderError:
            tags = ID3()
        tags.delall("APIC")
        tags.add(TIT2(encoding=3, text=track["title"]))
        tags.add(TPE1(encoding=3, text=artists))
        if track["artists"]:
            tags.add(TPE2(encoding=3, text=track["artists"][0]))
        if track.get("album"):
            tags.add(TALB(encoding=3, text=track["album"]))
        if track.get("year"):
            tags.add(TDRC(encoding=3, text=track["year"]))
        if track.get("number"):
            tags.add(TRCK(encoding=3, text=str(track["number"])))
        if cover_bytes:
            tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=cover_bytes))
        tags.save(path, v2_version=3)
    elif ext in ("m4a", "mp4"):
        from mutagen.mp4 import MP4, MP4Cover
        f = MP4(path)
        f["\xa9nam"] = track["title"]
        f["\xa9ART"] = artists
        if track.get("album"):
            f["\xa9alb"] = track["album"]
        if track.get("year"):
            f["\xa9day"] = track["year"]
        if track.get("number"):
            f["trkn"] = [(track["number"], 0)]
        if cover_bytes:
            f["covr"] = [MP4Cover(cover_bytes, imageformat=MP4Cover.FORMAT_JPEG)]
        f.save()
