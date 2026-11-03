"""Builds the RetroGrab icons from assets/logo_source.png.

- Removes the flat background (flood fill from the edges; the logo's black outline stops it)
- Crops to the logo, pads to a square
Outputs (in assets/):
    logo.png          512x512 transparent - README / GitHub
    retrograb.ico     16..256 px          - the .exe, shortcuts, taskbar
    titlebar.png      small               - the in-app title bar
"""
import os
from collections import deque

from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
SRC = os.path.join(ASSETS, "logo_source.png")
TOLERANCE = 38  # how far from the background colour still counts as background


def remove_background(img):
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()
    corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    bg = tuple(sum(c[i] for c in corners) // 4 for i in range(3))

    def is_bg(p):
        return sum(abs(p[i] - bg[i]) for i in range(3)) <= TOLERANCE

    mask = Image.new("L", (w, h), 255)
    m = mask.load()
    seen = bytearray(w * h)
    q = deque()
    for x in range(w):
        q.extend(((x, 0), (x, h - 1)))
    for y in range(h):
        q.extend(((0, y), (w - 1, y)))
    while q:
        x, y = q.popleft()
        i = y * w + x
        if seen[i]:
            continue
        seen[i] = 1
        if not is_bg(px[x, y]):
            continue
        m[x, y] = 0
        if x > 0: q.append((x - 1, y))
        if x < w - 1: q.append((x + 1, y))
        if y > 0: q.append((x, y - 1))
        if y < h - 1: q.append((x, y + 1))
    # soften the cut edge slightly so it doesn't look jagged when scaled
    mask = mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    img.putalpha(mask)
    return img


def square_crop(img, pad_ratio=0.03):
    box = img.getchannel("A").point(lambda a: 255 if a > 40 else 0).getbbox()
    img = img.crop(box)
    side = int(max(img.size) * (1 + 2 * pad_ratio))
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(img, ((side - img.width) // 2, (side - img.height) // 2), img)
    return canvas


def main():
    logo = square_crop(remove_background(Image.open(SRC)))
    logo.resize((512, 512), Image.LANCZOS).save(os.path.join(ASSETS, "logo.png"), optimize=True)
    big = logo.resize((256, 256), Image.LANCZOS)
    big.save(os.path.join(ASSETS, "retrograb.ico"),
             sizes=[(16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48), (64, 64), (128, 128), (256, 256)])
    logo.resize((18, 18), Image.LANCZOS).save(os.path.join(ASSETS, "titlebar.png"))
    old = os.path.join(ASSETS, "retrograb.png")
    if os.path.exists(old):
        os.remove(old)
    print("icons written to", ASSETS)


if __name__ == "__main__":
    main()
