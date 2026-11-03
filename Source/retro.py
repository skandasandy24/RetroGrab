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


def button(parent, text, cmd, width=None, **kw):
    b = tk.Button(parent, text=text, command=cmd, font=FONT, bg=GRAY, activebackground=GRAY,
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
        self.bind("<Configure>", lambda e: self.draw())

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
            self.create_rectangle(x, 4, x + block, h - 5, fill=NAVY, outline=NAVY)


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

    def select(self, name):
        for n, t in self.tabs.items():
            if n == name:
                t.configure(font=FONT_B, pady=4)
            else:
                t.configure(font=FONT, pady=2)


def scrolled_listbox(parent, height=4):
    wrap = tk.Frame(parent, bg=GRAY, relief="sunken", bd=2)
    lb = tk.Listbox(wrap, height=height, font=MONO, bg=WHITE, bd=0, highlightthickness=0,
                    selectbackground=NAVY, selectforeground=WHITE, activestyle="none")
    sb = tk.Scrollbar(wrap, command=lb.yview)
    lb.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    lb.pack(side="left", fill="both", expand=True)
    return wrap, lb


class RetroWindow:
    """Gives a Tk/Toplevel window a Win95 frame + gradient title bar."""

    def __init__(self, win, title, on_close, minimizable=True):
        self.win = win
        self._drag = (0, 0)
        win.configure(bg=GRAY)
        win.overrideredirect(True)
        self.outer = tk.Frame(win, bg=GRAY, relief="raised", bd=3)
        self.outer.pack(fill="both", expand=True)

        bar = tk.Canvas(self.outer, height=22, highlightthickness=0, bg=NAVY)
        bar.pack(fill="x", padx=1, pady=1)
        btns = tk.Frame(bar, bg=GRAY)
        holder = bar.create_window(0, 3, window=btns, anchor="ne")

        def paint(e):
            bar.delete("grad")
            steps = 64
            for i in range(steps):
                t = i / (steps - 1)
                c = f"#{int(0x10 * t):02x}{int(0x84 * t):02x}{int(0x80 + (0xd0 - 0x80) * t):02x}"
                bar.create_rectangle(e.width * i / steps, 0, e.width * (i + 1) / steps + 1, 22,
                                     fill=c, outline=c, tags="grad")
            bar.tag_lower("grad")
            bar.coords(holder, e.width - 3, 3)

        bar.bind("<Configure>", paint)
        # app logo in the title bar (falls back to nothing if the file is missing)
        self._icon = None
        try:
            self._icon = tk.PhotoImage(master=win, file=ICON_FILE)
            bar.create_image(3, 11, image=self._icon, anchor="w")
        except (tk.TclError, OSError):
            pass
        bar.create_text(25, 11, text=title, anchor="w", fill=WHITE, font=FONT_B)

        items = [("_", self.minimize)] if minimizable else []
        items += [("✕", on_close)]
        for sym, cmd in items:
            tk.Button(btns, text=sym, command=cmd, font=("Microsoft Sans Serif", 7, "bold"), bg=GRAY,
                      activebackground=GRAY, relief="raised", bd=2, width=2, padx=0, pady=0,
                      highlightthickness=0).pack(side="left", padx=(0, 2) if sym == "_" else 0)
        bar.bind("<ButtonPress-1>", self._start)
        bar.bind("<B1-Motion>", self._move)
        win.after(10, self._taskbar)

    def _start(self, e):
        self._drag = (e.x_root - self.win.winfo_x(), e.y_root - self.win.winfo_y())

    def _move(self, e):
        self.win.geometry(f"+{e.x_root - self._drag[0]}+{e.y_root - self._drag[1]}")

    def _hwnd(self):
        return ctypes.windll.user32.GetParent(self.win.winfo_id())

    def _taskbar(self):
        try:
            hwnd = self._hwnd()
            style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, (style & ~0x80) | 0x40000)
            self.win.withdraw()
            self.win.after(10, self.win.deiconify)
        except Exception:
            pass

    def minimize(self):
        try:
            ctypes.windll.user32.ShowWindow(self._hwnd(), 6)
        except Exception:
            self.win.iconify()

    def center(self, min_width=600):
        w = self.win
        w.update_idletasks()
        scale = w.winfo_fpixels("1i") / 96
        width = max(w.winfo_reqwidth(), int(min_width * scale))
        height = w.winfo_reqheight()
        x = (w.winfo_screenwidth() - width) // 2
        y = max(0, (w.winfo_screenheight() - height) // 2 - int(20 * scale))
        w.geometry(f"{width}x{height}+{x}+{y}")
