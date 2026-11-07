"""Windows 95 style widgets for Tkinter."""
import ctypes
import os
import sys
import tkinter as tk

ICON_FILE = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))),
                         "assets", "titlebar.png")

GRAY = "#c0c0c0"
DARK = "#808080"
WHITE = "#ffffff"
BLACK = "#000000"
NAVY = "#000080"
FONT = ("Microsoft Sans Serif", 9)
FONT_B = ("Microsoft Sans Serif", 9, "bold")
MONO = ("Courier New", 9)


# ---------------------------------------------------------------- themes
# Widgets are always built in the Classic 95 look; apply_tree() restyles them, and
# Classic 95 simply restores what each widget was built with.
def _t(**k):
    base = dict(dark=None, blocks=False, radius=0, flat=True, mono=("Consolas", 9))
    base.update(k)
    return base


THEMES = {
    "Classic 95": _t(flat=False, font="Microsoft Sans Serif", panel=GRAY, fg=BLACK, input=WHITE, input_fg=BLACK, muted=DARK, line=DARK,
                     accent=NAVY, accent_fg=WHITE, btn=GRAY, btn_fg=BLACK, title=(NAVY, "#1084d0"), title_fg=WHITE,
                     tbtn=GRAY, tbtn_fg=BLACK, close=GRAY, close_fg=BLACK, bar=NAVY, blocks=True, ok="#006400", err="#b00000"),
    "XP": _t(font="Tahoma", panel="#ece9d8", fg=BLACK, input=WHITE, input_fg=BLACK, muted="#6b6858", line="#7f9db9",
             accent="#316ac5", accent_fg=WHITE, btn="#f5f4ea", btn_fg=BLACK, title=("#0a4fd6", "#3a8cf5"), title_fg=WHITE,
             tbtn="#2f71e6", tbtn_fg=WHITE, close="#c63d20", close_fg=WHITE, bar="#2fb43a", blocks=True, radius=4, ok="#14761f", err="#b3261e"),
    "7": _t(font="Segoe UI", panel="#eef3fa", fg="#1e2b3c", input=WHITE, input_fg="#1e2b3c", muted="#5f6f82", line="#a9bdd4",
            accent="#1f6fc4", accent_fg=WHITE, btn="#f6f9fd", btn_fg="#1e2b3c", title=("#b9d1ea", "#e3eefa"), title_fg="#1e395b",
            tbtn="#d3e2f2", tbtn_fg="#1e395b", close="#b84040", close_fg=WHITE, bar="#06b025", radius=3, ok="#14761f", err="#b3261e"),
    "8": _t(font="Segoe UI", panel="#f0f0f0", fg="#1f1f1f", input=WHITE, input_fg="#1f1f1f", muted="#5e5e5e", line="#adadad",
            accent="#5c2d91", accent_fg=WHITE, btn="#e1e1e1", btn_fg="#1f1f1f", title=("#5c2d91", "#5c2d91"), title_fg=WHITE,
            tbtn="#5c2d91", tbtn_fg=WHITE, close="#b84040", close_fg=WHITE, bar="#5c2d91", ok="#14761f", err="#b3261e"),
    "10": _t(font="Segoe UI", panel="#f2f2f2", fg="#111111", input=WHITE, input_fg="#111111", muted="#5c5c5c", line="#bdbdbd",
             accent="#006fc8", accent_fg=WHITE, btn="#e6e6e6", btn_fg="#111111", title=(WHITE, WHITE), title_fg="#111111",
             tbtn=WHITE, tbtn_fg="#111111", close="#e81123", close_fg=WHITE, bar="#0078d7", ok="#107c10", err="#c42b1c",
             dark=dict(panel="#1f1f1f", fg="#f2f2f2", input="#2b2b2b", input_fg="#f2f2f2", muted="#a6a6a6", line="#4a4a4a",
                       accent="#2b9cf2", accent_fg="#0b0b0b", btn="#333333", btn_fg="#f2f2f2", title=("#141414", "#141414"), title_fg="#f2f2f2",
                       tbtn="#141414", tbtn_fg="#f2f2f2", bar="#2b9cf2", ok="#6ccb5f", err="#ff99a4")),
    "11": _t(font="Segoe UI", panel="#f3f3f3", fg="#1b1b1b", input=WHITE, input_fg="#1b1b1b", muted="#5d5d5d", line="#d1d1d1",
             accent="#005fb8", accent_fg=WHITE, btn="#fbfbfb", btn_fg="#1b1b1b", title=("#eeeeee", "#eeeeee"), title_fg="#1b1b1b",
             tbtn="#eeeeee", tbtn_fg="#1b1b1b", close="#c42b1c", close_fg=WHITE, bar="#005fb8", radius=7, ok="#0f7b0f", err="#c42b1c",
             dark=dict(panel="#202020", fg="#f3f3f3", input="#2d2d2d", input_fg="#f3f3f3", muted="#a8a8a8", line="#454545",
                       accent="#60cdff", accent_fg="#0b0b0b", btn="#2d2d2d", btn_fg="#f3f3f3", title=("#1a1a1a", "#1a1a1a"), title_fg="#f3f3f3",
                       tbtn="#1a1a1a", tbtn_fg="#f3f3f3", bar="#60cdff", ok="#6ccb5f", err="#ff99a4")),
}
T = dict(THEMES["Classic 95"])


def has_dark(name):
    return bool(THEMES.get(name, {}).get("dark"))


def set_theme(name, dark=False):
    """Makes `name` the current theme. Unknown names fall back to Classic 95."""
    t = dict(THEMES.get(name) or THEMES["Classic 95"])
    if dark and t.get("dark"):
        t.update(t["dark"])
    T.clear()
    T.update(t)


def _font(orig):
    s = str(orig)
    if "Courier" in s:
        return T["mono"]
    return (T["font"], 9, "bold") if "bold" in s else (T["font"], 9)


def _hexrgb(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def round_image(master, w, h, r, fill, border, back):
    """A smooth rounded rectangle as a PhotoImage, for theme buttons."""
    f, b, k = _hexrgb(fill), _hexrgb(border), _hexrgb(back)

    def mix(p, q, a):
        return tuple(int(p[i] + (q[i] - p[i]) * a) for i in range(3))

    def px(x, y):
        cx = min(max(x + .5, r), w - r)
        cy = min(max(y + .5, r), h - r)
        d = ((x + .5 - cx) ** 2 + (y + .5 - cy) ** 2) ** .5
        edge = max(0.0, min(1.0, r - d + .5))              # inside the outer shape
        inner = max(0.0, min(1.0, r - 1 - d + .5))         # inside the 1 px border
        if x + .5 > r and x + .5 < w - r:
            edge, inner = 1.0, (0.0 if y == 0 or y == h - 1 else 1.0)
        elif y + .5 > r and y + .5 < h - r:
            edge, inner = 1.0, (0.0 if x == 0 or x == w - 1 else 1.0)
        return mix(k, mix(b, f, inner), edge)

    img = tk.PhotoImage(master=master, width=w, height=h)
    rows = []
    for y in range(h):
        rows.append("{" + " ".join("#%02x%02x%02x" % px(x, y) for x in range(w)) + "}")
    img.put(" ".join(rows))
    return img


_KEYS = ("bg", "fg", "activebackground", "activeforeground", "selectcolor", "relief", "bd", "highlightthickness", "highlightbackground",
         "highlightcolor", "font", "insertbackground", "selectbackground", "selectforeground", "disabledforeground", "image", "compound", "width", "height", "padx", "pady")


def _line(w):
    w.configure(relief="flat", highlightthickness=1, highlightbackground=T["line"], highlightcolor=T["line"])


def _style(w, o, rounded):
    c = w.winfo_class()
    was_sunk = o.get("relief") in ("sunken", "raised", "groove") and int(str(o.get("bd", 0)) or 0) > 0
    bg0 = str(o.get("bg", "")).lower()
    if c in ("Frame", "Toplevel", "Tk"):
        w.configure(bg=T["line"] if bg0 == DARK else T["panel"])
        if was_sunk and c == "Frame":
            w.configure(bd=0); _line(w)
    elif c == "Labelframe":
        w.configure(bg=T["panel"], fg=T["fg"], bd=0, font=_font(o["font"])); _line(w)
    elif c == "Label":
        w.configure(bg=T["panel"], fg=T["muted"] if str(o.get("fg", "")).lower() == DARK else T["fg"], font=_font(o["font"]))
        if was_sunk:
            w.configure(bd=0); _line(w)
    elif c == "Button":
        w.configure(bg=T["btn"], fg=T["btn_fg"], activebackground=T["line"], activeforeground=T["btn_fg"], disabledforeground=T["muted"], font=_font(o["font"]), bd=0)
        _line(w)
        if T["radius"]:
            rounded.append(w)
    elif c == "Menubutton":
        if o.get("relief") == "flat":
            w.configure(bg=T["panel"], fg=T["fg"], activebackground=T["accent"], activeforeground=T["accent_fg"], font=_font(o["font"]))
        else:
            w.configure(bg=T["btn"], fg=T["btn_fg"], activebackground=T["line"], activeforeground=T["btn_fg"], font=_font(o["font"]), bd=0); _line(w)
    elif c in ("Radiobutton", "Checkbutton"):
        w.configure(bg=T["panel"], fg=T["fg"], activebackground=T["panel"], activeforeground=T["fg"], selectcolor=T["input"], font=_font(o["font"]))
    elif c in ("Text", "Entry"):
        if bg0 == BLACK:
            w.configure(font=T["mono"])
            return
        w.configure(bg=T["input"], fg=T["input_fg"], insertbackground=T["input_fg"], selectbackground=T["accent"], selectforeground=T["accent_fg"], font=_font(o["font"]))
        if was_sunk:
            _line(w); w.configure(highlightcolor=T["accent"])
    elif c == "Listbox":
        w.configure(bg=T["input"], fg=T["input_fg"], selectbackground=T["accent"], selectforeground=T["accent_fg"], font=T["mono"])
    elif c == "Menu":
        w.configure(bg=T["input"] if bg0 == WHITE else T["panel"], fg=T["fg"] if bg0 != WHITE else T["input_fg"], activebackground=T["accent"], activeforeground=T["accent_fg"], font=_font(o["font"]))


def apply_tree(w, _rounded=None):
    """Applies the current theme to `w` and everything inside it."""
    top = _rounded is None
    rounded = [] if top else _rounded
    if hasattr(w, "_retro"):
        w._retro.restyle()
    if isinstance(w, TabStrip):
        w.restyle()
    elif isinstance(w, BlockProgress):
        w.restyle()
    elif getattr(w, "_themed_elsewhere", False):
        pass
    elif w.winfo_class() == "Scrollbar":
        if hasattr(w, "_flat"):
            w._swap()
    else:
        if not hasattr(w, "_orig"):
            w._orig = {k: w.cget(k) for k in _KEYS if k in w.keys()}
        if isinstance(w, ThemedButton):
            w._rounded = False
        w.configure(**w._orig)
        if T["flat"]:
            _style(w, w._orig, rounded)
        if isinstance(w, ThemedButton):
            w.sync()
    for child in w.winfo_children():
        apply_tree(child, rounded)
    if top and rounded:
        w.update_idletasks()
        for b in rounded:
            bw, bh = b.winfo_reqwidth(), b.winfo_reqheight() + 2
            b._img = round_image(b, bw, bh, T["radius"], T["btn"], T["line"], T["panel"])
            b.configure(image=b._img, compound="center", width=bw, height=bh, bg=T["panel"], activebackground=T["panel"], highlightthickness=0, padx=0, pady=0)
            if isinstance(b, ThemedButton):
                b._rounded = True
                b.sync()


class FlatScroll(tk.Canvas):
    """A slim scrollbar for the modern themes (the Windows one can't be recoloured)."""

    def __init__(self, parent, target):
        super().__init__(parent, width=11, height=1, highlightthickness=0, bd=0)
        self.target, self.pos = target, (0.0, 1.0)
        self._themed_elsewhere = True
        self.bind("<Configure>", lambda e: self.draw())
        self.bind("<Button-1>", self._drag)
        self.bind("<B1-Motion>", self._drag)

    def set(self, a, b):
        self.pos = (float(a), float(b))
        self.draw()

    def _drag(self, e):
        size = self.pos[1] - self.pos[0]
        self.target.yview_moveto(max(0.0, e.y / max(1, self.winfo_height()) - size / 2))

    def draw(self):
        self.configure(bg=T["input"])
        self.delete("all")
        h = self.winfo_height()
        if self.pos[1] - self.pos[0] < .999:
            self.create_rectangle(3, self.pos[0] * h, 8, self.pos[1] * h, fill=T["muted"], outline="")


def scrollbar(parent, target):
    """Packs a scrollbar for `target`: the Windows one on Classic 95, a slim one otherwise."""
    sb = tk.Scrollbar(parent, command=target.yview)
    flat = FlatScroll(parent, target)
    sb._flat = flat

    def swap():
        if T["flat"]:
            sb.pack_forget()
            flat.pack(side="right", fill="y", before=target)
            flat.draw()
        else:
            flat.pack_forget()
            sb.pack(side="right", fill="y", before=target)

    sb._swap = swap
    target.configure(yscrollcommand=lambda a, b: (sb.set(a, b), flat.set(a, b)))
    sb.pack(side="right", fill="y")
    return sb


class ThemedButton(tk.Button):
    """On rounded themes a disabled button keeps its clean image: Windows would dither it,
    so it stays technically enabled, does nothing when clicked, and greys its text instead."""

    def __init__(self, parent, **kw):
        self._want, self._cmd, self._rounded = kw.get("state", "normal"), kw.get("command"), False
        super().__init__(parent, **kw)

    def configure(self, cnf=None, **kw):
        if isinstance(cnf, dict):
            kw = {**cnf, **kw}
            cnf = None
        if cnf is not None or not kw:
            return super().configure(cnf)
        sync = "state" in kw or "command" in kw
        self._want = kw.pop("state", self._want)
        self._cmd = kw.pop("command", self._cmd)
        if kw:
            super().configure(**kw)
        if sync:
            self.sync()

    config = configure

    def sync(self):
        off = self._want == "disabled"
        if self._rounded:
            super().configure(state="normal", command=(lambda: None) if off else (self._cmd or ""),
                              fg=T["muted"] if off else T["btn_fg"], activeforeground=T["muted"] if off else T["btn_fg"])
        else:
            super().configure(state=self._want, command=self._cmd or "")


def button(parent, text, cmd, width=None, **kw):
    b = ThemedButton(parent, text=text, command=cmd, font=FONT, bg=GRAY, activebackground=GRAY,
                  relief="raised", bd=2, padx=8, pady=1, highlightthickness=0, **kw)
    if width:
        b.configure(width=width)
    return b


def group(parent, title):
    return tk.LabelFrame(parent, text=f" {title} ", font=FONT, bg=GRAY, relief="groove", bd=2, padx=8, pady=5)


def label(parent, text="", **kw):
    kw.setdefault("bg", GRAY)
    kw.setdefault("font", FONT)
    return tk.Label(parent, text=text, **kw)


def entry(parent, var):
    return tk.Entry(parent, textvariable=var, font=FONT, bg=WHITE, relief="sunken", bd=2, highlightthickness=0)


def text_box(parent, height=3):
    return tk.Text(parent, height=height, font=FONT, bg=WHITE, relief="sunken", bd=2, wrap="word",
                   highlightthickness=0, undo=True)


def radio(parent, text, var, value, cmd=None):
    return tk.Radiobutton(parent, text=text, value=value, variable=var, font=FONT, bg=GRAY,
                          activebackground=GRAY, selectcolor=WHITE, highlightthickness=0, command=cmd)


def check(parent, text, var):
    return tk.Checkbutton(parent, text=text, variable=var, font=FONT, bg=GRAY, activebackground=GRAY,
                          selectcolor=WHITE, highlightthickness=0)


class Dropdown(tk.OptionMenu):
    def __init__(self, parent, var, values, width=12, command=None):
        super().__init__(parent, var, *values)
        self.var, self.command = var, command
        self.configure(font=FONT, bg=GRAY, activebackground=GRAY, relief="raised", bd=2,
                       highlightthickness=0, width=width, anchor="w")
        self["menu"].configure(font=FONT, bg=WHITE, activebackground=NAVY, activeforeground=WHITE,
                               relief="solid", bd=1)
        self.set_values(values)

    def set_values(self, values):
        menu = self["menu"]
        menu.delete(0, "end")
        for v in values:
            menu.add_command(label=v, command=lambda v=v: self._pick(v))
        if self.var.get() not in values:
            self.var.set(values[0])

    def _pick(self, v):
        self.var.set(v)
        if self.command:
            self.command(v)


class BlockProgress(tk.Canvas):
    """Segmented navy-block progress bar. set(None) shows a moving 'busy' marquee."""

    def __init__(self, parent, **kw):
        super().__init__(parent, height=22, bg=WHITE, highlightthickness=0, relief="sunken", bd=2, **kw)
        self.value = 0.0
        self.busy = False
        self._pos = 0
        self._job = None
        self._base = {"relief": "sunken", "bd": 2, "highlightthickness": 0}
        self.bind("<Configure>", lambda e: self.draw())

    def restyle(self):
        self.configure(bg=T["input"], **self._base)
        if T["flat"]:
            self.configure(bd=2)
            _line(self)
        self.draw()

    def set(self, pct):
        if pct is None:
            if not self.busy:
                self.busy = True
                self._animate()
            return
        self.busy = False
        self.value = max(0.0, min(100.0, float(pct)))
        self.draw()

    def _animate(self):
        if not self.busy:
            return
        self._pos += 1
        self.draw()
        self._job = self.after(90, self._animate)

    def draw(self):
        self.delete("all")
        w, h = self.winfo_width() - 8, self.winfo_height()
        if not T["blocks"]:   # modern themes: one smooth bar
            if self.busy:
                x = (self._pos * 14) % (w + 120) - 120
                self.create_rectangle(4 + max(0, x), 4, 4 + min(w, x + 120), h - 5, fill=T["bar"], outline=T["bar"])
            elif self.value > 0:
                self.create_rectangle(4, 4, 4 + w * self.value / 100, h - 5, fill=T["bar"], outline=T["bar"])
            return
        block, gap = 9, 2
        n_total = max(1, w // (block + gap))
        if self.busy:
            span = 5
            start = self._pos % (n_total + span) - span
            idx = range(max(0, start), min(n_total, start + span))
        else:
            idx = range(round(n_total * self.value / 100))
        for i in idx:
            x = 4 + i * (block + gap)
            self.create_rectangle(x, 4, x + block, h - 5, fill=T["bar"], outline=T["bar"])


class TabStrip(tk.Frame):
    """Row of classic tabs. `on_select(name)` is called on click."""

    def __init__(self, parent, names, on_select):
        super().__init__(parent, bg=GRAY)
        self.on_select = on_select
        self.tabs = {}
        for n in names:
            t = tk.Label(self, text=n, font=FONT, bg=GRAY, relief="raised", bd=2, padx=12, pady=2, cursor="hand2")
            t.pack(side="left", anchor="s")
            t.bind("<Button-1>", lambda e, n=n: self.on_select(n))
            self.tabs[n] = t
            t._themed_elsewhere = True
        self.current = None

    def restyle(self):
        self.configure(bg=T["panel"])
        if self.current:
            self.select(self.current)

    def select(self, name):
        self.current = name
        flat = T["flat"]
        for n, t in self.tabs.items():
            on = n == name
            if flat:
                t.configure(relief="flat", bd=0, bg=T["input"] if on else T["panel"], fg=T["accent"] if on and T["accent"] != T["panel"] else T["fg"] if on else T["muted"],
                            font=(T["font"], 9, "bold") if on else (T["font"], 9), pady=4 if on else 2, highlightthickness=1 if on else 0, highlightbackground=T["line"])
            else:
                t.configure(relief="raised", bd=2, bg=GRAY, fg=BLACK, font=FONT_B if on else FONT, pady=4 if on else 2, highlightthickness=0)


def scrolled_listbox(parent, height=4):
    wrap = tk.Frame(parent, bg=GRAY, relief="sunken", bd=2)
    lb = tk.Listbox(wrap, height=height, font=MONO, bg=WHITE, bd=0, highlightthickness=0,
                    selectbackground=NAVY, selectforeground=WHITE, activestyle="none")
    scrollbar(wrap, lb)
    lb.pack(side="left", fill="both", expand=True)
    return wrap, lb


class RetroWindow:
    """Gives a Tk/Toplevel window a Win95 frame + gradient title bar."""

    def __init__(self, win, title, on_close, minimizable=True):
        self.win = win
        self._drag = (0, 0)
        win.configure(bg=GRAY)
        win.overrideredirect(True)
        win._retro = self
        self.outer = tk.Frame(win, bg=GRAY, relief="raised", bd=3)
        self.outer.pack(fill="both", expand=True)

        bar = tk.Canvas(self.outer, height=22, highlightthickness=0, bg=NAVY)
        bar._themed_elsewhere = True
        self.bar = bar
        bar.pack(fill="x", padx=1, pady=1)
        btns = tk.Frame(bar, bg=GRAY)
        btns._themed_elsewhere = True
        self.tbtns, self.title_btns = btns, []
        holder = bar.create_window(0, 3, window=btns, anchor="ne")

        def paint(e=None):
            width = e.width if e else bar.winfo_width()
            bar.delete("grad")
            steps = 64
            (r1, g1, b1), (r2, g2, b2) = _hexrgb(T["title"][0]), _hexrgb(T["title"][1])
            for i in range(steps):
                t = i / (steps - 1)
                c = f"#{int(r1 + (r2 - r1) * t):02x}{int(g1 + (g2 - g1) * t):02x}{int(b1 + (b2 - b1) * t):02x}"
                bar.create_rectangle(width * i / steps, 0, width * (i + 1) / steps + 1, 22,
                                     fill=c, outline=c, tags="grad")
            bar.tag_lower("grad")
            bar.coords(holder, width - 3, 3)

        self._paint = paint
        bar.bind("<Configure>", paint)
        # app logo in the title bar (falls back to nothing if the file is missing)
        self._icon = None
        try:
            self._icon = tk.PhotoImage(master=win, file=ICON_FILE)
            bar.create_image(3, 11, image=self._icon, anchor="w")
        except (tk.TclError, OSError):
            pass
        self.title_text = bar.create_text(25, 11, text=title, anchor="w", fill=WHITE, font=FONT_B)

        items = [("_", self.minimize)] if minimizable else []
        items += [("✕", on_close)]
        for sym, cmd in items:
            tb = tk.Button(btns, text=sym, command=cmd, font=("Microsoft Sans Serif", 7, "bold"), bg=GRAY,
                           activebackground=GRAY, relief="raised", bd=2, width=2, padx=0, pady=0,
                           highlightthickness=0)
            tb.pack(side="left", padx=(0, 2) if sym == "_" else 0)
            tb._themed_elsewhere, tb._close = True, sym != "_"
            self.title_btns.append(tb)
        bar.bind("<ButtonPress-1>", self._start)
        bar.bind("<B1-Motion>", self._move)
        win.after(10, self._taskbar)

    def restyle(self):
        flat = T["flat"]
        self.bar.configure(bg=T["title"][0])
        self.tbtns.configure(bg=T["tbtn"])
        self.bar.itemconfigure(self.title_text, fill=T["title_fg"], font=(T["font"], 9, "bold"))
        for b in self.title_btns:
            bg, fg = (T["close"], T["close_fg"]) if b._close else (T["tbtn"], T["tbtn_fg"])
            b.configure(bg=bg, fg=fg, activebackground=bg, activeforeground=fg, relief="flat" if flat else "raised")
        self._paint()
        self.win.after(70, self._corners)

    def _corners(self):
        """Soft window corners on the themes that have them (Windows 11 only; ignored elsewhere)."""
        try:
            pref = ctypes.c_int(2 if T["radius"] >= 7 else 1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(ctypes.c_void_p(self._hwnd()), 33, ctypes.byref(pref), 4)
        except Exception:
            pass

    def fit(self):
        """Resizes to the content after a theme change, keeping the window where it is."""
        w = self.win
        w.update_idletasks()
        scale = w.winfo_fpixels("1i") / 96
        w.geometry(f"{max(w.winfo_reqwidth(), int(640 * scale))}x{w.winfo_reqheight()}")

    def _start(self, e):
        self._drag = (e.x_root - self.win.winfo_x(), e.y_root - self.win.winfo_y())

    def _move(self, e):
        self.win.geometry(f"+{e.x_root - self._drag[0]}+{e.y_root - self._drag[1]}")

    def _hwnd(self):
        return ctypes.windll.user32.GetParent(self.win.winfo_id())

    def _set_window_icon(self):
        """Give the real (frameless) window the RetroGrab icon for the taskbar and Alt+Tab."""
        ico = os.path.join(os.path.dirname(ICON_FILE), "retrograb.ico")
        if not os.path.isfile(ico):
            return
        from ctypes import wintypes
        u32 = ctypes.windll.user32
        u32.LoadImageW.restype = wintypes.HANDLE
        u32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT,
                                   ctypes.c_int, ctypes.c_int, wintypes.UINT]
        u32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        hwnd = self._hwnd()
        for which, cx, cy in ((1, 11, 12), (0, 49, 50)):  # ICON_BIG: SM_CXICON; ICON_SMALL: SM_CXSMICON
            h = u32.LoadImageW(None, ico, 1, u32.GetSystemMetrics(cx), u32.GetSystemMetrics(cy), 0x10)
            if h:
                u32.SendMessageW(hwnd, 0x80, which, h)  # WM_SETICON

    def _taskbar(self):
        try:
            hwnd = self._hwnd()
            style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, (style & ~0x80) | 0x40000)
            self.win.withdraw()
            self.win.after(10, self.win.deiconify)
        except Exception:
            pass
        self.win.after(60, self._safe_icon)

    def _safe_icon(self):
        try:
            self._set_window_icon()
        except Exception:
            pass

    def minimize(self):
        try:
            ctypes.windll.user32.ShowWindow(self._hwnd(), 6)
        except Exception:
            self.win.iconify()

    def center(self, min_width=600):
        w = self.win
        apply_tree(w)
        w.update_idletasks()
        scale = w.winfo_fpixels("1i") / 96
        width = max(w.winfo_reqwidth(), int(min_width * scale))
        height = w.winfo_reqheight()
        x = (w.winfo_screenwidth() - width) // 2
        y = max(0, (w.winfo_screenheight() - height) // 2 - int(20 * scale))
        w.geometry(f"{width}x{height}+{x}+{y}")
