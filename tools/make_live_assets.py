# -*- coding: utf-8 -*-
"""Generate the extra assets used by the three-column Live TV screen."""

from __future__ import print_function

import os

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "src", "IPTVPlayerPro", "images")

# The Live TV mini TV is drawn by Enigma2's video plane, not by the OSD.
# Cut a transparent hole in the background and in the right panel so the
# video is visible through the 512x300 preview rectangle.  The coordinates
# are (left, top, right, bottom).
VIDEO_BOX = (744, 104, 1256, 404)
RIGHT_PANEL_VIDEO_BOX = (24, 24, 536, 324)


def save(image, name):
    path = os.path.join(OUT, name)
    image.save(path, "PNG")
    print("  ", name, image.size)


def clear_box(image, box):
    """Set the alpha channel to zero without changing the RGB colours."""
    pixels = image.load()
    for y in range(box[1], box[3]):
        for x in range(box[0], box[2]):
            red, green, blue, _alpha = pixels[x, y]
            pixels[x, y] = (red, green, blue, 0)


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
    clear_box(image, VIDEO_BOX)
    save(image, "live_bg.png")


def make_header():
    image = vertical_gradient((1280, 80), (28, 30, 78), (12, 14, 35)).convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw.line([(0, 79), (1280, 79)], fill=(83, 82, 142, 255), width=1)
    draw.rectangle([0, 0, 1280, 2], fill=(81, 68, 147, 255))
    save(image, "live_header.png")


def make_panels():
    # Keep every panel opaque.  The only transparent area must be the video
    # cut-out itself; otherwise the TV service that was playing before the
    # plugin opened bleeds through the OSD as a blurred ghost image.
    save(rounded_panel((300, 640), (10, 13, 34, 255), (54, 57, 103, 255), 0, 0),
         "live_panel_left.png")
    save(rounded_panel((420, 640), (15, 17, 43, 255), (54, 57, 103, 255), 0, 0),
         "live_panel_mid.png")
    right_panel = rounded_panel((560, 640), (12, 14, 38, 255), (54, 57, 103, 255), 0, 0)
    clear_box(right_panel, RIGHT_PANEL_VIDEO_BOX)
    save(right_panel, "live_panel_right.png")
    # The idle placeholder covers the cut-out completely, so the previous
    # channel stays hidden until the user starts a stream in the mini TV.
    # Fill the whole rectangle (including the one-pixel edge) and draw the
    # rounded outline inside it; a transparent rim would let the old video
    # leak through as a thin bright frame.
    preview = Image.new("RGBA", (512, 300), (4, 5, 12, 255))
    ImageDraw.Draw(preview).rounded_rectangle(
        [1, 1, 510, 298], radius=14, outline=(54, 57, 103, 255), width=2)
    save(preview, "live_preview.png")
    save(rounded_panel((430, 42), (20, 23, 57, 255), (100, 98, 173, 255), 21, 2),
         "live_search.png")
    save(rounded_panel((230, 48), (75, 64, 139, 255), (139, 124, 205, 255), 9, 2),
         "live_button.png")
    save(rounded_panel((266, 48), (57, 49, 110, 255), (118, 108, 177, 255), 9, 2),
         "live_button_dark.png")


def make_player_assets():
    """Assets for the full-screen Live TV player and its information bar."""
    top = vertical_gradient((1280, 70), (30, 33, 88), (10, 12, 32)).convert("RGBA")
    draw = ImageDraw.Draw(top)
    draw.rectangle([0, 0, 1279, 1], fill=(65, 59, 127, 255))
    draw.line([(0, 68), (1279, 68)], fill=(91, 89, 150, 255), width=2)
    save(top, "player_top.png")

    bottom = vertical_gradient((1280, 200), (12, 14, 36), (3, 4, 10)).convert("RGBA")
    draw = ImageDraw.Draw(bottom)
    draw.rectangle([0, 0, 1279, 1], fill=(88, 84, 148, 255))
    draw.line([(0, 136), (1279, 136)], fill=(172, 170, 214, 255), width=1)
    save(bottom, "player_bottom.png")

    live = Image.new("RGBA", (72, 30), (0, 0, 0, 0))
    ImageDraw.Draw(live).rounded_rectangle(
        [0, 0, 71, 29], radius=6, fill=(207, 22, 52, 255),
        outline=(255, 122, 142, 255), width=1)
    save(live, "player_live.png")

    save(rounded_panel((104, 104), (18, 20, 42, 255),
                       (70, 72, 130, 255), 12, 2),
         "player_logo_bg.png")


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    make_background()
    make_header()
    make_panels()
    make_player_assets()
    print("Live screen assets generated.")


if __name__ == "__main__":
    main()
