# -*- coding: utf-8 -*-
"""Generate the extra assets used by the three-column Live TV screen."""

from __future__ import print_function

import os

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "src", "IPTVPlayerPro", "images")


def save(image, name):
    path = os.path.join(OUT, name)
    image.save(path, "PNG")
    print("  ", name, image.size)


def vertical_gradient(size, top, bottom):
    width, height = size
    image = Image.new("RGB", size)
    draw = ImageDraw.Draw(image)
    for y in range(height):
        ratio = float(y) / max(1, height - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3))
        draw.line([(0, y), (width, y)], fill=color)
    return image


def rounded_panel(size, fill, outline, radius=14, width=2):
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle([1, 1, size[0] - 2, size[1] - 2], radius=radius,
                           fill=fill, outline=outline, width=width)
    return image


def make_background():
    image = vertical_gradient((1280, 720), (9, 11, 30), (47, 10, 42)).convert("RGBA")

    def glow(box, color, blur, alpha):
        mask = Image.new("L", (1280, 720), 0)
        ImageDraw.Draw(mask).ellipse(box, fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(blur)).point(
            lambda value: int(value * alpha))
        layer = Image.new("RGBA", (1280, 720), color + (255,))
        return Image.composite(layer, image, mask)

    image = glow([-260, 80, 700, 760], (65, 47, 143), 150, 0.55)
    image = glow([620, -180, 1500, 560], (24, 26, 88), 180, 0.45)
    image = glow([520, 380, 1380, 880], (126, 20, 76), 170, 0.40)
    image = glow([200, 500, 1100, 900], (77, 21, 66), 120, 0.28)

    # A subtle vignette keeps the list text readable.
    vignette = Image.radial_gradient("L").resize((1280, 720))
    dark = Image.new("RGBA", (1280, 720), (0, 0, 0, 255))
    mask = vignette.point(lambda value: int(value * 0.32))
    image = Image.composite(dark, image, mask)
    save(image, "live_bg.png")


def make_header():
    image = vertical_gradient((1280, 80), (28, 30, 78), (12, 14, 35)).convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw.line([(0, 79), (1280, 79)], fill=(83, 82, 142, 255), width=1)
    draw.rectangle([0, 0, 1280, 2], fill=(81, 68, 147, 190))
    save(image, "live_header.png")


def make_panels():
    save(rounded_panel((300, 640), (10, 13, 34, 228), (54, 57, 103, 255), 0, 0),
         "live_panel_left.png")
    save(rounded_panel((420, 640), (15, 17, 43, 224), (54, 57, 103, 255), 0, 0),
         "live_panel_mid.png")
    save(rounded_panel((560, 640), (12, 14, 38, 232), (54, 57, 103, 255), 0, 0),
         "live_panel_right.png")
    save(rounded_panel((512, 300), (4, 5, 12, 245), (54, 57, 103, 255), 14, 2),
         "live_preview.png")
    save(rounded_panel((430, 42), (20, 23, 57, 235), (100, 98, 173, 255), 21, 2),
         "live_search.png")
    save(rounded_panel((230, 48), (75, 64, 139, 245), (139, 124, 205, 255), 9, 2),
         "live_button.png")
    save(rounded_panel((266, 48), (57, 49, 110, 235), (118, 108, 177, 255), 9, 2),
         "live_button_dark.png")


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    make_background()
    make_header()
    make_panels()
    print("Live screen assets generated.")


if __name__ == "__main__":
    main()
