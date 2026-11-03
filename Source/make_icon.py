"""Draws the RetroGrab pixel-art icon (monitor + yellow download arrow) -> assets/retrograb.ico"""
import os

from PIL import Image

ART = [
    "................................",
    "................................",
    "..KKKKKKKKKKKKKKKKKKKKKKKKKKKK..",
    "..KWWWWWWWWWWWWWWWWWWWWWWWWWGK..",
    "..KWGGGGGGGGGGGGGGGGGGGGGGGGDK..",
    "..KWGDDDDDDDDDDDDDDDDDDDDDDWGDK.",
    "..KWGDTTTTTTTTTTTTTTTTTTTTWGDK..",
    "..KWGDTTTTTTTTTYYYYTTTTTTTWGDK..",
    "..KWGDTTTTTTTTTYYYYTTTTTTTWGDK..",
    "..KWGDTTTTTTTTTYYYYTTTTTTTWGDK..",
    "..KWGDTTTTTTTTTYYYYTTTTTTTWGDK..",
    "..KWGDTTTTTTTTTYYYYTTTTTTTWGDK..",
    "..KWGDTTTTTTTYYYYYYYYTTTTTWGDK..",
    "..KWGDTTTTTTTTYYYYYYTTTTTTWGDK..",
    "..KWGDTTTTTTTTTYYYYTTTTTTTWGDK..",
    "..KWGDTTTTTTTTTTYYTTTTTTTTWGDK..",
    "..KWGDTTTTTTTTTTTTTTTTTTTTWGDK..",
    "..KWGDTTTTTTYYYYYYYYYYTTTTWGDK..",
    "..KWGDTTTTTTTTTTTTTTTTTTTTWGDK..",
    "..KWGDWWWWWWWWWWWWWWWWWWWWWGDK..",
    "..KWGGGGGGGGGGGGGGGGGGGGGGGGDK..",
    "..KWGGGGGGGGGGGGGGGGGGGRRGGGDK..",
    "..KDDDDDDDDDDDDDDDDDDDDDDDDDDK..",
    "..KKKKKKKKKKKKKKKKKKKKKKKKKKKK..",
    "...........KGGGGGGGGK...........",
    "...........KDDDDDDDDK...........",
    "......KKKKKKKKKKKKKKKKKKKK......",
    "......KWWWWWWWWWWWWWWWWWWK......",
    "......KGGGGGGGGGGGGGGGGGDK......",
    "......KKKKKKKKKKKKKKKKKKKK......",
    "................................",
    "................................",
]
COLORS = {".": (0, 0, 0, 0), "K": (0, 0, 0, 255), "W": (255, 255, 255, 255), "G": (192, 192, 192, 255),
          "D": (128, 128, 128, 255), "T": (0, 128, 128, 255), "Y": (255, 255, 0, 255), "R": (0, 200, 0, 255)}

img = Image.new("RGBA", (32, 32))
for y, row in enumerate(ART):
    for x, ch in enumerate(row[:32]):
        img.putpixel((x, y), COLORS[ch])
big = img.resize((256, 256), Image.NEAREST)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "retrograb.ico")
os.makedirs(os.path.dirname(out), exist_ok=True)
big.save(out, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
big.save(out.replace(".ico", ".png"))
print("wrote", out)
