"""Download engine: YouTube (yt-dlp), Instagram (yt-dlp + gallery-dl), Spotify (metadata + YouTube)."""
import logging
import os
import re

import yt_dlp
from yt_dlp.utils import DownloadCancelled, sanitize_filename

import spotify
from common import COOKIES, ffmpeg_location, has_instagram_login, js_runtimes


class Cancelled(Exception):
    pass


class JobError(Exception):
    pass


VIDEO_SORT = {"mp4": ["ext:mp4:m4a"], "webm": ["ext:webm:webm"], "mkv": ["res"]}


def human_bytes(n):
    if not n:
        return "?"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} TB"


def human_time(s):
    if s is None:
        return "--:--"
    s = int(s)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60:02d}:{s % 60:02d}"


class YDLLogger:
    def __init__(self, rep):
        self.rep = rep

    def debug(self, msg):
        if not msg.startswith("[debug] "):
            self.rep.log(msg)

    def info(self, msg):
        self.rep.log(msg)

    def warning(self, msg):
        self.rep.log("WARNING: " + msg)

    def error(self, msg):
        self.rep.log(msg)


def base_opts(rep, cancel, folder, on_saved=None):
    def progress_hook(d):
        if cancel.is_set():
            raise DownloadCancelled("Cancelled by user")
        info = d.get("info_dict") or {}
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            done = d.get("downloaded_bytes") or 0
            pct = done * 100 / total if total else None
            if pct is None and d.get("fragment_count"):
                pct = (d.get("fragment_index") or 0) * 100 / d["fragment_count"]
            kind = "audio" if info.get("vcodec") == "none" else ("video" if info.get("acodec") == "none" else "file")
            rep.progress(pct, f"{(pct or 0):.1f}% of {human_bytes(total)}   ETA {human_time(d.get('eta'))}"
                              f"   ({kind} stream)", human_bytes(d.get("speed")) + "/s" if d.get("speed") else "")
            rep.status("Downloading...")
        elif d["status"] == "finished":
            rep.progress(100, "Stream finished.", "")

    def pp_hook(d):
        if cancel.is_set():
            raise DownloadCancelled("Cancelled by user")
        if d["status"] == "started":
            names = {"Merger": "Merging video + audio", "ExtractAudio": "Converting audio",
                     "VideoRemuxer": "Converting video", "EmbedThumbnail": "Embedding thumbnail",
                     "EmbedSubtitle": "Embedding subtitles"}
            pp = d.get("postprocessor", "")
            rep.status(next((v for k, v in names.items() if k in pp), "Processing") + "...")

    def title_hook(d):
        info = d.get("info_dict") or {}
        if info.get("title"):
            idx = info.get("playlist_index")
            n = info.get("n_entries") or info.get("playlist_count")
            prefix = f"[{idx}/{n}] " if idx and n else ""
            rep.title(prefix + info["title"])

    opts = {
        "logger": YDLLogger(rep),
        "noprogress": True,
        "progress_hooks": [title_hook, progress_hook],
        "postprocessor_hooks": [pp_hook],
        "js_runtimes": js_runtimes(),
        "paths": {"home": folder},
        "windowsfilenames": True,
        "retries": 5,
        "fragment_retries": 5,
        "concurrent_fragment_downloads": 4,
        "post_hooks": [on_saved] if on_saved else [],
    }
    ff = ffmpeg_location()
    if ff:
        opts["ffmpeg_location"] = ff
    return opts


def audio_pp(fmt, quality):
    q = "0" if quality == "Best" or fmt in ("wav", "flac") else quality.split()[0]
    return {"key": "FFmpegExtractAudio", "preferredcodec": fmt, "preferredquality": q}


def apply_media_choice(opts, mode, fmt, quality):
    """Fill format selection + postprocessors for Video+Audio / Video only / Audio only."""
    pps = opts.setdefault("postprocessors", [])
    if mode == "Audio only":
        opts["format"] = "ba/b"
        pps.append(audio_pp(fmt, quality))
        return
    h = "" if quality == "Best" else f"[height<={quality.split('p')[0]}]"
    opts["format_sort"] = VIDEO_SORT.get(fmt, ["res"])
    if mode == "Video only":
        opts["format"] = f"bv{h}/bv*{h}/bv"
        pps.append({"key": "FFmpegVideoRemuxer", "preferedformat": fmt})
    else:
        opts["format"] = f"bv*{h}+ba/b{h}/bv*+ba/b"
        opts["merge_output_format"] = fmt


def _run_ydl(opts, urls, cancel):
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            code = ydl.download(urls)
    except DownloadCancelled:
        raise Cancelled()
    except yt_dlp.utils.DownloadError as e:
        if cancel.is_set():
            raise Cancelled()
        raise JobError(re.sub(r"^ERROR:\s*", "", str(e)))
    if cancel.is_set():
        raise Cancelled()
    if code:
        raise JobError("Some items failed - see Tools > Show log.")


# ---------------------------------------------------------------- YouTube
def run_youtube(job, rep, cancel):
    o = job["opts"]
    folder = os.path.join(o["folder"], "YouTube")
    opts = base_opts(rep, cancel, folder, on_saved=lambda p: rep.saved(p, "YouTube"))
    opts["outtmpl"] = {"default": "%(title).150B [%(id)s].%(ext)s",
                       "pl_video": "%(playlist_title).80B/%(playlist_index)03d - %(title).150B [%(id)s].%(ext)s"}
    opts["noplaylist"] = not o.get("playlist")
    apply_media_choice(opts, o["mode"], o["fmt"], o["quality"])
    pps = opts["postprocessors"]
    if o.get("subs") and o["mode"] != "Audio only":
        opts.update(writesubtitles=True, subtitleslangs=["en.*", "en"])
        pps.append({"key": "FFmpegEmbedSubtitle", "already_have_subtitle": False})
    if o.get("thumb") and o["fmt"] not in ("webm", "opus", "wav"):
        opts["writethumbnail"] = True
        pps.append({"key": "EmbedThumbnail", "already_have_thumbnail": False})
    _run_ydl(opts, [job["url"]], cancel)


# -------------------------------------------------------------- Instagram
def instagram_kind(url):
    if re.search(r"instagram\.com/(?:[\w.]+/)?(?:reel|reels|tv)/", url):
        return "reel"
    if re.search(r"instagram\.com/(?:[\w.]+/)?p/", url):
        return "post"
    if "/stories/" in url:
        return "story"
    return "profile"


def _gallery_dl(url, folder, rep, cancel):
    from gallery_dl import config as gconfig, job as gjob, output as goutput

    gconfig.clear()
    gconfig.set((), "base-directory", folder)
    gconfig.set(("extractor",), "directory", ["{username}"])
    gconfig.set(("extractor",), "filename", "{username} {date:%Y-%m-%d} {shortcode}_{num:>02}.{extension}")
    gconfig.set(("extractor", "instagram"), "videos", True)
    gconfig.set(("downloader",), "progress", 0.0)
    gconfig.set(("output",), "mode", "null")
    if has_instagram_login():
        gconfig.set(("extractor",), "cookies", COOKIES)

    class Out(goutput.NullOutput):
        def start(self, path):
            if cancel.is_set():
                raise Cancelled()
            rep.title(os.path.basename(path))
            rep.progress(None, "Starting...", "")

        def skip(self, path):
            rep.log(f"Already have: {path}")

        def success(self, path):
            Job.count += 1
            rep.progress(100, f"Saved file {Job.count}", "")
            rep.log(f"Saved: {path}")
            rep.saved(path, "Instagram")

        def progress(self, total, done, rate):
            if cancel.is_set():
                raise Cancelled()
            pct = done * 100 / total if total else None
            rep.progress(pct, f"File {Job.count + 1}: {human_bytes(done)} of {human_bytes(total)}",
                         human_bytes(rate) + "/s")

    class Job(gjob.DownloadJob):
        count = 0

        def __init__(self, url, parent=None):
            super().__init__(url, parent)
            self.out = Out()

    class Handler(logging.Handler):
        def emit(self, record):
            rep.log(f"[{record.name}] {record.getMessage()}")

    handler = Handler(logging.INFO)
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)
    rep.status("Downloading from Instagram...")
    try:
        status = Job(url).run()
    finally:
        logging.getLogger().removeHandler(handler)
    if cancel.is_set():
        raise Cancelled()
    if Job.count == 0 and status:
        if not has_instagram_login():
            raise JobError("Instagram wants you to log in. Click 'Log in to Instagram' on the Instagram tab.")
        raise JobError("Instagram download failed - see Tools > Show log.")
    if status & 4:
        raise JobError(f"Saved {Job.count} file(s), but some failed.")


def run_instagram(job, rep, cancel):
    o = job["opts"]
    url = job["url"]
    folder = os.path.join(o["folder"], "Instagram")
    kind = instagram_kind(url)

    if o["ig_mode"] == "Audio only (MP3)" or (kind == "reel" and o["ig_mode"] == "Auto"):
        opts = base_opts(rep, cancel, folder, on_saved=lambda p: rep.saved(p, "Instagram"))
        opts["outtmpl"] = {"default": "%(uploader,channel|instagram).60B - %(title).80B [%(id)s].%(ext)s"}
        opts["noplaylist"] = kind != "profile"
        if has_instagram_login():
            opts["cookiefile"] = COOKIES
        if o["ig_mode"] == "Audio only (MP3)":
            apply_media_choice(opts, "Audio only", "mp3", "Best")
        else:
            apply_media_choice(opts, "Video + Audio", "mp4", "Best")
        try:
            _run_ydl(opts, [url], cancel)
            return
        except JobError as e:
            if o["ig_mode"] == "Audio only (MP3)":
                if not has_instagram_login():
                    raise JobError(f"{e}  (Tip: log in to Instagram first.)")
                raise
            rep.log(f"yt-dlp couldn't get it ({e}); trying gallery-dl...")
    _gallery_dl(url, folder, rep, cancel)


# ---------------------------------------------------------------- Spotify
def run_spotify(job, rep, cancel):
    o = job["opts"]
    rep.status("Reading Spotify info...")
    rep.progress(None, "Contacting Spotify...", "")
    try:
        name, tracks = spotify.get_tracks(job["url"])
    except RuntimeError as e:
        raise JobError(str(e))
    except Exception as e:
        raise JobError(f"Couldn't read the Spotify link: {e}")
    if not tracks:
        raise JobError("No songs found at that Spotify link.")

    folder = os.path.join(o["folder"], "Spotify")
    if name and o.get("subfolder"):
        folder = os.path.join(folder, sanitize_filename(name))
    fmt = o["fmt"]
    rep.log(f"Spotify: {name or 'single track'} - {len(tracks)} song(s)")

    search_opts = {"logger": YDLLogger(rep), "quiet": True, "extract_flat": "in_playlist",
                   "js_runtimes": js_runtimes(), "noprogress": True}
    failed = []
    with yt_dlp.YoutubeDL(search_opts) as searcher:
        for i, t in enumerate(tracks, 1):
            if cancel.is_set():
                raise Cancelled()
            label = f"{', '.join(t['artists'])} - {t['title']}"
            rep.title(f"[{i}/{len(tracks)}] {label}")
            rep.progress(0, "Searching YouTube for the best match...", "")
            rep.status(f"Song {i} of {len(tracks)}")
            base = sanitize_filename(label)[:180]
            target = os.path.join(folder, f"{base}.{fmt}")
            if o.get("skip_existing") and os.path.exists(target):
                rep.log(f"Already have: {base}")
                continue
            try:
                res = searcher.extract_info(f"ytsearch8:{spotify.search_query(t)}", download=False)
                entries = [e for e in (res.get("entries") or []) if e and e.get("id")]
                if not entries:
                    raise JobError("no YouTube results")
                best = max(entries, key=lambda e: spotify.score(e, t))
                rep.log(f"Match for '{label}': {best.get('title')} ({best.get('channel') or best.get('uploader')})")

                saved = []
                opts = base_opts(rep, cancel, folder, on_saved=saved.append)
                opts["progress_hooks"] = opts["progress_hooks"][1:]  # keep the Spotify title
                opts["outtmpl"] = {"default": base.replace("%", "%%") + ".%(ext)s"}
                opts["noplaylist"] = True
                apply_media_choice(opts, "Audio only", fmt, o["quality"])
                _run_ydl(opts, [f"https://www.youtube.com/watch?v={best['id']}"], cancel)

                path = saved[-1] if saved else target
                rep.status("Adding song info & cover art...")
                cover_url = t.get("cover") or spotify.track_cover(t["id"])
                cover = spotify.download_bytes(cover_url) if cover_url else None
                try:
                    spotify.tag_file(path, t, cover)
                except Exception as e:
                    rep.log(f"WARNING: couldn't tag {base}: {e}")
                rep.saved(path, "Spotify")
            except Cancelled:
                raise
            except Exception as e:
                failed.append(label)
                rep.log(f"FAILED: {label} - {e}")
    if failed:
        if len(failed) == len(tracks):
            raise JobError("Couldn't download any of the songs - see Tools > Show log.")
        raise JobError(f"{len(tracks) - len(failed)} of {len(tracks)} songs saved; {len(failed)} failed.")


RUNNERS = {"YouTube": run_youtube, "Instagram": run_instagram, "Spotify": run_spotify}
