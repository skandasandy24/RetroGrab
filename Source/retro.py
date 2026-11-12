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
    "XP": _t(font="Tahoma", size=8, panel="#ece9d8", fg=BLACK, input=WHITE, input_fg=BLACK, muted="#6b6858", line="#7f9db9",
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
    "11": _t(font="Segoe UI Variable Text", panel="#f3f3f3", fg="#1b1b1b", input=WHITE, input_fg="#1b1b1b", muted="#5d5d5d", line="#d1d1d1",
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
    t.update(CAPTION.get(name) or CAPTION["Classic 95"])
    t["is_dark"] = bool(dark and THEMES.get(name, {}).get("dark"))
    if t["is_dark"] and t.get("frame_dark"):
        t["frame"] = (t["frame_dark"], t["frame"][1])
    T.clear()
    T.update(t)


def _font(orig):
    s = str(orig)
    if "Courier" in s:
        return T["mono"]
    fam = _family(T["font"], "Segoe UI")
    return (fam, T.get("size", 9), "bold") if "bold" in s else (fam, T.get("size", 9))


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
         "highlightcolor", "font", "insertbackground", "selectbackground", "selectforeground", "disabledforeground", "image", "compound", "width", "height", "padx", "pady",
         "indicatoron", "selectimage", "offrelief", "overrelief")


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
            if isinstance(w, tk.OptionMenu):
                w.configure(indicatoron=0, padx=6)
                if not hasattr(w, "_arrow"):
                    w._arrow = tk.Label(w, bd=0, highlightthickness=0, cursor="arrow")
                    w._arrow._themed_elsewhere = True
                    w._arrow.bind("<Button-1>", lambda e, m=w: m["menu"].post(m.winfo_rootx(), m.winfo_rooty() + m.winfo_height()))
                w._arrow.configure(image=arrow_icon(w), bg=T["btn"])
                w._arrow.place(relx=1.0, x=-5, rely=.5, anchor="e")
    elif c in ("Radiobutton", "Checkbutton"):
        off, on = check_icons(w, "radio" if c == "Radiobutton" else "check")
        w.configure(bg=T["panel"], fg=T["fg"], activebackground=T["panel"], activeforeground=T["fg"], selectcolor=T["panel"], font=_font(o["font"]),
                    indicatoron=0, image=off, selectimage=on, compound="left", relief="flat", offrelief="flat", overrelief="flat", bd=0, padx=4)
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
        if hasattr(w, "_arrow"):
            w._arrow.place_forget()
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


# ---------------------------------------------------------------- title bars per Windows version
# Measured on Windows 11 (100%): title bar 31 px, caption buttons 46 px wide, 10x10 glyphs with 1 px strokes.
# Windows 10 used the same caption layout with Segoe MDL2 Assets glyphs. XP, 7 and 8 are recreated from their look.
CAPTION = {
    "Classic 95": dict(cap=None),
    "XP": dict(cap="xp", title_h=30, frame=("#0054e3", 3), title_font=("Trebuchet MS", -13, "bold"), title_x=27,
               title_stops=[(0, "#3c8cf6"), (.08, "#0a63f2"), (.45, "#0058ee"), (.85, "#0052e5"), (1, "#0046cf")]),
    "7": dict(cap="7", title_h=30, frame=("#a9c4e6", 6), title_font=("Segoe UI", -12), title_x=31,
              title_stops=[(0, "#cfe0f3"), (.5, "#bdd3ee"), (1, "#a9c4e6")]),
    "8": dict(cap="8", title_h=30, frame=("#5c2d91", 6), title_font=("Segoe UI", -12), title_x=None),
    "10": dict(cap="10", title_h=31, frame=("#8c8c8c", 1), frame_dark="#3c3c3c", title_font=("Segoe UI", -12), title_x=30),
    "11": dict(cap="11", title_h=31, frame=("#cdcdcd", 1), frame_dark="#3a3a3a", title_font=("Segoe UI Variable Text", -12), title_x=48),
}
_FAMILIES = None


def _family(name, fallback):
    global _FAMILIES
    if _FAMILIES is None:
        import tkinter.font as tkfont
        _FAMILIES = set(tkfont.families())
    return name if name in _FAMILIES else fallback


def _vgrad(cv, x0, y0, x1, y1, stops, tag):
    """Vertical gradient as 1 px lines (stops: [(0..1, '#rrggbb'), ...])."""
    h = max(1, int(y1 - y0))
    for i in range(h):
        p = i / max(1, h - 1)
        for (a, ca), (b, cb) in zip(stops, stops[1:]):
            if p <= b:
                k = (p - a) / max(1e-6, b - a)
                (r1, g1, b1), (r2, g2, b2) = _hexrgb(ca), _hexrgb(cb)
                c = "#%02x%02x%02x" % (int(r1 + (r2 - r1) * k), int(g1 + (g2 - g1) * k), int(b1 + (b2 - b1) * k))
                break
        cv.create_line(x0, y0 + i, x1, y0 + i, fill=c, tags=tag)


def _grad_round(master, w, h, r, stops, border, back):
    """A rounded button face with a vertical gradient (XP style), as a smooth PhotoImage."""
    def at(p):
        for (a, ca), (b, cb) in zip(stops, stops[1:]):
            if p <= b:
                k = (p - a) / max(1e-6, b - a)
                x, y = _hexrgb(ca), _hexrgb(cb)
                return tuple(int(x[i] + (y[i] - x[i]) * k) for i in range(3))
        return _hexrgb(stops[-1][1])
    bo, bk = _hexrgb(border), _hexrgb(back)
    mix = lambda p, q, t: tuple(int(p[i] + (q[i] - p[i]) * t) for i in range(3))
    img = tk.PhotoImage(master=master, width=w, height=h)
    rows = []
    for y in range(h):
        fill = at(y / max(1, h - 1)); row = []
        for x in range(w):
            cx = min(max(x + .5, r), w - r); cy = min(max(y + .5, r), h - r)
            d = ((x + .5 - cx) ** 2 + (y + .5 - cy) ** 2) ** .5
            edge = max(0.0, min(1.0, r - d + .5)); inner = max(0.0, min(1.0, r - 1 - d + .5))
            if r < x + .5 < w - r:
                edge, inner = 1.0, (0.0 if y in (0, h - 1) else 1.0)
            elif r < y + .5 < h - r:
                edge, inner = 1.0, (0.0 if x in (0, w - 1) else 1.0)
            row.append("#%02x%02x%02x" % mix(bk, mix(bo, fill, inner), edge))
        rows.append("{" + " ".join(row) + "}")
    img.put(" ".join(rows))
    return img


def _caption_layout(style, W, H, names, s):
    """Caption button rectangles, right to left, in title bar coordinates."""
    if style in ("10", "11"):
        sizes, top, gap, right = {n: (46, H) for n in names}, 0, 0, 0
    elif style == "8":
        sizes, top, gap, right = {"min": (26, 20), "max": (26, 20), "close": (45, 20)}, 0, 0, 2
    elif style == "7":
        sizes, top, gap, right = {"min": (26, 19), "max": (25, 19), "close": (47, 19)}, 0, 0, 0
    else:  # xp
        sizes, top, gap, right = {n: (21, 21) for n in names}, (H - 21) // 2, 2, 5
    out, x = {}, W - right * s
    for n in reversed(names):
        w, h = sizes[n]
        out[n] = (x - w * s, top * s, x, (top + h) * s)
        x -= (w + gap) * s
    return out


def _glyph_font(style):
    if style == "11":
        return _family("Segoe Fluent Icons", "Segoe MDL2 Assets")
    return _family("Segoe MDL2 Assets", "Segoe UI Symbol")


def paint_caption(win, width):
    """Draws the whole title bar for a modern theme: background, icon, title and caption buttons."""
    cv, st, s = win.bar, T["cap"], win.scale
    H = int(T["title_h"] * s)
    cv.delete("grad"); cv.delete("cap")
    if T.get("title_stops") and not T.get("is_dark"):
        _vgrad(cv, 0, 0, width, H, T["title_stops"], "grad")
    else:
        cv.create_rectangle(0, 0, width, H, fill=T["title"][0], outline="", tags="grad")
    cv.tag_lower("grad")
    cy = H / 2
    cv.coords(win.icon_item, 5 * s if st == "xp" else (16 * s if st == "11" else 8 * s), cy) if win.icon_item else None
    fam, size, *rest = T["title_font"]
    font = (_family(fam, "Segoe UI"), int(size * s), *rest)
    title_x = T.get("title_x")
    if st == "xp":   # white bold title with a dark drop shadow
        cv.create_text(title_x * s + 1, cy + 1, text=win.title, anchor="w", fill="#0a1d6e", font=font, tags="cap")
    if st == "7":    # black title with a soft white glow
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1)):
            cv.create_text(title_x * s + dx, cy + dy, text=win.title, anchor="w", fill="#eef4fb", font=font, tags="cap")
    cv.itemconfigure(win.title_text, font=font, fill="#000000" if st == "7" else T["title_fg"], anchor="center" if title_x is None else "w")
    cv.coords(win.title_text, width / 2 if title_x is None else title_x * s, cy)
    cv.tag_raise(win.title_text)
    for n, (x0, y0, x1, y1) in _caption_layout(st, width, T["title_h"], win.caption_names, s).items():
        state = "disabled" if n == "max" else ("press" if win.cap_press == n else "hover" if win.cap_hover == n else "rest")
        _paint_button(win, cv, st, n, state, x0, y0, x1, y1, s)


def _paint_button(win, cv, st, n, state, x0, y0, x1, y1, s):
    dark = T.get("is_dark")
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    tag = ("cap", "btn_" + n)
    if st in ("10", "11"):
        if n == "close" and state in ("hover", "press"):
            bg = ("#e81123" if state == "hover" else "#f1707a") if st == "10" else ("#c42b1c" if state == "hover" else "#c83c31")
            fg = "#ffffff"
        else:
            light = {"10": {"hover": "#e5e5e5", "press": "#cccccc"}, "11": {"hover": "#e5e5e5", "press": "#ececec"}}
            darkc = {"10": {"hover": "#353535", "press": "#4a4a4a"}, "11": {"hover": "#2d2d2d", "press": "#292929"}}
            bg = (darkc if dark else light)[st].get(state)
            fg = ("#5a5a5a" if dark else "#b9b9b9") if state == "disabled" else T["title_fg"]
        if bg:
            cv.create_rectangle(x0, y0, x1, y1, fill=bg, outline="", tags=tag)
        code = {"min": "", "max": "", "close": ""}[n]
        cv.create_text(cx, cy - (1 if n == "min" else 2) * s, text=code, fill=fg, font=(_glyph_font(st), int(-10 * s)), tags=tag)
        return
    if st == "8":
        if n == "close":
            bg = {"rest": "#c75050", "hover": "#e04343", "press": "#993d3d"}[state]
        else:
            bg = {"hover": "#7a4aac", "press": "#45216d"}.get(state)
        if bg:
            cv.create_rectangle(x0, y0, x1, y1, fill=bg, outline="", tags=tag)
        fg = "#a58fc0" if state == "disabled" else "#ffffff"
        code = {"min": "", "max": "", "close": ""}[n]
        cv.create_text(cx, cy, text=code, fill=fg, font=(_glyph_font("10"), int(-10 * s), "bold"), tags=tag)
        return
    if st == "7":
        if n == "close":
            top, bot = {"rest": (("#eab2a6", "#de8d7e"), ("#c94532", "#d7634f")), "hover": (("#f6c4b8", "#ee9a89"), ("#e2442c", "#f06e55")),
                        "press": (("#c98c80", "#b8675a"), ("#9d2a1b", "#ad3b2b"))}[state]
        else:
            top, bot = {"rest": (("#e7eef8", "#d4e1f1"), ("#b6c9e2", "#c8d8ec")), "hover": (("#e9f4ff", "#cfe7fd"), ("#8ec3f4", "#b5dafb")),
                        "press": (("#b9cce4", "#a7bede"), ("#7e9fc8", "#94b2d6")), "disabled": (("#dde6f2", "#cfdbeb"), ("#bccde3", "#c9d7ea"))}[state]
        mid = (y0 + y1) / 2
        _vgrad(cv, x0, y0, x1, mid, [(0, top[0]), (1, top[1])], tag)
        _vgrad(cv, x0, mid, x1, y1, [(0, bot[0]), (1, bot[1])], tag)
        cv.create_rectangle(x0, y0, x1 - 1, y1 - 1, outline="#43597a", tags=tag)
        cv.create_line(x0 + 1, y0 + 1, x1 - 1, y0 + 1, fill="#ffffff", tags=tag)
        g = "#c9d3e0" if state == "disabled" else "#ffffff"
        o = "#9aa9bd" if state == "disabled" else "#26364e"
        _glyph_shapes(cv, n, cx, cy, s, g, o, tag, style="7")
        return
    # XP: rounded, glossy blue buttons with a white rim; the close button is red-orange
    key = (n == "close", state, int(x1 - x0), int(y1 - y0))
    if key not in win.cap_images:
        if n == "close":
            stops = {"rest": [(0, "#e88a6f"), (.5, "#d2502f"), (1, "#c23c1d")], "hover": [(0, "#f6a68f"), (.5, "#e2603d"), (1, "#d24a28")],
                     "press": [(0, "#b6391b"), (1, "#9e2f14")]}[state]
        else:
            stops = {"rest": [(0, "#6aa8ff"), (.5, "#2a6fe8"), (1, "#3c80f0")], "hover": [(0, "#8cbcff"), (.5, "#3f80f2"), (1, "#5291f6")],
                     "press": [(0, "#2558c8"), (1, "#1f4eb6")], "disabled": [(0, "#7da6ec"), (1, "#5d8be0")]}[state]
        win.cap_images[key] = _grad_round(cv, int(x1 - x0), int(y1 - y0), int(3 * s), stops, "#ffffff", "#0058ee")
    cv.create_image(x0, y0, image=win.cap_images[key], anchor="nw", tags=tag)
    _glyph_shapes(cv, n, cx, cy, s, "#9fbcf0" if state == "disabled" else "#ffffff", None, tag, style="xp")


def _glyph_shapes(cv, n, cx, cy, s, fill, outline, tag, style):
    """Thick pixel glyphs for XP and 7 (optionally with a dark outline, as on 7)."""
    def rect(x0, y0, x1, y1):
        if outline:
            cv.create_rectangle(cx + (x0 - 1) * s, cy + (y0 - 1) * s, cx + (x1 + 1) * s, cy + (y1 + 1) * s, fill=outline, outline="", tags=tag)
        cv.create_rectangle(cx + x0 * s, cy + y0 * s, cx + x1 * s, cy + y1 * s, fill=fill, outline="", tags=tag)
    if n == "min":
        rect(-4, 2, 3, 5) if style == "xp" else rect(-4, 1, 4, 3)
    elif n == "max":
        if outline:
            cv.create_rectangle(cx - 6 * s, cy - 5 * s, cx + 6 * s, cy + 5 * s, fill=outline, outline="", tags=tag)
        rect(-5, -4, 5, -1)
        rect(-5, -4, -3, 4); rect(3, -4, 5, 4); rect(-5, 2, 5, 4)
        if outline:
            cv.create_rectangle(cx - 3 * s, cy - 1 * s, cx + 3 * s, cy + 2 * s, fill=outline, outline="", tags=tag)
    else:
        w = 3 * s if style == "xp" else 2 * s
        pts = [(-4, -4, 4, 4), (-4, 4, 4, -4)]
        if outline:
            for x0, y0, x1, y1 in pts:
                cv.create_line(cx + x0 * s, cy + y0 * s, cx + x1 * s, cy + y1 * s, fill=outline, width=w + 2 * s, capstyle="projecting", tags=tag)
        for x0, y0, x1, y1 in pts:
            cv.create_line(cx + x0 * s, cy + y0 * s, cx + x1 * s, cy + y1 * s, fill=fill, width=w, capstyle="projecting", tags=tag)


# ---------------------------------------------------------------- checkbox, radio and drop-down icons per version
_ICONS = {}


def _paint_px(master, size, fn):
    """Builds a PhotoImage by sampling fn(x, y) -> (r, g, b, a) four times per pixel (smooth edges)."""
    img = tk.PhotoImage(master=master, width=size, height=size)
    back = _hexrgb(T["panel"])
    rows = []
    for y in range(size):
        row = []
        for x in range(size):
            acc = [0.0, 0.0, 0.0]
            for sx, sy in ((.25, .25), (.75, .25), (.25, .75), (.75, .75)):
                r, g, b, a = fn(x + sx, y + sy)
                for i, c in enumerate((r, g, b)):
                    acc[i] += (c * a + back[i] * (1 - a)) / 4
            row.append("#%02x%02x%02x" % tuple(int(v) for v in acc))
        rows.append("{" + " ".join(row) + "}")
    img.put(" ".join(rows))
    return img


def _rgba(c, a=1.0):
    return (*_hexrgb(c), a)


def _over(*layers):
    """Composites (r, g, b, a) layers bottom to top."""
    r = g = b = 0.0; a = 0.0
    for lr, lg, lb, la in layers:
        r, g, b = r * (1 - la) + lr * la, g * (1 - la) + lg * la, b * (1 - la) + lb * la
        a = a + la * (1 - a)
    return (r, g, b, a)


def _tick(x, y, s, w=1.6):
    """Distance-based check mark from (3,7)->(5.5,9.5)->(10,4) in a 13 px box."""
    def seg(ax, ay, bx, by):
        ax, ay, bx, by = ax * s, ay * s, bx * s, by * s
        dx, dy = bx - ax, by - ay
        t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
        return ((x - ax - t * dx) ** 2 + (y - ay - t * dy) ** 2) ** .5
    d = min(seg(3.2, 6.8, 5.5, 9.2), seg(5.5, 9.2, 9.8, 3.8))
    return max(0.0, min(1.0, w * s / 2 - d + .5))


def check_icons(master, kind):
    """(unchecked, checked) images for a checkbox ('check') or radio button ('radio') in the current theme."""
    st, dark = T.get("cap"), T.get("is_dark")
    key = (id(master.tk), st, dark, kind, T["panel"])
    if key in _ICONS:
        return _ICONS[key]
    s = max(1.0, master.winfo_fpixels("1i") / 96)
    n = int(round(13 * s))
    acc, fg = T["accent"], T["fg"]

    def box(x, y, r):          # inside a rounded square with radius r (in 13 px units)
        rr = r * s
        cx = min(max(x, rr), n - rr); cy = min(max(y, rr), n - rr)
        return max(0.0, min(1.0, rr - ((x - cx) ** 2 + (y - cy) ** 2) ** .5 + .5)) if rr else (1.0 if 0 <= x <= n and 0 <= y <= n else 0.0)

    def circle(x, y, rad):
        return max(0.0, min(1.0, rad * s - ((x - n / 2) ** 2 + (y - n / 2) ** 2) ** .5 + .5))

    def make(on):
        def fn(x, y):
            if kind == "check":
                outer, inner = box(x, y, 0 if st in ("xp", "7", "8", "10") else 3), 0.0
                inset = 1 * s
                ix, iy = x - inset, y - inset
                if inset <= x <= n - inset and inset <= y <= n - inset:
                    m = n - 2 * inset
                    inner = box(ix * n / m, iy * n / m, 0 if st != "11" else 2.2)
                if st == "xp":
                    p = y / n
                    face = _rgba("#%02x%02x%02x" % tuple(int(220 + 35 * p) for _ in range(3)))
                    layers = [_rgba("#1c5180", outer), (*face[:3], inner)]
                    if on:
                        layers.append(_rgba("#21a121", _tick(x, y, s, 2.2)))
                elif st == "7":
                    p = y / n
                    face = "#%02x%02x%02x" % ((int(222 + 25 * (1 - p)),) * 3)
                    layers = [_rgba("#8e8f8f", outer), _rgba(face, inner)]
                    if on:
                        layers.append(_rgba("#3b5a82", _tick(x, y, s, 1.9)))
                elif st == "8":
                    layers = [_rgba("#333333" if not dark else "#ffffff", outer), _rgba(T["input"], inner)]
                    if on:
                        layers.append(_rgba(T["input_fg"], _tick(x, y, s, 1.8)))
                else:   # 10 and 11: filled with the accent colour when ticked
                    border = acc if on else (T["fg"] if st == "10" else T["muted"])
                    layers = [_rgba(border, outer), _rgba(acc if on else T["panel"], inner)]
                    if on:
                        layers.append(_rgba(T["accent_fg"], _tick(x, y, s, 1.6)))
                return _over(*layers)
            # radio
            ring, fill = circle(x, y, 6.4), circle(x, y, 5.4)
            if st == "xp":
                layers = [_rgba("#1c5180", ring), _rgba("#f6f6f3", fill)]
                if on:
                    layers.append(_rgba("#21a121", circle(x, y, 2.6)))
            elif st == "7":
                layers = [_rgba("#8e8f8f", ring), _rgba("#eeeeee", fill)]
                if on:
                    layers.append(_rgba("#2b6bb6", circle(x, y, 3.0)))
            elif st == "8":
                layers = [_rgba("#333333" if not dark else "#ffffff", ring), _rgba(T["input"], fill)]
                if on:
                    layers.append(_rgba(T["input_fg"], circle(x, y, 2.8)))
            elif st == "10":
                layers = [_rgba(acc if on else T["fg"], ring), _rgba(T["panel"], fill)]
                if on:
                    layers.append(_rgba(T["fg"], circle(x, y, 2.8)))
            else:   # 11: accent ring with a light centre
                layers = [_rgba(acc if on else T["muted"], ring), _rgba(acc if on else T["panel"], fill)]
                if on:
                    layers.append(_rgba(T["accent_fg"], circle(x, y, 2.6)))
            return _over(*layers)
        return _paint_px(master, n, fn)

    _ICONS[key] = (make(False), make(True))
    return _ICONS[key]


def arrow_icon(master):
    """The small drop-down arrow for the current theme."""
    st, dark = T.get("cap"), T.get("is_dark")
    key = (id(master.tk), st, dark, "arrow", T["btn"])
    if key in _ICONS:
        return _ICONS[key]
    s = max(1.0, master.winfo_fpixels("1i") / 96)
    n = int(round(12 * s))
    col = T["btn_fg"]

    def fn(x, y):
        x, y = x / s, y / s
        if st in ("xp", "7"):   # solid triangle
            inside = 3 <= y <= 7 and abs(x - 6) <= (7 - y) * 0.9 + .6
            return _rgba(col, 1.0 if inside else 0.0)
        # chevron, thin like Segoe MDL2 / Fluent
        d = min(abs((x - 2) - (y - 4)) / 1.414 if 2 <= x <= 6 else 9, abs((10 - x) - (y - 4)) / 1.414 if 6 <= x <= 10 else 9)
        return _rgba(col, max(0.0, min(1.0, .75 - d)) if 3.5 <= y <= 8.5 else 0.0)
    img = tk.PhotoImage(master=master, width=n, height=n)
    back = _hexrgb(T["btn"])
    rows = []
    for yy in range(n):
        row = []
        for xx in range(n):
            accs = [0.0, 0.0, 0.0]
            for sx, sy in ((.25, .25), (.75, .25), (.25, .75), (.75, .75)):
                r, g, b, a = fn(xx + sx, yy + sy)
                for i, c in enumerate((r, g, b)):
                    accs[i] += (c * a + back[i] * (1 - a)) / 4
            row.append("#%02x%02x%02x" % tuple(int(v) for v in accs))
        rows.append("{" + " ".join(row) + "}")
    img.put(" ".join(rows))
    _ICONS[key] = img
    return img


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
        self.title, self.on_close = title, on_close
        self.caption_names = ["min", "max", "close"] if minimizable else ["close"]
        self.cap_hover = self.cap_press = None
        self.cap_images = {}
        self.scale = win.winfo_fpixels("1i") / 96
        self.outer = tk.Frame(win, bg=GRAY, relief="raised", bd=3)
        self.outer._themed_elsewhere = True
        self.outer.pack(fill="both", expand=True)

        bar = tk.Canvas(self.outer, height=22, highlightthickness=0, bg=NAVY)
        bar._themed_elsewhere = True
        self.bar = bar
        bar.pack(fill="x", padx=1, pady=1)
        btns = tk.Frame(bar, bg=GRAY)
        btns._themed_elsewhere = True
        self.tbtns, self.title_btns = btns, []
        holder = bar.create_window(0, 3, window=btns, anchor="ne")
        self.holder = holder

        def paint(e=None):
            width = e.width if e else bar.winfo_width()
            if T.get("cap"):
                paint_caption(self, width)
                return
            bar.delete("grad")
            bar.delete("cap")
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
        self._icon = self.icon_item = None
        try:
            self._icon = tk.PhotoImage(master=win, file=ICON_FILE)
            self.icon_item = bar.create_image(3, 11, image=self._icon, anchor="w")
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
        bar.bind("<ButtonRelease-1>", self._release)
        bar.bind("<Motion>", self._hover)
        bar.bind("<Leave>", lambda e: self._set_hover(None))
        win.bind("<Configure>", lambda e: self._shape() if e.widget is win else None, add="+")
        win.after(10, self._taskbar)

    def restyle(self):
        cap = T.get("cap")
        self.cap_hover = self.cap_press = None
        self.cap_images.clear()
        if cap:
            self.bar.itemconfigure(self.holder, state="hidden")
            self.bar.configure(height=int(T["title_h"] * self.scale), bg=T["title"][0])
            color, width = T["frame"]
            self.outer.configure(bg=T["panel"], relief="flat", bd=0, highlightthickness=int(width * self.scale),
                                 highlightbackground=color, highlightcolor=color)
            self.bar.pack_configure(padx=0, pady=0)
        else:   # Classic 95: exactly as it was built
            self.bar.itemconfigure(self.holder, state="normal")
            self.bar.configure(height=22, bg=NAVY)
            self.outer.configure(bg=GRAY, relief="raised", bd=3, highlightthickness=0)
            self.bar.pack_configure(padx=1, pady=1)
            self.bar.itemconfigure(self.title_text, fill=WHITE, font=FONT_B, anchor="w")
            self.bar.coords(self.title_text, 25, 11)
            if self.icon_item:
                self.bar.coords(self.icon_item, 3, 11)
            for b in self.title_btns:
                b.configure(bg=GRAY, fg=BLACK, activebackground=GRAY, activeforeground=BLACK, relief="raised")
        self._paint()
        self.win.after(70, self._corners)

    # caption buttons drawn on the title bar (modern themes)
    def _cap_at(self, x, y):
        if not T.get("cap"):
            return None
        for n, (x0, y0, x1, y1) in _caption_layout(T["cap"], self.bar.winfo_width(), T["title_h"], self.caption_names, self.scale).items():
            if x0 <= x < x1 and y0 <= y < y1:
                return n
        return None

    def _set_hover(self, n):
        if n == "max":
            n = None   # this window can't be maximized, like a fixed-size Windows app
        if n != self.cap_hover:
            self.cap_hover = n
            if T.get("cap"):
                self._paint()

    def _hover(self, e):
        self._set_hover(self._cap_at(e.x, e.y))

    def _release(self, e):
        n, self.cap_press = self.cap_press, None
        if n and n == self._cap_at(e.x, e.y):
            self._paint()
            (self.minimize if n == "min" else self.on_close)()
        elif n:
            self._paint()

    def _shape(self):
        """Rounded top corners like XP and 7 (a window region); square otherwise."""
        try:
            hwnd = self._hwnd()
            u, g = ctypes.windll.user32, ctypes.windll.gdi32
            r = {"xp": 8, "7": 6}.get(T.get("cap"), 0)
            if r:
                r = int(r * self.scale)
                w, h = self.win.winfo_width(), self.win.winfo_height()
                if (w, h, r) != getattr(self, "_rgn", None):
                    u.SetWindowRgn(hwnd, g.CreateRoundRectRgn(0, 0, w + 1, h + 2 * r, 2 * r, 2 * r), True)
                    self._rgn = (w, h, r)
            elif getattr(self, "_rgn", None):
                u.SetWindowRgn(hwnd, None, True)
                self._rgn = None
        except Exception:
            pass

    def _corners(self):
        """Soft window corners on the themes that have them (Windows 11 only; ignored elsewhere)."""
        try:
            self._shape()
            pref = ctypes.c_int(2 if T.get("cap") == "11" else 1)
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
        n = self._cap_at(e.x, e.y)
        if n and n != "max":
            self.cap_press = n
            self._paint()
            self._drag = None
            return
        self._drag = (e.x_root - self.win.winfo_x(), e.y_root - self.win.winfo_y())

    def _move(self, e):
        if not self._drag:
            return
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
