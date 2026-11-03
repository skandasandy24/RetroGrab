"""yt-dlp Downloader - a retro Windows 95 style front-end for yt-dlp."""
import ctypes
import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

APP_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")
DEFAULT_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
PYTHON = sys.executable.replace("pythonw.exe", "python.exe")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# ---- Win95 palette ----
GRAY = "#c0c0c0"
DARK = "#808080"
WHITE = "#ffffff"
NAVY = "#000080"
TITLE_GRAD_END = "#1084d0"
FONT = ("Microsoft Sans Serif", 9)
FONT_B = ("Microsoft Sans Serif", 9, "bold")
MONO = ("Fixedsys", 9)

MODES = ["Video + Audio", "Video only", "Audio only"]
VIDEO_FORMATS = ["mp4", "mkv", "webm"]
AUDIO_FORMATS = ["mp3", "m4a", "opus", "wav", "flac"]
VIDEO_QUALITIES = ["Best", "2160p (4K)", "1440p", "1080p", "720p", "480p", "360p", "240p", "144p"]
AUDIO_QUALITIES = ["Best", "320 kbps", "256 kbps", "192 kbps", "128 kbps", "96 kbps"]

SEP = "␟"  # unlikely to appear in output
PROGRESS_TEMPLATE = SEP.join([
    "download:PROG",
    "%(progress._percent_str)s",
    "%(progress._speed_str)s",
    "%(progress._eta_str)s",
    "%(progress._total_bytes_str,progress._total_bytes_estimate_str)s",
    "%(info.title)s",
])


def load_settings():
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(data):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def build_format_args(mode, fmt, quality):
    """Translate the UI choices into yt-dlp arguments."""
    if mode == "Audio only":
        args = ["-f", "ba/b", "-x", "--audio-format", fmt]
        if quality == "Best" or fmt in ("wav", "flac"):
            args += ["--audio-quality", "0"]
        else:
            args += ["--audio-quality", quality.split()[0] + "K"]
        return args

    h = "" if quality == "Best" else f"[height<={quality.split('p')[0]}]"
    sort = {"mp4": "ext:mp4:m4a", "webm": "ext:webm:webm", "mkv": "res"}[fmt]
    if mode == "Video only":
        return ["-f", f"bv{h}/bv*{h}", "-S", sort, "--remux-video", fmt]
    return ["-f", f"bv*{h}+ba/b{h}/bv*+ba/b", "-S", sort, "--merge-output-format", fmt]


# ---------------- retro widgets ----------------
def btn(parent, text, cmd, width=None, **kw):
    b = tk.Button(parent, text=text, command=cmd, font=FONT, bg=GRAY, activebackground=GRAY,
                  relief="raised", bd=2, padx=8, pady=1, highlightthickness=0, **kw)
    if width:
        b.configure(width=width)
    return b


def group(parent, title):
    return tk.LabelFrame(parent, text=f" {title} ", font=FONT, bg=GRAY, relief="groove",
                         bd=2, padx=8, pady=6)


def sunken_entry(parent, var):
    return tk.Entry(parent, textvariable=var, font=FONT, bg=WHITE, relief="sunken", bd=2,
                    highlightthickness=0)


def dropdown(parent, var, values, width=12, command=None):
    om = tk.OptionMenu(parent, var, *values, command=command)
    om.configure(font=FONT, bg=GRAY, activebackground=GRAY, relief="raised", bd=2,
                 highlightthickness=0, width=width, anchor="w", indicatoron=True)
    om["menu"].configure(font=FONT, bg=WHITE, activebackground=NAVY, activeforeground=WHITE,
                         relief="solid", bd=1)
    return om


def set_dropdown(om, var, values, command=None):
    menu = om["menu"]
    menu.delete(0, "end")
    for v in values:
        menu.add_command(label=v, command=lambda v=v: (var.set(v), command and command(v)))
    if var.get() not in values:
        var.set(values[0])


class BlockProgress(tk.Canvas):
    """Classic segmented navy-block progress bar."""

    def __init__(self, parent, **kw):
        super().__init__(parent, height=22, bg=WHITE, highlightthickness=0, relief="sunken", bd=2, **kw)
        self.value = 0
        self.bind("<Configure>", lambda e: self.draw())

    def set(self, pct):
        self.value = max(0.0, min(100.0, pct))
        self.draw()

    def draw(self):
        self.delete("all")
        w = self.winfo_width() - 8
        block, gap = 9, 2
        n_total = max(1, w // (block + gap))
        n_fill = round(n_total * self.value / 100)
        for i in range(n_fill):
            x = 4 + i * (block + gap)
            self.create_rectangle(x, 4, x + block, self.winfo_height() - 5, fill=NAVY, outline=NAVY)


# ---------------- application ----------------
class App:
    def __init__(self, root):
        self.root = root
        self.proc = None
        self._cancelled = False
        self._drag = (0, 0)
        s = load_settings()

        root.title("yt-dlp Downloader")
        root.configure(bg=GRAY)
        root.overrideredirect(True)

        outer = tk.Frame(root, bg=GRAY, relief="raised", bd=3)
        outer.pack(fill="both", expand=True)
        self._title_bar(outer)
        self._menu_bar(outer)

        body = tk.Frame(outer, bg=GRAY, padx=10, pady=6)
        body.pack(fill="both", expand=True)

        # ---- URL ----
        g = group(body, "URL")
        g.pack(fill="x", pady=4)
        tk.Label(g, text="Paste one or more links (one per line):", font=FONT, bg=GRAY).pack(anchor="w")
        row = tk.Frame(g, bg=GRAY)
        row.pack(fill="x", pady=(3, 0))
        self.url_box = tk.Text(row, height=3, font=FONT, bg=WHITE, relief="sunken", bd=2,
                               wrap="word", highlightthickness=0)
        self.url_box.pack(side="left", fill="x", expand=True)
        side = tk.Frame(row, bg=GRAY)
        side.pack(side="left", padx=(6, 0), anchor="n")
        btn(side, "Paste", self.paste, width=7).pack(pady=(0, 4))
        btn(side, "Clear", lambda: self.url_box.delete("1.0", "end"), width=7).pack()

        # ---- Options (mode + quality) ----
        g = group(body, "Options")
        g.pack(fill="x", pady=4)
        self.mode = tk.StringVar(value=s.get("mode", MODES[0]))
        mrow = tk.Frame(g, bg=GRAY)
        mrow.pack(fill="x")
        tk.Label(mrow, text="Download:", font=FONT, bg=GRAY, width=10, anchor="w").pack(side="left")
        for m in MODES:
            tk.Radiobutton(mrow, text=m, value=m, variable=self.mode, font=FONT, bg=GRAY,
                           activebackground=GRAY, selectcolor=WHITE, highlightthickness=0,
                           command=self.on_mode_change).pack(side="left", padx=(0, 14))
        qrow = tk.Frame(g, bg=GRAY)
        qrow.pack(fill="x", pady=(6, 0))
        self.quality_label = tk.Label(qrow, text="Quality:", font=FONT, bg=GRAY, width=10, anchor="w")
        self.quality_label.pack(side="left")
        self.quality = tk.StringVar(value=s.get("quality", "Best"))
        self.quality_menu = dropdown(qrow, self.quality, VIDEO_QUALITIES, width=12)
        self.quality_menu.pack(side="left")
        xrow = tk.Frame(g, bg=GRAY)
        xrow.pack(fill="x", pady=(6, 0))
        tk.Label(xrow, text="Extras:", font=FONT, bg=GRAY, width=10, anchor="w").pack(side="left")
        self.playlist = tk.BooleanVar(value=s.get("playlist", False))
        self.subs = tk.BooleanVar(value=s.get("subs", False))
        self.thumb = tk.BooleanVar(value=s.get("thumb", False))
        for text, var in (("Whole playlist", self.playlist), ("Subtitles", self.subs),
                          ("Embed thumbnail", self.thumb)):
            tk.Checkbutton(xrow, text=text, variable=var, font=FONT, bg=GRAY, activebackground=GRAY,
                           selectcolor=WHITE, highlightthickness=0).pack(side="left", padx=(0, 14))

        # ---- Format ----
        g = group(body, "Format")
        g.pack(fill="x", pady=4)
        frow = tk.Frame(g, bg=GRAY)
        frow.pack(fill="x")
        tk.Label(frow, text="File type:", font=FONT, bg=GRAY, width=10, anchor="w").pack(side="left")
        self.fmt = tk.StringVar(value=s.get("fmt", "mp4"))
        self.fmt_menu = dropdown(frow, self.fmt, VIDEO_FORMATS, width=8)
        self.fmt_menu.pack(side="left")
        self.fmt_hint = tk.Label(frow, text="", font=FONT, bg=GRAY, fg=DARK)
        self.fmt_hint.pack(side="left", padx=10)

        # ---- Path ----
        g = group(body, "Save to")
        g.pack(fill="x", pady=4)
        prow = tk.Frame(g, bg=GRAY)
        prow.pack(fill="x")
        self.folder = tk.StringVar(value=s.get("folder", DEFAULT_DIR))
        sunken_entry(prow, self.folder).pack(side="left", fill="x", expand=True, ipady=2)
        btn(prow, "Browse...", self.browse).pack(side="left", padx=(6, 0))
        btn(prow, "Open", self.open_folder).pack(side="left", padx=(4, 0))

        # ---- Progress ----
        g = group(body, "Progress")
        g.pack(fill="both", expand=True, pady=4)
        self.now_title = tk.StringVar(value="Nothing downloading.")
        tk.Label(g, textvariable=self.now_title, font=FONT, bg=GRAY, anchor="w").pack(fill="x")
        self.bar = BlockProgress(g)
        self.bar.pack(fill="x", pady=4)
        self.detail = tk.StringVar(value="0%")
        tk.Label(g, textvariable=self.detail, font=FONT, bg=GRAY, anchor="w").pack(fill="x")
        logwrap = tk.Frame(g, bg=GRAY, relief="sunken", bd=2)
        logwrap.pack(fill="both", expand=True, pady=(4, 0))
        self.log = tk.Text(logwrap, height=4, font=MONO, bg="#000000", fg="#c0c0c0", bd=0,
                           state="disabled", wrap="char", highlightthickness=0)
        sb = tk.Scrollbar(logwrap, command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log.pack(side="left", fill="both", expand=True)

        # ---- Buttons ----
        brow = tk.Frame(body, bg=GRAY)
        brow.pack(fill="x", pady=(6, 2))
        self.dl_btn = btn(brow, "Download", self.start, width=11, default="active")
        self.dl_btn.pack(side="right")
        self.cancel_btn = btn(brow, "Cancel", self.cancel, width=11, state="disabled")
        self.cancel_btn.pack(side="right", padx=6)
        btn(brow, "Update yt-dlp", self.update_ytdlp).pack(side="left")

        # ---- Status bar ----
        sbar = tk.Frame(outer, bg=GRAY)
        sbar.pack(fill="x", side="bottom", padx=2, pady=2)
        self.status = tk.StringVar(value="Ready")
        tk.Label(sbar, textvariable=self.status, font=FONT, bg=GRAY, relief="sunken", bd=1,
                 anchor="w", padx=4).pack(side="left", fill="x", expand=True)
        self.speed = tk.StringVar(value="")
        tk.Label(sbar, textvariable=self.speed, font=FONT, bg=GRAY, relief="sunken", bd=1,
                 width=22, anchor="w", padx=4).pack(side="left", padx=(2, 0))

        self.on_mode_change(initial=True)
        root.update_idletasks()
        w = max(root.winfo_reqwidth(), int(600 * root.winfo_fpixels("1i") / 96))
        h = root.winfo_reqheight()
        root.geometry(f"{w}x{h}+{(root.winfo_screenwidth() - w) // 2}+{max(0, (root.winfo_screenheight() - h) // 2 - 20)}")
        root.bind("<Control-Return>", lambda e: self.start())
        root.bind("<Escape>", lambda e: self.on_close())
        root.after(10, self._show_in_taskbar)

        try:
            clip = root.clipboard_get().strip()
            if clip.startswith("http"):
                self.url_box.insert("1.0", clip)
        except tk.TclError:
            pass

    # ---------- custom Win95 title bar ----------
    def _title_bar(self, parent):
        bar = tk.Canvas(parent, height=22, highlightthickness=0, bg=NAVY)
        bar.pack(fill="x", padx=1, pady=1)

        def paint(_=None):
            bar.delete("grad")
            w = bar.winfo_width()
            r1, g1, b1 = 0x00, 0x00, 0x80
            r2, g2, b2 = 0x10, 0x84, 0xd0
            steps = 60
            for i in range(steps):
                t = i / (steps - 1)
                c = f"#{int(r1 + (r2 - r1) * t):02x}{int(g1 + (g2 - g1) * t):02x}{int(b1 + (b2 - b1) * t):02x}"
                bar.create_rectangle(w * i / steps, 0, w * (i + 1) / steps + 1, 22, fill=c, outline=c, tags="grad")
            bar.tag_lower("grad")

        bar.create_rectangle(5, 5, 17, 17, fill="#ffff00", outline="#000000")
        bar.create_polygon(8, 8, 8, 14, 14, 11, fill="#ff0000", outline="#000000")
        bar.create_text(23, 11, text="yt-dlp Downloader", anchor="w", fill=WHITE, font=FONT_B)

        btns = tk.Frame(bar, bg=GRAY)
        bar.bind("<Configure>", lambda e: (paint(), bar.coords(win, e.width - 3, 3)))
        win = bar.create_window(0, 3, window=btns, anchor="ne")
        for sym, cmd in (("_", self.minimize), ("□", None), ("✕", self.on_close)):
            b = tk.Button(btns, text=sym, command=cmd, font=("Microsoft Sans Serif", 7, "bold"),
                          bg=GRAY, activebackground=GRAY, relief="raised", bd=2, width=2, height=1,
                          padx=0, pady=0, highlightthickness=0)
            if cmd is None:
                b.configure(state="disabled")
            b.pack(side="left", padx=(0 if sym != "✕" else 2, 0))

        for w in (bar,):
            w.bind("<ButtonPress-1>", self._start_drag)
            w.bind("<B1-Motion>", self._do_drag)

    def _menu_bar(self, parent):
        mb = tk.Frame(parent, bg=GRAY)
        mb.pack(fill="x", padx=2)
        for name, items in (
            ("File", [("Open download folder", self.open_folder), ("-", None), ("Exit", self.on_close)]),
            ("Tools", [("Update yt-dlp", self.update_ytdlp), ("Clear log", self.clear_log)]),
            ("Help", [("About...", self.about)]),
        ):
            m = tk.Menubutton(mb, text=name, font=FONT, bg=GRAY, activebackground=NAVY,
                              activeforeground=WHITE, relief="flat", padx=6, underline=0)
            menu = tk.Menu(m, tearoff=0, font=FONT, bg=GRAY, activebackground=NAVY,
                           activeforeground=WHITE, relief="raised", bd=2)
            for label, cmd in items:
                menu.add_separator() if label == "-" else menu.add_command(label=label, command=cmd)
            m["menu"] = menu
            m.pack(side="left")
        tk.Frame(parent, height=2, bg=DARK).pack(fill="x", padx=2)

    def _start_drag(self, e):
        self._drag = (e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y())

    def _do_drag(self, e):
        self.root.geometry(f"+{e.x_root - self._drag[0]}+{e.y_root - self._drag[1]}")

    def _hwnd(self):
        return ctypes.windll.user32.GetParent(self.root.winfo_id())

    def _show_in_taskbar(self):
        try:
            GWL_EXSTYLE, WS_EX_APPWINDOW, WS_EX_TOOLWINDOW = -20, 0x40000, 0x80
            hwnd = self._hwnd()
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW)
            self.root.withdraw()
            self.root.after(10, self.root.deiconify)
        except Exception:
            pass

    def minimize(self):
        try:
            ctypes.windll.user32.ShowWindow(self._hwnd(), 6)  # SW_MINIMIZE
        except Exception:
            pass

    # ---------- UI logic ----------
    def on_mode_change(self, initial=False):
        audio = self.mode.get() == "Audio only"
        set_dropdown(self.quality_menu, self.quality, AUDIO_QUALITIES if audio else VIDEO_QUALITIES)
        set_dropdown(self.fmt_menu, self.fmt, AUDIO_FORMATS if audio else VIDEO_FORMATS,
                     command=lambda v: self.update_hint())
        self.quality_label.configure(text="Bitrate:" if audio else "Resolution:")
        self.update_hint()

    def update_hint(self):
        hints = {"mp4": "Plays everywhere", "mkv": "Any codec, best quality", "webm": "Web format (VP9/AV1)",
                 "mp3": "Plays everywhere", "m4a": "AAC, small & good", "opus": "Best quality per size",
                 "wav": "Uncompressed (large)", "flac": "Lossless (large)"}
        self.fmt_hint.configure(text=hints.get(self.fmt.get(), ""))

    def paste(self):
        try:
            text = self.root.clipboard_get().strip()
        except tk.TclError:
            return
        current = self.url_box.get("1.0", "end").strip()
        self.url_box.insert("end", ("\n" if current else "") + text)

    def browse(self):
        d = filedialog.askdirectory(initialdir=self.folder.get() or DEFAULT_DIR)
        if d:
            self.folder.set(os.path.normpath(d))

    def open_folder(self):
        path = self.folder.get()
        if os.path.isdir(path):
            os.startfile(path)

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def about(self):
        messagebox.showinfo("About", "yt-dlp Downloader\nA retro front-end for yt-dlp.\n\nCtrl+Enter = Download\nEsc = Exit")

    def write_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def ui(self, fn, *args, **kw):
        self.root.after(0, lambda: fn(*args, **kw))

    def set_busy(self, busy):
        self.dl_btn.configure(state="disabled" if busy else "normal")
        self.cancel_btn.configure(state="normal" if busy else "disabled")

    def persist(self):
        save_settings({"mode": self.mode.get(), "quality": self.quality.get(), "fmt": self.fmt.get(),
                       "folder": self.folder.get(), "playlist": self.playlist.get(),
                       "subs": self.subs.get(), "thumb": self.thumb.get()})

    # ---------- running yt-dlp ----------
    def start(self):
        if self.proc:
            return
        urls = [u.strip() for u in self.url_box.get("1.0", "end").split() if u.strip()]
        if not urls:
            messagebox.showwarning("yt-dlp Downloader", "Please paste at least one URL.")
            return
        folder = self.folder.get().strip() or DEFAULT_DIR
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as e:
            messagebox.showerror("yt-dlp Downloader", f"Can't use that folder:\n{e}")
            return
        self.persist()

        cmd = [PYTHON, "-m", "yt_dlp", "--newline", "--no-colors", "--js-runtimes", "node",
               "--progress-template", PROGRESS_TEMPLATE,
               "-P", folder, "-o", "%(title)s [%(id)s].%(ext)s"]
        cmd += build_format_args(self.mode.get(), self.fmt.get(), self.quality.get())
        cmd += ["--yes-playlist"] if self.playlist.get() else ["--no-playlist"]
        if self.subs.get():
            cmd += ["--write-subs", "--sub-langs", "en.*", "--embed-subs"]
        if self.thumb.get():
            cmd += ["--embed-thumbnail"]
        cmd += ["--"] + urls

        self.bar.set(0)
        self.detail.set("0%")
        self.now_title.set("Connecting...")
        self.status.set("Starting download...")
        self.write_log(f"> {self.mode.get()} | {self.quality.get()} | {self.fmt.get()}")
        self.set_busy(True)
        threading.Thread(target=self.run, args=(cmd, True), daemon=True).start()

    def handle_line(self, line):
        if line.startswith("PROG" + SEP):
            parts = line.split(SEP, 5)
            if len(parts) == 6:
                _, pct, speed, eta, total, title = (p.strip() for p in parts)
                try:
                    self.bar.set(float(pct.rstrip("%")))
                except ValueError:
                    pass
                self.now_title.set(title[:80])
                self.detail.set(f"{pct} of {total}    ETA {eta}")
                self.speed.set(f"Speed: {speed}")
                self.status.set("Downloading...")
            return
        if line.startswith("[Merger]") or line.startswith("[ExtractAudio]") or line.startswith("[VideoRemuxer]"):
            self.status.set("Processing with ffmpeg...")
        self.write_log(line)

    def run(self, cmd, is_download):
        try:
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                         encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
            for line in self.proc.stdout:
                line = line.rstrip()
                if line:
                    self.ui(self.handle_line, line)
            code = self.proc.wait()
            if self._cancelled:
                self.ui(self.status.set, "Cancelled.")
                self.ui(self.now_title.set, "Download cancelled.")
            elif code == 0:
                self.ui(self.status.set, "Done!" if is_download else "yt-dlp updated.")
                if is_download:
                    self.ui(self.bar.set, 100)
                    self.ui(self.now_title.set, "Download complete.")
                    self.ui(self.detail.set, "100%")
            else:
                self.ui(self.status.set, f"Error (code {code}) - see log.")
        except Exception as e:
            self.ui(self.write_log, f"ERROR: {e}")
            self.ui(self.status.set, "Error.")
        finally:
            self.proc = None
            self._cancelled = False
            self.ui(self.speed.set, "")
            self.ui(self.set_busy, False)

    def cancel(self):
        if self.proc:
            self._cancelled = True
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.proc.pid)],
                           capture_output=True, creationflags=NO_WINDOW)

    def update_ytdlp(self):
        if self.proc:
            return
        self.write_log("> Updating yt-dlp...")
        self.status.set("Updating yt-dlp...")
        self.set_busy(True)
        cmd = [PYTHON, "-m", "pip", "install", "-U", "yt-dlp[default]"]
        threading.Thread(target=self.run, args=(cmd, False), daemon=True).start()

    def on_close(self):
        if self.proc and not messagebox.askyesno("yt-dlp Downloader", "A download is running. Cancel it and exit?"):
            return
        self.cancel()
        self.persist()
        self.root.destroy()


if __name__ == "__main__":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    App(root)
    root.mainloop()
