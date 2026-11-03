"""Spotify support: read public track/album/playlist info, then match songs on YouTube.

Spotify's own audio is DRM-protected and is never touched. Only the public
metadata (title, artists, length, cover art) is read from Spotify's embed page.
"""
import json
import re
import unicodedata
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


# Songs from Indian films (and many others) are released in several languages with
# the same tune and near-identical titles - the language tag is what tells them apart.
LANGUAGES = {
    "tamil": "tamil", "telugu": "telugu", "hindi": "hindi", "kannada": "kannada",
    "malayalam": "malayalam", "marathi": "marathi", "bengali": "bengali", "bangla": "bengali",
    "punjabi": "punjabi", "gujarati": "gujarati", "odia": "odia", "bhojpuri": "bhojpuri",
    "urdu": "urdu", "english": "english", "spanish": "spanish", "korean": "korean",
    "japanese": "japanese", "chinese": "chinese", "french": "french", "arabic": "arabic",
}


def norm(s):
    """Lowercase, unify quotes/width (Spotify and YouTube differ), keep only words."""
    s = unicodedata.normalize("NFKC", s or "").lower()
    s = re.sub(r"[\"'“”‘’`＂]", "", s)
    return re.sub(r"[^\w]+", " ", s).strip()


def languages(text):
    words = set(norm(text).split())
    return {LANGUAGES[w] for w in words if w in LANGUAGES}


def core_title(title):
    """'Veezha Veera (From "X") [Tamil]' -> 'veezha veera'"""
    return norm(re.split(r"\s*[\(\[]|\s+-\s+", title or "", maxsplit=1)[0])


def score(entry, track):
    """Higher is better. Compares a YouTube / YouTube Music result with the Spotify track."""
    yt_title = (entry.get("title") or "").lower()
    channel = (entry.get("channel") or entry.get("uploader") or "").lower()
    sp_title = (track["title"] or "").lower()
    s = 0.0

    # exact title (after normalising quotes etc.) is the strongest signal
    if norm(yt_title) == norm(sp_title):
        s += 60
    elif core_title(sp_title) and core_title(sp_title) in norm(yt_title):
        s += 15

    # language versions: [Tamil] must not become the [Telugu] version
    want = languages(f"{track['title']} {track.get('album') or ''}")
    got = languages(yt_title)
    if want:
        if got & want:
            s += 30
        elif got:
            s -= 100
        elif track.get("_strict_lang"):
            s -= 60  # user picked a language: unlabelled uploads can't be trusted to be it

    if entry.get("_source") == "ytmusic":
        s += 10  # official track audio, no video intro/outro

    dur = entry.get("duration")
    if dur and track["duration"]:
        diff = abs(dur - track["duration"])
        s -= min(diff, 120)
        if diff > 25:
            s -= 40
    elif not dur:
        s -= 5  # unknown here; checked before downloading

    for w in BAD_WORDS:
        if re.search(rf"\b{re.escape(w)}\b", yt_title) and w not in sp_title:
            s -= 30
    if channel.endswith(" - topic"):
        s += 20
    if "official audio" in yt_title or "audio" in yt_title:
        s += 8
    if "official video" in yt_title or "music video" in yt_title:
        s -= 4  # videos often have intros/outros

    words = _words(sp_title)
    if words:
        s += 25 * len(words & _words(yt_title)) / len(words)
    artists = [a.lower() for a in track["artists"]]
    if artists and any(a in yt_title or a in channel for a in artists):
        s += 15
    return s


def search_query(track):
    return f"{', '.join(track['artists'][:2])} - {track['title']}"


_LANG_TAG = re.compile(r"\s*[\[\(]\s*(" + "|".join(LANGUAGES) + r")(?:\s+version)?\s*[\]\)]", re.I)


def strip_language(title):
    """'Song (From "X") [Tamil]' -> 'Song (From "X")'"""
    return _LANG_TAG.sub("", title or "").strip()


def with_language(track, lang):
    """Copy of the track asking for a specific language version (results must be labelled with it)."""
    t = dict(track)
    t["title"] = f"{strip_language(track['title'])} [{lang.title()}]"
    t["album"] = strip_language(track.get("album") or "") or None
    t["_strict_lang"] = True
    return t


def _ytm_search(searcher, query, n, log):
    try:
        res = searcher.extract_info("https://music.youtube.com/search?q=" + urllib.parse.quote(query) + "#songs",
                                    download=False)
    except Exception as e:
        log(f"YouTube Music search failed ({e}).")
        return []
    out = []
    for e in (res.get("entries") or [])[:n]:
        if e and e.get("id"):
            e["_source"] = "ytmusic"
            out.append(e)
    return out


def _merge(*lists):
    seen, unique = set(), []
    for lst in lists:
        for e in lst:
            if e["id"] not in seen:
                seen.add(e["id"])
                unique.append(e)
    return unique


def spotify_language(track):
    langs = languages(f"{track['title']} {track.get('album') or ''}")
    return next(iter(langs)) if len(langs) == 1 else None


def gather(searcher, track, log=lambda m: None):
    """Search YouTube Music (official tracks) + YouTube. The YouTube Music search leaves
    out the language tag so that every language version of the song shows up."""
    plain = dict(track, title=strip_language(track["title"]))
    lists = [_ytm_search(searcher, search_query(plain), 10, log)]
    if plain["title"] != track["title"]:
        lists.append(_ytm_search(searcher, search_query(track), 5, log))
    try:
        res = searcher.extract_info(f"ytsearch8:{search_query(track)}", download=False)
        lists.append([e for e in (res.get("entries") or []) if e and e.get("id")])
    except Exception as e:
        log(f"YouTube search failed: {e}")
    return _merge(*lists)


def find_language_version(searcher, track, lang, candidates, log=lambda m: None):
    """Best match for the chosen language - searches for that version specifically too."""
    t = with_language(track, lang)
    extra = _ytm_search(searcher, search_query(t), 5, log)
    return find_match(searcher, t, log, candidates=_merge(extra, candidates))


def available_languages(candidates, track):
    """Languages this song is offered in, judged from results that look like the same song
    (similar title - 'Veezha Veera' vs 'Veera Veera' - or the same film, and similar length)."""
    want = _words(core_title(track["title"]))
    film = re.search(r"\(from\s+(.+?)\)", norm_quotes(track["title"]), re.I)
    found = set()
    for e in candidates:
        title = e.get("title") or ""
        langs = languages(title)
        if len(langs) != 1:
            continue
        if e.get("duration") and track["duration"] and abs(e["duration"] - track["duration"]) > 25:
            continue
        same_title = want and len(want & _words(core_title(title))) / len(want) >= 0.5
        same_film = film and norm(film.group(1)) in norm(title)
        if same_title and (same_film or not film):
            found |= langs
    return sorted(found)


def norm_quotes(s):
    return unicodedata.normalize("NFKC", s or "").replace("＂", '"')


def find_match(searcher, track, log=lambda m: None, candidates=None):
    """Best YouTube video for a Spotify track, or None.

    Ranks the candidates against the track. If the best one's length is unknown it's
    looked up, and anything more than 25 s off from Spotify's length is skipped.
    """
    if candidates is None:
        candidates = gather(searcher, track, log)
    ranked = sorted(candidates, key=lambda e: score(e, track), reverse=True)

    for e in ranked[:4]:
        if not e.get("duration") and track["duration"]:
            try:  # look up the real length before trusting it
                info = searcher.extract_info(f"https://www.youtube.com/watch?v={e['id']}",
                                             download=False, process=False)
                e["duration"] = info.get("duration")
                e.setdefault("channel", info.get("channel"))
            except Exception as ex:
                # e.g. YouTube's temporary "confirm you're not a bot" - keep the
                # candidate and rely on its title/language score instead
                log(f"Couldn't check the length of '{e.get('title')}' ({str(ex)[:80]}); using it anyway.")
        if e.get("duration") and track["duration"] and abs(e["duration"] - track["duration"]) > 25:
            log(f"Skipping '{e.get('title')}' - length {e['duration']}s vs Spotify {track['duration']:.0f}s")
            continue
        log(f"Match: {e.get('title')} [{e.get('_source', 'youtube')}]")
        return e
    return None


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
