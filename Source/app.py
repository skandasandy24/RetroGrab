"""RetroGrab main window."""
import itertools
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox

import retro as R
from common import (APP_NAME, APP_VERSION, DATA, DEFAULT_FOLDER, FROZEN, HISTORY_FILE, IG_SESSION, SETTINGS_FILE,
                    delete_instagram_session, has_instagram_login, load_json, save_json)

IG_PRIVACY = (
    "How the Instagram login works:\n\n"
    "• You log in on Instagram's own page (instagram.com) in a private Microsoft Edge window.\n"
    "• RetroGrab never sees, reads or saves your username or password.\n"
    "• After you log in, only Instagram's session cookie is kept, encrypted by Windows so it "
    "only works for your Windows account on this PC. A copied file is useless elsewhere.\n"
    "• It is only ever sent to instagram.com, to download what you ask for. "
    "RetroGrab has no servers and sends nothing anywhere else.\n"
    "• 'Log out' deletes it. The code is open source, so anyone can check this "
    "(Source\\login.py and common.py).")

LOG_FILE = os.path.join(DATA, "retrograb.log")

MODES = ["Video + Audio", "Video only", "Audio only"]
VIDEO_FORMATS = ["mp4", "mkv", "webm"]
AUDIO_FORMATS = ["mp3", "m4a", "opus", "wav", "flac"]
VIDEO_QUALITIES = ["Best", "2160p (4K)", "1440p", "1080p", "720p", "480p", "360p", "240p", "144p"]
AUDIO_QUALITIES = ["Best", "320 kbps", "256 kbps", "192 kbps", "128 kbps", "96 kbps"]
HINTS = {"mp4": "Plays everywhere", "mkv": "Any codec, best for 4K", "webm": "Web format (VP9/AV1)",
         "mp3": "Plays everywhere", "m4a": "AAC, small & good", "opus": "Best quality per MB",
         "wav": "Uncompressed (huge)", "flac": "Lossless (large)"}
IG_MODES = ["Auto", "Audio only (MP3)", "Original files"]
IG_HINTS = {"Auto": "Reels -> MP4 video.  Posts & carousels -> all photos and videos.",
            "Audio only (MP3)": "Just the sound from a reel or video post.",
            "Original files": "Every photo/video exactly as Instagram stores it."}
TABS = ["YouTube", "Instagram", "Spotify", "History"]


def detect_service(url):
    u = url.lower()
    if "spotify.com" in u or u.startswith("spotify:"):
        return "Spotify"
    if "instagram.com" in u or "instagr.am" in u:
        return "Instagram"
    if "youtube.com" in u or "youtu.be" in u or "music.youtube" in u:
        return "YouTube"
    return None


class Reporter:
    """Thread-safe bridge from the worker thread to the UI."""

    def __init__(self, q, cancel=None):
        self.q = q
        self.cancel = cancel

    def ask_language(self, label, langs, default, multi):
        """Called from the worker: shows the language dialog and waits for the answer.
        Returns (language, use_for_rest) or None to skip the song."""
        done, box = threading.Event(), {}
        self.q.put(("ask_lang", (label, langs, default, multi, done, box)))
        while not done.wait(0.2):
            if self.cancel is not None and self.cancel.is_set():
                return None
        return box.get("answer")

    def log(self, m):
        self.q.put(("log", m))

    def status(self, m):
        self.q.put(("status", m))

    def title(self, m):
        self.q.put(("title", m))

    def progress(self, pct, detail, speed):
        self.q.put(("progress", (pct, detail, speed)))

    def saved(self, path, service):
        self.q.put(("saved", (path, service)))


class App:
    def __init__(self, root, engine_versions):
        self.root = root
        self.versions = engine_versions
        self.s = load_json(SETTINGS_FILE, {})
        self.history = load_json(HISTORY_FILE, [])
        self.jobs = []
        self.ids = itertools.count(1)
        self.events = queue.Queue()
        self.cancel_event = threading.Event()
        self.current = None
        self.worker = None
        self.log_lines = []
        self.log_win = None

        self.theme_var = tk.StringVar(value=self.s.get("theme", "Classic 95"))
        self.dark = bool(self.s.get("dark", False))
        root.title(APP_NAME)
        self.frame = R.RetroWindow(root, f"{APP_NAME} - YouTube / Instagram / Spotify Downloader", self.on_close)
        outer = self.frame.outer
        self._menu(outer)

        body = tk.Frame(outer, bg=R.GRAY, padx=10, pady=4)
        body.pack(fill="both", expand=True)

        # ---- tabs ----
        self.tabstrip = R.TabStrip(body, TABS, self.show_tab)
        self.tabstrip.pack(fill="x")
        stack = tk.Frame(body, bg=R.GRAY, relief="raised", bd=2, padx=8, pady=6)
        stack.pack(fill="x")
        stack.columnconfigure(0, weight=1)
        self.panels = {}
        for name, builder in (("YouTube", self._yt_panel), ("Instagram", self._ig_panel),
                              ("Spotify", self._sp_panel), ("History", self._hist_panel)):
            p = tk.Frame(stack, bg=R.GRAY)
            p.grid(row=0, column=0, sticky="nsew")
            builder(p)
            self.panels[name] = p

        # ---- save to ----
        g = R.group(body, "Save to")
        g.pack(fill="x", pady=(6, 3))
        self.folder = tk.StringVar(value=self.s.get("folder", DEFAULT_FOLDER))
        R.entry(g, self.folder).pack(side="left", fill="x", expand=True, ipady=2)
        R.button(g, "Browse...", self.browse).pack(side="left", padx=(6, 0))
        R.button(g, "Open", self.open_folder).pack(side="left", padx=(4, 0))

        # ---- action row ----
        row = tk.Frame(body, bg=R.GRAY)
        row.pack(fill="x", pady=3)
        self.dl_btn = R.button(row, "Download", self.add_jobs, width=12, default="active")
        self.dl_btn.pack(side="right")
        self.hint = R.label(row, "Tip: paste links from any site - they go to the right tab automatically.",
                            fg=R.DARK)
        self.hint.pack(side="left")

        # ---- queue ----
        g = R.group(body, "Queue")
        g.pack(fill="x", pady=3)
        wrap, self.qlist = R.scrolled_listbox(g, height=3)
        wrap.pack(side="left", fill="x", expand=True)
        qb = tk.Frame(g, bg=R.GRAY)
        qb.pack(side="left", padx=(6, 0), anchor="n")
        self.cancel_btn = R.button(qb, "Cancel", self.cancel_current, width=9, state="disabled")
        self.cancel_btn.pack(pady=(0, 3))
        R.button(qb, "Remove", self.remove_job, width=9).pack(pady=(0, 3))
        R.button(qb, "Clear done", self.clear_done, width=9).pack()

        # ---- progress ----
        g = R.group(body, "Progress")
        g.pack(fill="x", pady=3)
        self.now_title = tk.StringVar(value="Nothing downloading.")
        R.label(g, textvariable=self.now_title, anchor="w").pack(fill="x")
        self.bar = R.BlockProgress(g)
        self.bar.pack(fill="x", pady=3)
        self.detail = tk.StringVar(value="")
        R.label(g, textvariable=self.detail, anchor="w").pack(fill="x")

        # ---- status bar ----
        sbar = tk.Frame(outer, bg=R.GRAY)
        sbar.pack(fill="x", side="bottom", padx=2, pady=2)
        self.status = tk.StringVar(value="Ready")
        R.label(sbar, textvariable=self.status, relief="sunken", bd=1, anchor="w", padx=4).pack(
            side="left", fill="x", expand=True)
        self.speed = tk.StringVar(value="")
        R.label(sbar, textvariable=self.speed, relief="sunken", bd=1, width=16, anchor="w", padx=4).pack(
            side="left", padx=(2, 0))

        self.link_job = None
        for b in (self.yt_urls, self.ig_urls, self.sp_urls):
            self._watch_box(b)
        self.yt_playlist.trace_add("write", self.yt_refresh)
        self.refresh_login()
        self.refresh_history()
        self.on_yt_mode()
        self.show_tab(self.s.get("tab", "YouTube"))
        self.apply_theme(self.theme_var.get(), self.dark, save=False)
        self.frame.center(640)

        root.bind("<Control-Return>", lambda e: self.add_jobs())
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.after(80, self.poll)
        if "--test-url" in sys.argv:  # hidden: queue a URL through the real UI path (for troubleshooting)
            url = sys.argv[sys.argv.index("--test-url") + 1]
            root.after(500, lambda: self._test_url(url))
        else:
            root.after(300, self.autofill_clipboard)
            root.after(2500, self.check_app_update)
        self.add_log(f"--- {APP_NAME} {APP_VERSION} started {time.strftime('%Y-%m-%d %H:%M:%S')} ---")

    # ================================================================ app updates
    def check_app_update(self, manual=False):
        import appupdate

        def run():
            if not manual:
                appupdate.cleanup()  # leftovers from a previous update
            try:
                info = appupdate.check()
                err = None
            except Exception as e:
                info, err = None, e
            self.root.after(0, lambda: self._app_update_result(info, err, manual))

        threading.Thread(target=run, daemon=True).start()

    def _app_update_result(self, info, err, manual):
        if err:
            self.add_log(f"Update check failed: {err}")
            if manual:
                messagebox.showinfo(APP_NAME, f"Couldn't check for updates (no internet?).\n\n{err}")
            return
        if not info:
            if manual:
                messagebox.showinfo(APP_NAME, f"You have the latest version ({APP_VERSION}).")
            return
        if not manual and self.s.get("skip_version") == info["version"]:
            return
        self.add_log(f"Update available: {APP_VERSION} -> {info['version']}")
        self.update_dialog(info)

    def update_dialog(self, info):
        import appupdate
        import webbrowser

        w = tk.Toplevel(self.root)
        rw = R.RetroWindow(w, "Update available", w.destroy, minimizable=False)
        body = tk.Frame(rw.outer, bg=R.GRAY, padx=14, pady=10)
        body.pack(fill="both", expand=True)
        R.label(body, f"A new version of RetroGrab is available!", font=R.FONT_B, anchor="w").pack(fill="x")
        R.label(body, f"You have {APP_VERSION}.  New: {info['version']}  ({info['title']})", anchor="w").pack(
            fill="x", pady=(2, 8))
        wrap = tk.Frame(body, bg=R.GRAY, relief="sunken", bd=2)
        wrap.pack(fill="both", expand=True)
        notes = tk.Text(wrap, width=64, height=10, font=R.FONT, bg=R.WHITE, bd=0, wrap="word",
                        highlightthickness=0)
        notes.insert("1.0", re.sub(r"[*`]", "", info["notes"]) or "No release notes.")
        notes.configure(state="disabled")
        notes.pack(fill="both", expand=True, padx=4, pady=4)
        skip = tk.BooleanVar(value=False)
        R.check(body, "Don't remind me about this version", skip).pack(anchor="w", pady=(6, 0))
        status = tk.StringVar(value="Your settings, history, Instagram login and downloads are kept.")
        R.label(body, textvariable=status, fg=R.DARK, anchor="w").pack(fill="x", pady=(4, 0))
        row = tk.Frame(body, bg=R.GRAY)
        row.pack(fill="x", pady=(8, 0))

        def later():
            if skip.get():
                self.s["skip_version"] = info["version"]
                self.persist()
            w.destroy()

        def open_page():
            webbrowser.open(info["page"])
            later()

        def update_now():
            if self.current:
                messagebox.showinfo(APP_NAME, "Wait for the current download to finish, then update.", parent=w)
                return
            for b in buttons:
                b.configure(state="disabled")

            def progress(done, total):
                txt = f"Downloading update... {done * 100 // total}%" if total else "Downloading update..."
                self.root.after(0, lambda: status.set(txt))

            def run():
                try:
                    new_dir = appupdate.download(info, progress)
                    self.root.after(0, lambda: finish(new_dir))
                except Exception as e:
                    self.root.after(0, lambda: failed(e))

            threading.Thread(target=run, daemon=True).start()

        def finish(new_dir):
            status.set("Installing... RetroGrab will restart by itself.")
            self.persist()
            appupdate.install_and_restart(new_dir)
            self.root.after(300, self.root.destroy)

        def failed(e):
            self.add_log(f"Update failed: {e}")
            status.set(f"Update failed: {str(e)[:90]}")
            for b in buttons:
                b.configure(state="normal")

        buttons = []
        b = R.button(row, "Later", later, width=9)
        b.pack(side="right")
        buttons.append(b)
        b = R.button(row, "Open download page", open_page)
        b.pack(side="right", padx=6)
        buttons.append(b)
        if appupdate.can_install(info):
            b = R.button(row, "Update now", update_now, width=11, default="active")
            b.pack(side="right")
            buttons.append(b)
        rw.center(520)
        w.attributes("-topmost", True)
        w.after(80, lambda: (w.lift(), w.focus_force()))

    def _test_url(self, url):
        svc = detect_service(url) or "YouTube"
        self.show_tab(svc)
        box = {"YouTube": self.yt_urls, "Instagram": self.ig_urls, "Spotify": self.sp_urls}[svc]
        box.insert("1.0", url)
        self.add_jobs()

    # ================================================================ panels
    def _url_group(self, parent, label, var_name):
        g = R.group(parent, "URL")
        g.pack(fill="x")
        R.label(g, label).pack(anchor="w")
        row = tk.Frame(g, bg=R.GRAY)
        row.pack(fill="x", pady=(3, 0))
        box = R.text_box(row, 3)
        box.pack(side="left", fill="x", expand=True)
        side = tk.Frame(row, bg=R.GRAY)
        side.pack(side="left", padx=(6, 0), anchor="n")
        R.button(side, "Paste", lambda: self.paste(box), width=7).pack(pady=(0, 4))
        R.button(side, "Clear", lambda: box.delete("1.0", "end"), width=7).pack()
        setattr(self, var_name, box)

    def _row(self, parent, text):
        r = tk.Frame(parent, bg=R.GRAY)
        r.pack(fill="x", pady=2)
        lbl = R.label(r, text, width=11, anchor="w")
        lbl.pack(side="left")
        return r, lbl

    def _yt_panel(self, p):
        s = self.s.get("yt", {})
        self._url_group(p, "YouTube video, Short or playlist links (one per line):", "yt_urls")
        g = R.group(p, "Options")
        g.pack(fill="x", pady=(6, 0))
        r, _ = self._row(g, "Download:")
        self.yt_mode = tk.StringVar(value=s.get("mode", MODES[0]))
        for m in MODES:
            R.radio(r, m, self.yt_mode, m, self.on_yt_mode).pack(side="left", padx=(0, 14))
        r, self.yt_q_label = self._row(g, "Resolution:")
        self.yt_quality = tk.StringVar(value=s.get("quality", "Best"))
        self.yt_wanted = s.get("quality") if s.get("quality") in VIDEO_QUALITIES else "Best"  # what the user chose
        self.yt_url, self.yt_info, self.yt_checking, self.yt_token, self.yt_cache = None, None, False, 0, {}
        self.yt_q_menu = R.Dropdown(r, self.yt_quality, VIDEO_QUALITIES, width=12, command=self.on_yt_quality_pick)
        self.yt_q_menu.pack(side="left")
        R.label(r, "   File type:").pack(side="left")
        self.yt_fmt = tk.StringVar(value=s.get("fmt", "mp4"))
        self.yt_fmt_menu = R.Dropdown(r, self.yt_fmt, VIDEO_FORMATS, width=6,
                                      command=lambda v: self.yt_hint.configure(text=HINTS.get(v, "")))
        self.yt_fmt_menu.pack(side="left")
        self.yt_hint = R.label(r, "", fg=R.DARK)
        self.yt_hint.pack(side="left", padx=8)
        r, _ = self._row(g, "Extras:")
        self.yt_playlist = tk.BooleanVar(value=s.get("playlist", False))
        self.yt_subs = tk.BooleanVar(value=s.get("subs", False))
        self.yt_thumb = tk.BooleanVar(value=s.get("thumb", False))
        R.check(r, "Whole playlist", self.yt_playlist).pack(side="left", padx=(0, 12))
        R.check(r, "Subtitles", self.yt_subs).pack(side="left", padx=(0, 12))
        R.check(r, "Embed thumbnail", self.yt_thumb).pack(side="left")

    def _ig_panel(self, p):
        s = self.s.get("ig", {})
        self._url_group(p, "Instagram reel, post or carousel links (one per line):", "ig_urls")
        g = R.group(p, "Login")
        g.pack(fill="x", pady=(6, 0))
        self.ig_login_label = R.label(g, "", anchor="w")
        self.ig_login_label.pack(side="left", fill="x", expand=True)
        self.ig_logout_btn = R.button(g, "Log out", self.ig_logout)
        self.ig_logout_btn.pack(side="right")
        self.ig_login_btn = R.button(g, "Log in to Instagram...", self.ig_login)
        self.ig_login_btn.pack(side="right", padx=4)
        R.button(g, "Privacy...", self.ig_privacy).pack(side="right")
        g = R.group(p, "Options")
        g.pack(fill="x", pady=(6, 0))
        r, _ = self._row(g, "Download:")
        self.ig_mode = tk.StringVar(value=s.get("mode", "Auto"))
        for m in IG_MODES:
            R.radio(r, m, self.ig_mode, m, lambda: self.ig_hint.configure(text=IG_HINTS[self.ig_mode.get()])
                    ).pack(side="left", padx=(0, 14))
        self.ig_hint = R.label(g, IG_HINTS.get(self.ig_mode.get(), ""), fg=R.DARK, anchor="w")
        self.ig_hint.pack(fill="x")

    def _sp_panel(self, p):
        s = self.s.get("sp", {})
        self._url_group(p, "Spotify song, album or playlist links (one per line):", "sp_urls")
        g = R.group(p, "Options")
        g.pack(fill="x", pady=(6, 0))
        r, _ = self._row(g, "File type:")
        self.sp_fmt = tk.StringVar(value=s.get("fmt", "mp3"))
        self.sp_fmt_menu = R.Dropdown(r, self.sp_fmt, ["mp3", "m4a"], width=6)
        self.sp_fmt_menu.pack(side="left")
        self.sp_q_label = R.label(r, "   Bitrate:")
        self.sp_q_label.pack(side="left")
        self.sp_quality = tk.StringVar(value=s.get("quality", "320 kbps"))
        self.sp_q_menu = R.Dropdown(r, self.sp_quality, AUDIO_QUALITIES, width=9)
        self.sp_q_menu.pack(side="left")
        r, _ = self._row(g, "Extras:")
        self.sp_subfolder = tk.BooleanVar(value=s.get("subfolder", True))
        self.sp_skip = tk.BooleanVar(value=s.get("skip", True))
        R.check(r, "Albums/playlists in their own folder", self.sp_subfolder).pack(side="left", padx=(0, 12))
        R.check(r, "Skip songs I already have", self.sp_skip).pack(side="left")
        R.label(g, "Songs are found on YouTube by title, artist and length, then tagged with Spotify's\n"
                   "info and cover art. Spotify's own (DRM-protected) audio is never downloaded.",
                fg=R.DARK, justify="left", anchor="w").pack(fill="x", pady=(2, 0))

    def _hist_panel(self, p):
        g = R.group(p, "Downloaded files")
        g.pack(fill="both", expand=True)
        wrap, self.hlist = R.scrolled_listbox(g, height=10)
        wrap.pack(fill="both", expand=True)
        self.hlist.bind("<Double-Button-1>", lambda e: self.hist_open(False))
        row = tk.Frame(g, bg=R.GRAY)
        row.pack(fill="x", pady=(6, 0))
        R.button(row, "Play / Open", lambda: self.hist_open(False)).pack(side="left")
        R.button(row, "Show in folder", lambda: self.hist_open(True)).pack(side="left", padx=4)
        R.button(row, "Clear history", self.hist_clear).pack(side="right")

    # ---- themes
    def theme_picked(self):
        self.apply_theme(self.theme_var.get(), self.dark)

    def toggle_dark(self):
        self.apply_theme(self.theme_var.get(), not self.dark)

    def apply_theme(self, name, dark=False, save=True):
        name = name if name in R.THEMES else "Classic 95"
        self.theme_var.set(name)
        self.dark = bool(dark)                      # kept even on themes without one, so it comes back on 10 / 11
        R.set_theme(name, self.dark)
        R.apply_tree(self.root)
        if R.has_dark(name):
            self.dark_btn.configure(text="Light mode" if self.dark else "Dark mode")
            self.dark_btn.pack(side="right", padx=(0, 4), pady=2)
        else:
            self.dark_btn.pack_forget()
        R.apply_tree(self.dark_btn)
        self.refresh_login()
        self.refresh_queue()
        self.frame.fit()
        if save:
            self.persist()

    def _menu(self, parent):
        mb = tk.Frame(parent, bg=R.GRAY)
        mb.pack(fill="x", padx=2)
        menus = (
            ("File", [("Open downloads folder", self.open_folder), ("-", None), ("Exit", self.on_close)]),
            ("Tools", [("Show log...", self.show_log), ("Update download engines...", self.check_updates),
                       ("-", None), ("Log in to Instagram...", self.ig_login),
                       ("Log out of Instagram", self.ig_logout)]),
            ("View", [("theme", name) for name in R.THEMES]),
            ("Help", [("How to use", self.help), ("Check for RetroGrab updates...",
                                                   lambda: self.check_app_update(manual=True)),
                      ("-", None), ("About...", self.about)]),
        )
        for name, items in menus:
            m = tk.Menubutton(mb, text=name, font=R.FONT, bg=R.GRAY, activebackground=R.NAVY,
                              activeforeground=R.WHITE, relief="flat", padx=6, underline=0)
            menu = tk.Menu(m, tearoff=0, font=R.FONT, bg=R.GRAY, activebackground=R.NAVY,
                           activeforeground=R.WHITE, relief="raised", bd=2)
            for lbl, cmd in items:
                if lbl == "theme":
                    menu.add_radiobutton(label=cmd, variable=self.theme_var, value=cmd, command=self.theme_picked)
                elif lbl == "-":
                    menu.add_separator()
                else:
                    menu.add_command(label=lbl, command=cmd)
            m["menu"] = menu
            m.pack(side="left")
        self.dark_btn = R.button(mb, "Dark mode", self.toggle_dark)   # only shown on themes that have one
        tk.Frame(parent, height=2, bg=R.DARK).pack(fill="x", padx=2)

    # ================================================================ UI logic
    def show_tab(self, name):
        if name not in self.panels:
            name = "YouTube"
        self.tab = name
        self.panels[name].tkraise()
        self.tabstrip.select(name)
        self.dl_btn.configure(state="disabled" if name == "History" else "normal")

    def on_yt_mode(self):
        audio = self.yt_mode.get() == "Audio only"
        self._apply_yt_qualities()
        self.yt_fmt_menu.set_values(AUDIO_FORMATS if audio else VIDEO_FORMATS)
        self.yt_q_label.configure(text="Bitrate:" if audio else "Resolution:")
        self.yt_hint.configure(text=HINTS.get(self.yt_fmt.get(), ""))

    # ---- links go to the right tab, and the YouTube tab shows that video's real qualities
    def _watch_box(self, box):
        def changed(_e):
            if box.edit_modified():
                box.edit_modified(False)
                if self.link_job:
                    self.root.after_cancel(self.link_job)
                self.link_job = self.root.after(120, self.route_links)
        box.bind("<<Modified>>", changed)

    def route_links(self):
        self.link_job = None
        boxes = {"YouTube": self.yt_urls, "Instagram": self.ig_urls, "Spotify": self.sp_urls}
        target = None
        for svc, box in boxes.items():
            words = box.get("1.0", "end").split()
            keep = []
            for w in words:
                dest = detect_service(w)
                if dest and dest != svc:
                    other = boxes[dest]
                    other.insert("end", ("\n" if other.get("1.0", "end").strip() else "") + w)
                    target = dest
                else:
                    keep.append(w)
            if len(keep) != len(words):
                box.delete("1.0", "end")
                box.insert("1.0", "\n".join(keep))
        if target:
            self.show_tab(target)
            boxes[target].focus_set()
        self.yt_refresh()

    def yt_refresh(self, *_):
        urls = [w for w in self.yt_urls.get("1.0", "end").split() if detect_service(w) == "YouTube"]
        one = urls[0] if len(urls) == 1 else None
        if one and ("/playlist" in one or ("list=" in one and self.yt_playlist.get())):
            one = None  # every video in a playlist can differ: keep the full list
        if one == self.yt_url:
            return
        self.yt_url, self.yt_info, self.yt_checking = one, None, False
        self.yt_token += 1
        if one in self.yt_cache:
            self.yt_info = self.yt_cache[one]
        elif one:
            self.yt_checking = True
            token = self.yt_token

            def run():
                try:
                    import engine
                    self.events.put(("yt_q", (token, one, engine.video_qualities(one), None)))
                except Exception as e:
                    self.events.put(("yt_q", (token, one, None, e)))

            threading.Thread(target=run, daemon=True).start()
        self._apply_yt_qualities()

    def yt_q_result(self, token, url, info, err):
        if token != self.yt_token:
            return  # the link changed while we were checking
        self.yt_checking = False
        if info:
            self.yt_cache[url] = self.yt_info = info
        else:
            self.add_log(f"Couldn't check qualities for {url}: {err}")
            if not self.current:
                self.status.set("Couldn't check this video's qualities. Showing the full list.")
        self._apply_yt_qualities()

    def _apply_yt_qualities(self):
        if self.yt_mode.get() == "Audio only":
            self.yt_q_menu.set_values(AUDIO_QUALITIES)
        elif self.yt_checking:
            self.yt_q_menu.set_values(VIDEO_QUALITIES)
            self.yt_quality.set("Checking...")
        elif self.yt_info:
            labels = self.yt_info[0]
            best = "Best (" + labels[0].split()[0] + ")"
            self.yt_q_menu.set_values([best] + labels)
            if self.yt_wanted == "Best":
                self.yt_quality.set(best)
            else:  # the closest quality that doesn't go above the user's choice
                num = lambda q: int(q.split("p")[0])
                fits = [q for q in labels if num(q) <= num(self.yt_wanted)]
                self.yt_quality.set(fits[0] if fits else labels[-1])
        else:
            self.yt_q_menu.set_values(VIDEO_QUALITIES)
            self.yt_quality.set(self.yt_wanted)

    def on_yt_quality_pick(self, value):
        if self.yt_mode.get() != "Audio only":
            self.yt_wanted = "Best" if value.startswith("Best") else value

    def yt_quality_choice(self):
        v = self.yt_quality.get()
        if self.yt_mode.get() == "Audio only":
            return v
        return self.yt_wanted if v == "Checking..." else "Best" if v.startswith("Best") else v

    def paste(self, box):
        try:
            text = self.root.clipboard_get().strip()
        except tk.TclError:
            return
        cur = box.get("1.0", "end").strip()
        box.insert("end", ("\n" if cur else "") + text)

    def autofill_clipboard(self):
        try:
            clip = self.root.clipboard_get().strip()
        except tk.TclError:
            return
        svc = detect_service(clip) if clip.startswith(("http", "spotify:")) and "\n" not in clip else None
        if svc:
            box = {"YouTube": self.yt_urls, "Instagram": self.ig_urls, "Spotify": self.sp_urls}[svc]
            if not box.get("1.0", "end").strip():
                box.insert("1.0", clip)
            self.show_tab(svc)

    def browse(self):
        d = filedialog.askdirectory(initialdir=self.folder.get() or DEFAULT_FOLDER)
        if d:
            self.folder.set(os.path.normpath(d))

    def open_folder(self):
        path = self.folder.get().strip() or DEFAULT_FOLDER
        os.makedirs(path, exist_ok=True)
        os.startfile(path)

    def persist(self):
        self.s.update({
            "folder": self.folder.get(), "tab": self.tab, "theme": self.theme_var.get(), "dark": self.dark,
            "yt": {"mode": self.yt_mode.get(), "quality": self.yt_quality_choice(), "fmt": self.yt_fmt.get(),
                   "playlist": self.yt_playlist.get(), "subs": self.yt_subs.get(), "thumb": self.yt_thumb.get()},
            "ig": {"mode": self.ig_mode.get()},
            "sp": {"fmt": self.sp_fmt.get(), "quality": self.sp_quality.get(),
                   "subfolder": self.sp_subfolder.get(), "skip": self.sp_skip.get()},
        })
        save_json(SETTINGS_FILE, self.s)

    # ================================================================ log
    def add_log(self, line):
        self.log_lines.append(line)
        try:  # local log file for troubleshooting - stays in data\, never uploaded anywhere
            if os.path.isfile(LOG_FILE) and os.path.getsize(LOG_FILE) > 2_000_000:
                os.replace(LOG_FILE, LOG_FILE + ".old")
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass
        if len(self.log_lines) > 3000:
            del self.log_lines[:500]
        if self.log_win and self.log_win.winfo_exists():
            self.log_text.configure(state="normal")
            self.log_text.insert("end", line + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")

    def show_log(self):
        if self.log_win and self.log_win.winfo_exists():
            self.log_win.lift()
            return
        w = tk.Toplevel(self.root)
        self.log_win = w
        rw = R.RetroWindow(w, "Log", w.destroy, minimizable=False)
        body = tk.Frame(rw.outer, bg=R.GRAY, padx=8, pady=8)
        body.pack(fill="both", expand=True)
        wrap = tk.Frame(body, bg=R.GRAY, relief="sunken", bd=2)
        wrap.pack(fill="both", expand=True)
        self.log_text = tk.Text(wrap, width=90, height=24, font=R.MONO, bg=R.BLACK, fg=R.GRAY, bd=0,
                                wrap="char", highlightthickness=0)
        R.scrollbar(wrap, self.log_text)
        self.log_text.pack(side="left", fill="both", expand=True)
        self.log_text.insert("end", "\n".join(self.log_lines) + ("\n" if self.log_lines else ""))
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        row = tk.Frame(body, bg=R.GRAY)
        row.pack(fill="x", pady=(6, 0))
        R.button(row, "Close", w.destroy, width=9).pack(side="right")
        R.button(row, "Copy all", lambda: (self.root.clipboard_clear(),
                                           self.root.clipboard_append("\n".join(self.log_lines)))).pack(side="left")
        rw.center(600)

    # ================================================================ queue
    def add_jobs(self):
        if self.tab == "History":
            return
        box = {"YouTube": self.yt_urls, "Instagram": self.ig_urls, "Spotify": self.sp_urls}[self.tab]
        urls = [u.strip() for u in box.get("1.0", "end").split() if u.strip()]
        if not urls:
            messagebox.showwarning(APP_NAME, "Paste at least one link first.")
            return
        folder = self.folder.get().strip() or DEFAULT_FOLDER
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as e:
            messagebox.showerror(APP_NAME, f"Can't use that folder:\n{e}")
            return
        self.persist()
        unknown = []
        for url in urls:
            svc = detect_service(url) or (self.tab if url.startswith("http") else None)
            if not svc:
                unknown.append(url)
                continue
            if svc == "Instagram":
                opts = {"ig_mode": self.ig_mode.get()}
            elif svc == "Spotify":
                opts = {"fmt": self.sp_fmt.get(), "quality": self.sp_quality.get(),
                        "subfolder": self.sp_subfolder.get(), "skip_existing": self.sp_skip.get()}
            else:
                q = self.yt_quality_choice()
                limit = self.yt_info[1].get(q) if self.yt_info and url == self.yt_url else None
                opts = {"mode": self.yt_mode.get(), "quality": q, "height_limit": limit, "fmt": self.yt_fmt.get(),
                        "playlist": self.yt_playlist.get(), "subs": self.yt_subs.get(),
                        "thumb": self.yt_thumb.get()}
            opts["folder"] = folder
            self.jobs.append({"id": next(self.ids), "service": svc, "url": url, "opts": opts,
                              "status": "Waiting", "note": ""})
        box.delete("1.0", "end")
        if unknown:
            messagebox.showwarning(APP_NAME, "These don't look like links and were skipped:\n" + "\n".join(unknown))
        self.refresh_queue()
        self.start_worker()

    def refresh_queue(self):
        sel = self.qlist.curselection()
        self.qlist.delete(0, "end")
        for j in self.jobs:
            name = j.get("name") or j["url"]
            note = f"  - {j['note']}" if j["note"] else ""
            self.qlist.insert("end", f"{j['status']:<11} {j['service']:<10} {name}{note}")
            color = {"Done": R.T["ok"], "Failed": R.T["err"], "Cancelled": R.T["muted"]}.get(j["status"])
            if color:
                self.qlist.itemconfigure("end", foreground=color)
        for i in sel:
            if i < self.qlist.size():
                self.qlist.selection_set(i)

    def remove_job(self):
        sel = self.qlist.curselection()
        if not sel:
            return
        job = self.jobs[sel[0]]
        if job is self.current:
            if messagebox.askyesno(APP_NAME, "This one is downloading now. Cancel it?"):
                self.cancel_current()
            return
        self.jobs.remove(job)
        self.refresh_queue()

    def clear_done(self):
        self.jobs = [j for j in self.jobs if j["status"] in ("Waiting", "Downloading")]
        self.refresh_queue()

    def cancel_current(self):
        if self.current:
            self.cancel_event.set()
            self.status.set("Cancelling...")

    def start_worker(self):
        if self.worker and self.worker.is_alive():
            return
        self.worker = threading.Thread(target=self.work, daemon=True)
        self.worker.start()

    def work(self):
        import engine
        rep = Reporter(self.events, self.cancel_event)
        while True:
            job = next((j for j in self.jobs if j["status"] == "Waiting"), None)
            if not job:
                self.events.put(("idle", None))
                return
            self.cancel_event.clear()
            self.current = job
            job["status"] = "Downloading"
            self.events.put(("start", job))
            rep.log(f"===== {job['service']}: {job['url']}")
            try:
                engine.RUNNERS[job["service"]](job, rep, self.cancel_event)
                job["status"], job["note"] = "Done", ""
            except engine.Cancelled:
                job["status"], job["note"] = "Cancelled", ""
            except engine.JobError as e:
                job["status"], job["note"] = "Failed", str(e)[:200]
            except Exception as e:  # unexpected - keep the app alive
                job["status"], job["note"] = "Failed", f"{type(e).__name__}: {e}"[:200]
                import traceback
                rep.log(traceback.format_exc())
            rep.log(f"===== {job['status']} {job['note']}")
            self.current = None
            self.events.put(("end", job))

    def poll(self):
        last_progress = None
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == "progress":
                    last_progress = data
                elif kind == "log":
                    self.add_log(data)
                elif kind == "status":
                    self.status.set(data)
                elif kind == "title":
                    self.now_title.set(data[:95])
                    if self.current:
                        self.current["name"] = data[:80]
                elif kind == "ask_lang":
                    self.root.after(0, lambda d=data: self.language_dialog(*d))
                elif kind == "yt_q":
                    self.yt_q_result(*data)
                elif kind == "saved":
                    self.add_history(*data)
                elif kind == "start":
                    self.cancel_btn.configure(state="normal")
                    self.bar.set(0)
                    self.now_title.set(data["url"][:95])
                    self.detail.set("Starting...")
                    self.status.set(f"Working on {data['service']} link...")
                    self.refresh_queue()
                elif kind == "end":
                    self.refresh_queue()
                    self.speed.set("")
                    if data["status"] == "Done":
                        self.bar.set(100)
                        self.detail.set("Finished.")
                    else:
                        self.bar.set(0)
                        self.detail.set(f"{data['status']}. {data['note']}"[:120])
                elif kind == "idle":
                    self.cancel_btn.configure(state="disabled")
                    done = sum(j["status"] == "Done" for j in self.jobs)
                    failed = sum(j["status"] == "Failed" for j in self.jobs)
                    self.status.set(f"All done.  {done} finished" + (f", {failed} failed" if failed else ""))
                    self.now_title.set("Nothing downloading.")
        except queue.Empty:
            pass
        if last_progress:
            pct, detail, speed = last_progress
            self.bar.set(pct)
            self.detail.set(detail)
            self.speed.set(speed)
        self.root.after(80, self.poll)

    # ================================================================ language choice
    def language_dialog(self, label, langs, default, multi, done, box):
        w = tk.Toplevel(self.root)
        closed = []

        def finish(answer):
            if closed:
                return
            closed.append(1)
            box["answer"] = answer
            done.set()
            try:
                w.grab_release()
            except tk.TclError:
                pass
            w.destroy()

        rw = R.RetroWindow(w, "Choose language", lambda: finish(None), minimizable=False)
        body = tk.Frame(rw.outer, bg=R.GRAY, padx=14, pady=10)
        body.pack(fill="both", expand=True)
        R.label(body, "This song is available in more than one language:", anchor="w").pack(fill="x")
        R.label(body, label[:110], font=R.FONT_B, wraplength=440, justify="left", anchor="w").pack(
            fill="x", pady=(4, 8))
        var = tk.StringVar(value=default if default in langs else langs[0])
        g = R.group(body, "Download it in")
        g.pack(fill="x")
        for lang in langs:
            text = lang.title() + ("      ← as listed on Spotify" if lang == default else "")
            R.radio(g, text, var, lang).pack(anchor="w")
        keep = tk.BooleanVar(value=True)
        if multi:
            R.check(body, "Use this language for the rest of this album / playlist", keep).pack(anchor="w",
                                                                                                pady=(8, 0))
        row = tk.Frame(body, bg=R.GRAY)
        row.pack(fill="x", pady=(12, 0))
        R.button(row, "Skip song", lambda: finish(None), width=10).pack(side="right")
        R.button(row, "Download", lambda: finish((var.get(), multi and keep.get())), width=10,
                 default="active").pack(side="right", padx=6)
        w.bind("<Return>", lambda e: finish((var.get(), multi and keep.get())))
        w.bind("<Escape>", lambda e: finish(None))
        rw.center(460)
        w.attributes("-topmost", True)

        def grab():
            try:
                w.lift()
                w.focus_force()
                w.grab_set()
            except tk.TclError:
                pass

        w.after(80, grab)

        def watch_cancel():  # the job was cancelled while the question was open
            if closed:
                return
            if self.cancel_event.is_set():
                finish(None)
            else:
                w.after(300, watch_cancel)

        watch_cancel()
        self.status.set("Waiting for you to choose a language...")

    # ================================================================ history
    def add_history(self, path, service):
        if not path:
            return
        path = os.path.abspath(path)
        self.history = [h for h in self.history if h["path"] != path]
        self.history.insert(0, {"time": time.strftime("%Y-%m-%d %H:%M"), "service": service, "path": path})
        del self.history[1000:]
        save_json(HISTORY_FILE, self.history)
        self.refresh_history()

    def refresh_history(self):
        self.hlist.delete(0, "end")
        for h in self.history:
            self.hlist.insert("end", f"{h['time']}  {h['service']:<10} {os.path.basename(h['path'])}")

    def hist_open(self, folder):
        sel = self.hlist.curselection()
        if not sel:
            return
        path = self.history[sel[0]]["path"]
        if not os.path.exists(path):
            messagebox.showinfo(APP_NAME, "That file has been moved or deleted.")
            return
        if folder:
            subprocess.Popen(["explorer", "/select,", path])
        else:
            os.startfile(path)

    def hist_clear(self):
        if messagebox.askyesno(APP_NAME, "Clear the download history? (Files are not deleted.)"):
            self.history = []
            save_json(HISTORY_FILE, self.history)
            self.refresh_history()

    # ================================================================ instagram login
    def refresh_login(self):
        if has_instagram_login():
            self.ig_login_label.configure(text="✔ Logged in. Downloads use your Instagram account.",
                                          fg=R.T["ok"])
            self.ig_logout_btn.configure(state="normal")
        else:
            self.ig_login_label.configure(text="Not logged in. Most Instagram links need a login.", fg=R.T["err"])
            self.ig_logout_btn.configure(state="disabled")

    def ig_privacy(self):
        messagebox.showinfo(APP_NAME + " - Instagram privacy", IG_PRIVACY + (
            "\n\nStatus: " + ("logged in. The encrypted session is in:\n" + IG_SESSION
                              if has_instagram_login() else "not logged in. Nothing is stored.")))

    def ig_login(self):
        self.show_tab("Instagram")
        if not messagebox.askokcancel(APP_NAME + " - Log in to Instagram", IG_PRIVACY +
                                      "\n\nOpen Instagram's login page now?"):
            return
        cmd =[sys.executable, "--ig-login"] if FROZEN else [sys.executable, os.path.abspath(sys.argv[0]),
                                                              "--ig-login"]
        self.ig_login_btn.configure(state="disabled")
        self.ig_login_label.configure(text="Log in using the window that just opened...", fg=R.T["fg"])

        def wait():
            try:
                code = subprocess.run(cmd, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).returncode
            except Exception as e:
                code = -1
                self.events.put(("log", f"Login window failed: {e}"))
            self.root.after(0, lambda: self._login_done(code))

        threading.Thread(target=wait, daemon=True).start()

    def _login_done(self, code):
        self.ig_login_btn.configure(state="normal")
        self.refresh_login()
        if code != 0 and not has_instagram_login():
            messagebox.showinfo(APP_NAME, "Login wasn't completed. You can try again any time.\n\n"
                                          "(The login window needs Microsoft Edge WebView2, which comes with "
                                          "Windows 10 and 11.)")

    def ig_logout(self):
        if not messagebox.askyesno(APP_NAME, "Log out of Instagram in RetroGrab?\n\n"
                                             "This deletes the saved session from this PC."):
            return
        delete_instagram_session()
        self.refresh_login()
        messagebox.showinfo(APP_NAME, "Logged out. RetroGrab no longer has any Instagram data on this PC.\n\n"
                                      "Extra safety: in Instagram, Settings > Accounts Center > Password and "
                                      "security > Where you're logged in, lets you end that session too.")

    # ================================================================ misc
    def check_updates(self):
        if self.current:
            messagebox.showinfo(APP_NAME, "Wait for the current download to finish first.")
            return
        import updater
        self.status.set("Checking for updates...")
        self.show_log()

        def run():
            try:
                updated = updater.update(self.versions, log=lambda m: self.events.put(("log", m)))
                msg = ("Updated: " + ", ".join(updated) + "\n\nRestart RetroGrab to use the new version."
                       if updated else "Everything is already up to date.")
            except Exception as e:
                msg = f"Update failed:\n{e}"
            self.root.after(0, lambda: (self.status.set("Ready"), messagebox.showinfo(APP_NAME, msg)))

        threading.Thread(target=run, daemon=True).start()

    def help(self):
        messagebox.showinfo(APP_NAME, (
            "1. Copy a link from YouTube, Instagram or Spotify.\n"
            "2. Pick the tab (it switches by itself when you open the app with a link copied).\n"
            "3. Choose your options, then click Download (or press Ctrl+Enter).\n\n"
            "You can paste many links at once - one per line. They wait in the Queue and download one by one.\n\n"
            "Instagram: click 'Log in to Instagram...' once. Your login stays saved on this PC.\n\n"
            "If a site stops working, use Tools > Check for updates."))

    def about(self):
        v = self.versions
        messagebox.showinfo(APP_NAME, (
            f"{APP_NAME} {APP_VERSION}\nA retro downloader for YouTube, Instagram and Spotify.\n\n"
            f"Engines:\n  yt-dlp {v.get('yt-dlp')}\n  yt-dlp-ejs {v.get('yt-dlp-ejs')}\n"
            f"  gallery-dl {v.get('gallery-dl')}\n\n"
            "Only download things you have the right to - your own content, or with permission."))

    def on_close(self):
        if self.current and not messagebox.askyesno(APP_NAME, "A download is running. Cancel it and exit?"):
            return
        self.cancel_event.set()
        self.persist()
        self.root.destroy()
