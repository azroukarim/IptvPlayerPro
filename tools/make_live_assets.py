# -*- coding: utf-8 -*-
"""Generate the extra assets used by the three-column Live TV screen."""

from __future__ import print_function

import os

from PIL import Image, ImageDraw

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


def gradient_panel(size, top, bottom, outline, width=1):
    """A main-menu style red gradient with a thin edge."""
    image = vertical_gradient(size, top, bottom).convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, size[0] - 1, size[1] - 1],
                   outline=outline, width=width)
    return image


def make_background():
    # Reuse the main-menu background so both screens share the same
    # near-black base and red glow.  Only the mini-TV cut-out differs.
    base_path = os.path.join(OUT, "bg.png")
    if os.path.isfile(base_path):
        image = Image.open(base_path).convert("RGBA")
        if image.size != (1280, 720):
            image = image.resize((1280, 720), Image.LANCZOS)
    else:
        image = vertical_gradient((1280, 720), (10, 10, 17),
                                  (47, 10, 16)).convert("RGBA")
    clear_box(image, VIDEO_BOX)
    save(image, "live_bg.png")


def make_header():
    image = vertical_gradient((1280, 80), (38, 12, 16), (12, 7, 9)).convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw.line([(0, 79), (1280, 79)], fill=(120, 24, 30, 255), width=1)
    draw.rectangle([0, 0, 1280, 2], fill=(150, 30, 38, 255))
    save(image, "live_header.png")


def make_panels():
    # Keep every panel opaque.  The only transparent area must be the video
    # cut-out itself; otherwise the TV service that was playing before the
    # plugin opened bleeds through the OSD as a blurred ghost image.
    border = (92, 13, 13, 255)
    save(gradient_panel((300, 640), (55, 8, 10), (26, 5, 6), border, 1),
         "live_panel_left.png")
    save(gradient_panel((420, 640), (62, 9, 12), (30, 6, 8), border, 1),
         "live_panel_mid.png")
    right_panel = gradient_panel((560, 640), (52, 8, 10), (24, 5, 6), border, 1)
    clear_box(right_panel, RIGHT_PANEL_VIDEO_BOX)
    save(right_panel, "live_panel_right.png")
    # The idle placeholder covers the cut-out completely, so the previous
    # channel stays hidden until the user starts a stream in the mini TV.
    # Fill the whole rectangle (including the one-pixel edge) and draw the
    # rounded outline inside it; a transparent rim would let the old video
    # leak through as a thin bright frame.
    preview = Image.new("RGBA", (512, 300), (8, 4, 6, 255))
    ImageDraw.Draw(preview).rounded_rectangle(
        [1, 1, 510, 298], radius=14, outline=(110, 22, 28, 255), width=2)
    save(preview, "live_preview.png")
    save(rounded_panel((200, 44), (30, 10, 13, 255), (150, 32, 40, 255), 22, 2),
         "live_search.png")
    save(rounded_panel((230, 48), (120, 16, 16, 255), (245, 245, 245, 255), 9, 2),
         "live_button.png")
    save(rounded_panel((266, 48), (74, 9, 9, 255), (140, 30, 36, 255), 9, 2),
         "live_button_dark.png")


def make_search_icon():
    """A small anti-aliased magnifier for the compact Live TV search pill."""
    scale = 4
    size = 24
    image = Image.new("RGBA", (size * scale, size * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    colour = (240, 218, 218, 255)
    draw.ellipse([4 * scale, 4 * scale, 17 * scale, 17 * scale],
                 outline=colour, width=2 * scale)
    draw.line([(16 * scale, 16 * scale), (21 * scale, 21 * scale)],
              fill=colour, width=3 * scale)
    cap = int(1.5 * scale)
    for x, y in ((16, 16), (21, 21)):
        draw.ellipse([x * scale - cap, y * scale - cap,
                      x * scale + cap, y * scale + cap], fill=colour)
    image = image.resize((size, size), Image.LANCZOS)
    save(image, "live_search_icon.png")


def make_player_assets():
    """Assets for the full-screen Live TV player and its information bar."""
    top = vertical_gradient((1280, 70), (38, 12, 16), (12, 7, 9)).convert("RGBA")
    draw = ImageDraw.Draw(top)
    draw.rectangle([0, 0, 1279, 1], fill=(150, 30, 38, 255))
    draw.line([(0, 68), (1279, 68)], fill=(120, 24, 30, 255), width=2)
    save(top, "player_top.png")

    bottom = vertical_gradient((1280, 200), (18, 8, 10), (4, 2, 3)).convert("RGBA")
    draw = ImageDraw.Draw(bottom)
    draw.rectangle([0, 0, 1279, 1], fill=(120, 24, 30, 255))
    draw.line([(0, 136), (1279, 136)], fill=(150, 60, 64, 255), width=1)
    save(bottom, "player_bottom.png")

    live = Image.new("RGBA", (72, 30), (0, 0, 0, 0))
    ImageDraw.Draw(live).rounded_rectangle(
        [0, 0, 71, 29], radius=6, fill=(207, 22, 52, 255),
        outline=(255, 122, 142, 255), width=1)
    save(live, "player_live.png")

    save(rounded_panel((104, 104), (20, 9, 12, 255),
                       (92, 20, 26, 255), 12, 2),
         "player_logo_bg.png")


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    make_background()
    make_header()
    make_panels()
    make_search_icon()
    make_player_assets()
    print("Live screen assets generated.")


if __name__ == "__main__":
    main()
