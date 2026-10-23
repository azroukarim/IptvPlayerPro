# -*- coding: utf-8 -*-
"""Generate all PNG assets for IPTV Player Pro (build time only).

Requires Pillow:  pip install pillow
"""

from __future__ import print_function

import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "src", "IPTVPlayerPro", "images")

WHITE = (245, 245, 245, 255)
RED = (228, 32, 32, 255)
GOLD = (255, 200, 70, 255)

FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"
FONT_REGULAR = "C:/Windows/Fonts/arial.ttf"


def ensure():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)


def font(size, bold=True):
    path = FONT_BOLD if bold else FONT_REGULAR
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def downsample(img, size):
    return img.resize(size, Image.LANCZOS)


def new(w, h, scale=4):
    return Image.new("RGBA", (w * scale, h * scale), (0, 0, 0, 0)), scale


def save(img, name):
    path = os.path.join(OUT, name)
    img.save(path, "PNG")
    print("  ", name, img.size)


# --------------------------------------------------------------------- shapes
def line(draw, points, color, width, scale):
    points = [(x * scale, y * scale) for x, y in points]
    draw.line(points, fill=color, width=int(width * scale), joint="curve")


def rounded(draw, box, radius, outline=None, width=0, fill=None, scale=1):
    box = [int(value * scale) for value in box]
    draw.rounded_rectangle(box, radius=int(radius * scale), outline=outline,
                           width=int(width * scale), fill=fill)


def ellipse(draw, box, color=None, width=0, fill=None, scale=1):
    box = [int(value * scale) for value in box]
    draw.ellipse(box, outline=color, width=int(width * scale), fill=fill)


def polygon(draw, points, fill, scale):
    draw.polygon([(x * scale, y * scale) for x, y in points], fill=fill)


def play_triangle(draw, cx, cy, size, color, scale):
    polygon(draw, [(cx - size * 0.36, cy - size * 0.5), (cx + size * 0.55, cy),
                   (cx - size * 0.36, cy + size * 0.5)], color, scale)


def arc(draw, box, start, end, color, width, scale):
    box = [int(v * scale) for v in box]
    draw.arc(box, start=start, end=end, fill=color, width=int(width * scale))


# ---------------------------------------------------------------------- icons
def icon_live():
    img, s = new(280, 280)
    d = ImageDraw.Draw(img)
    rounded(d, (28, 74, 252, 246), 28, outline=WHITE, width=11, scale=s)
    rounded(d, (96, 130, 184, 196), 12, outline=WHITE, width=8, scale=s)
    play_triangle(d, 148, 163, 46, WHITE, s)
    line(d, [(92, 78), (140, 22)], WHITE, 11, s)
    line(d, [(188, 78), (140, 22)], WHITE, 11, s)
    return downsample(img, (140, 140))


def icon_movies():
    img, s = new(120, 120)
    d = ImageDraw.Draw(img)
    ellipse(d, (10, 10, 110, 110), color=WHITE, width=9, scale=s)
    play_triangle(d, 62, 60, 44, WHITE, s)
    return downsample(img, (56, 56))


def icon_series():
    img, s = new(120, 120)
    d = ImageDraw.Draw(img)
    rounded(d, (10, 44, 110, 104), 8, outline=WHITE, width=8, scale=s)
    line(d, [(10, 62), (110, 62)], WHITE, 6, s)
    line(d, [(18, 44), (40, 14)], WHITE, 7, s)
    line(d, [(50, 44), (72, 14)], WHITE, 7, s)
    line(d, [(82, 44), (104, 14)], WHITE, 7, s)
    return downsample(img, (56, 56))


def icon_account():
    img, s = new(120, 120)
    d = ImageDraw.Draw(img)
    ellipse(d, (18, 12, 54, 48), color=WHITE, width=7, scale=s)
    ellipse(d, (66, 20, 96, 50), color=WHITE, width=6, scale=s)
    arc(d, (6, 46, 66, 116), 180, 360, WHITE, 7, s)
    arc(d, (58, 56, 108, 112), 180, 360, WHITE, 6, s)
    return downsample(img, (56, 56))


def icon_server():
    img, s = new(120, 120)
    d = ImageDraw.Draw(img)
    ellipse(d, (14, 42, 40, 68), color=WHITE, width=5, scale=s)
    arc(d, (6, 68, 46, 112), 180, 360, WHITE, 5, s)
    ellipse(d, (80, 42, 106, 68), color=WHITE, width=5, scale=s)
    arc(d, (74, 68, 114, 112), 180, 360, WHITE, 5, s)
    # arrows between the two people
    line(d, [(44, 30), (76, 30)], WHITE, 5, s)
    line(d, [(68, 24), (78, 30), (68, 36)], WHITE, 5, s)
    line(d, [(76, 92), (44, 92)], WHITE, 5, s)
    line(d, [(52, 86), (42, 92), (52, 98)], WHITE, 5, s)
    return downsample(img, (56, 56))


def icon_settings():
    img, s = new(76, 76)
    d = ImageDraw.Draw(img)
    cx = cy = 38
    # gear body
    d.ellipse([int((cx - 16) * s), int((cy - 16) * s), int((cx + 16) * s), int((cy + 16) * s)],
              outline=WHITE, width=int(5 * s))
    d.ellipse([int((cx - 6) * s), int((cy - 6) * s), int((cx + 6) * s), int((cy + 6) * s)],
              outline=WHITE, width=int(4 * s))
    for index in range(8):
        angle = index * math.pi / 4
        x1 = cx + math.cos(angle) * 16
        y1 = cy + math.sin(angle) * 16
        x2 = cx + math.cos(angle) * 23
        y2 = cy + math.sin(angle) * 23
        line(d, [(x1, y1), (x2, y2)], WHITE, 6, s)
    return downsample(img, (38, 38))


def icon_reload():
    img, s = new(76, 76)
    d = ImageDraw.Draw(img)
    arc(d, (12, 12, 64, 64), 40, 320, WHITE, 6, s)
    polygon(d, [(60, 12), (68, 26), (52, 28)], WHITE, s)
    return downsample(img, (38, 38))


def icon_exit():
    img, s = new(76, 76)
    d = ImageDraw.Draw(img)
    line(d, [(16, 12), (40, 12), (40, 64), (16, 64), (16, 12)], WHITE, 5, s)
    line(d, [(44, 38), (66, 38)], WHITE, 5, s)
    polygon(d, [(58, 30), (70, 38), (58, 46)], WHITE, s)
    return downsample(img, (38, 38))


def icon_channel():
    img, s = new(88, 88)
    d = ImageDraw.Draw(img)
    rounded(d, (10, 20, 78, 72), 12, outline=WHITE, width=5, scale=s)
    play_triangle(d, 47, 46, 24, WHITE, s)
    line(d, [(28, 20), (48, 4)], WHITE, 4, s)
    line(d, [(60, 20), (48, 4)], WHITE, 4, s)
    return downsample(img, (56, 56))


def icon_folder():
    img, s = new(88, 88)
    d = ImageDraw.Draw(img)
    rounded(d, (8, 24, 80, 74), 7, outline=WHITE, width=5, scale=s)
    line(d, [(8, 34), (40, 34), (48, 24), (80, 24)], WHITE, 5, s)
    return downsample(img, (56, 56))


def icon_star():
    img, s = new(88, 88)
    d = ImageDraw.Draw(img)
    points = []
    for index in range(10):
        angle = -math.pi / 2 + index * math.pi / 5
        radius = 38 if index % 2 == 0 else 16
        points.append((44 + math.cos(angle) * radius, 44 + math.sin(angle) * radius))
    polygon(d, points, GOLD, s)
    return downsample(img, (56, 56))


def icon_movie_card():
    img, s = new(92, 132)
    d = ImageDraw.Draw(img)
    rounded(d, (6, 6, 86, 126), 8, outline=WHITE, width=5, scale=s)
    for y in (22, 44, 88, 110):
        rounded(d, (14, y, 24, y + 8), 2, fill=WHITE, scale=s)
        rounded(d, (68, y, 78, y + 8), 2, fill=WHITE, scale=s)
    play_triangle(d, 50, 66, 28, WHITE, s)
    return downsample(img, (46, 66))


def icon_series_card():
    img, s = new(92, 132)
    d = ImageDraw.Draw(img)
    rounded(d, (6, 34, 86, 126), 8, outline=WHITE, width=5, scale=s)
    line(d, [(6, 54), (86, 54)], WHITE, 4, s)
    line(d, [(16, 34), (30, 10)], WHITE, 5, s)
    line(d, [(40, 34), (54, 10)], WHITE, 5, s)
    line(d, [(64, 34), (78, 10)], WHITE, 5, s)
    play_triangle(d, 48, 88, 26, WHITE, s)
    return downsample(img, (46, 66))


def icon_doc():
    img, s = new(88, 88)
    d = ImageDraw.Draw(img)
    rounded(d, (16, 8, 72, 80), 6, outline=WHITE, width=5, scale=s)
    for y in (30, 44, 58):
        line(d, [(26, y), (62, y)], WHITE, 4, s)
    play_triangle(d, 62, 66, 18, WHITE, s)
    return downsample(img, (56, 56))


def icon_mag_box():
    img, s = new(92, 92)
    d = ImageDraw.Draw(img)
    rounded(d, (8, 26, 84, 82), 8, outline=WHITE, width=5, scale=s)
    line(d, [(8, 40), (84, 40)], WHITE, 4, s)
    line(d, [(46, 18), (46, 8)], WHITE, 4, s)
    arc(d, (32, 2, 60, 24), 180, 360, WHITE, 4, s)
    play_triangle(d, 48, 64, 20, WHITE, s)
    return downsample(img, (56, 56))


def icon_more():
    img, s = new(76, 76)
    d = ImageDraw.Draw(img)
    for cx in (20, 38, 56):
        ellipse(d, (cx - 6, 32, cx + 6, 44), fill=WHITE, scale=s)
    return downsample(img, (38, 38))


def icon_episode():
    img, s = new(88, 88)
    d = ImageDraw.Draw(img)
    ellipse(d, (12, 12, 76, 76), color=WHITE, width=5, scale=s)
    play_triangle(d, 47, 44, 26, WHITE, s)
    return downsample(img, (56, 56))


# --------------------------------------------------------------------- cards
def gradient_card(width, height, top, bottom, border, border_width, radius=16):
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    grad = Image.new("RGBA", (1, height))
    for y in range(height):
        ratio = float(y) / max(1, height - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3)) + (255,)
        grad.putpixel((0, y), color)
    grad = grad.resize((width, height))
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, width - 1, height - 1], radius=radius, fill=255)
    img.paste(grad, (0, 0), mask)
    draw = ImageDraw.Draw(img)
    if border and border_width:
        draw.rounded_rectangle([border_width // 2, border_width // 2, width - 1 - border_width // 2, height - 1 - border_width // 2],
                               radius=radius, outline=border, width=border_width)
    return img


def make_cards():
    # Native display sizes: ePixmap widgets do not scale by default.
    sizes = {"big": (300, 300), "small": (200, 140), "wide": (370, 70)}
    for name, (w, h) in sizes.items():
        save(gradient_card(w, h, (92, 13, 13), (58, 7, 7), (42, 4, 4, 255), 2, radius=8),
             "card_{0}.png".format(name))
        save(gradient_card(w, h, (146, 22, 22), (96, 12, 12), (255, 255, 255, 255), 4, radius=8),
             "card_{0}_f.png".format(name))


# ---------------------------------------------------------------- background
def make_background():
    width, height = 1280, 720
    base = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(base)
    for y in range(height):
        ratio = float(y) / (height - 1)
        color = (int(13 + 3 * ratio), int(13 + 2 * ratio), int(22 + 4 * ratio))
        draw.line([(0, y), (width, y)], fill=color)
    # soft red glow behind the tiles (no visible rectangle edges)
    glow = Image.new("L", (width, height), 0)
    ImageDraw.Draw(glow).ellipse([240, 27, 1307, 773], fill=255)
    glow = glow.filter(ImageFilter.GaussianBlur(173))
    glow = glow.point(lambda value: int(value * 0.42))
    red_layer = Image.new("RGB", (width, height), (128, 10, 10))
    base = Image.composite(red_layer, base, glow)
    # gentle vignette
    vignette = Image.radial_gradient("L").resize((width, height))
    dark = Image.new("RGB", (width, height), (0, 0, 0))
    mask = vignette.point(lambda value: int(value * 0.25))
    base = Image.composite(dark, base, mask)
    base = base.filter(ImageFilter.GaussianBlur(0.5))
    save(base.convert("RGBA"), "bg.png")


def make_logo():
    img = Image.new("RGBA", (640, 236), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # play emblem
    triangle = [(28, 40), (190, 118), (28, 196)]
    draw.polygon(triangle, fill=(200, 20, 20, 255))
    draw.line(triangle + [triangle[0]], fill=(255, 90, 90, 255), width=6, joint="curve")
    draw.polygon([(78, 88), (140, 118), (78, 148)], fill=(255, 255, 255, 255))
    # word mark
    draw.text((214, 26), "IPTV", font=font(112, True), fill=(255, 255, 255, 255))
    draw.text((226, 152), "P R O", font=font(48, True), fill=(255, 70, 70, 255))
    # Native display size (2x render downsampled).
    save(downsample(img, (320, 118)), "logo.png")
    save(downsample(img, (160, 59)), "logo_small.png")


def make_loading_assets():
    """Top-right loading panel and 5% progress-bar frames."""
    panel = Image.new("RGBA", (440, 104), (0, 0, 0, 0))
    draw = ImageDraw.Draw(panel)
    draw.rounded_rectangle([0, 0, 439, 103], radius=12,
                           fill=(18, 5, 7, 242), outline=(150, 30, 30, 255),
                           width=2)
    draw.rounded_rectangle([12, 4, 428, 6], radius=1,
                           fill=(220, 50, 50, 255))
    save(panel, "loading_panel.png")

    width, height = 408, 14
    for index in range(21):
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([0, 0, width - 1, height - 1], radius=7,
                               fill=(38, 12, 16, 255),
                               outline=(120, 34, 38, 255), width=1)
        fill_width = int((width - 4) * index / 20.0)
        if fill_width > 0:
            gradient = Image.new("RGBA", (width, height))
            gdraw = ImageDraw.Draw(gradient)
            for x in range(width):
                ratio = float(x) / max(1, width - 1)
                color = (int(180 + 70 * ratio), int(24 + 90 * ratio),
                         int(24 + 30 * ratio), 255)
                gdraw.line([(x, 0), (x, height)], fill=color)
            mask = Image.new("L", (width, height), 0)
            ImageDraw.Draw(mask).rounded_rectangle(
                [1, 1, fill_width, height - 2], radius=6, fill=255)
            img.paste(gradient, (0, 0), mask)
            draw = ImageDraw.Draw(img)
            draw.rounded_rectangle([0, 0, width - 1, height - 1], radius=7,
                                   outline=(150, 40, 42, 255), width=1)
        save(img, "loadbar_{0:02d}.png".format(index))


def make_plugin_icon():
    # PluginBrowser draws this with a 100x40 box and BT_SCALE.
    img = Image.new("RGBA", (200, 80), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([1, 1, 198, 78], radius=12, fill=(96, 12, 12, 255), outline=(220, 40, 40, 255), width=3)
    draw.polygon([(18, 18), (64, 40), (18, 62)], fill=(220, 30, 30, 255))
    draw.polygon([(30, 28), (54, 40), (30, 52)], fill=(255, 255, 255, 255))
    draw.text((78, 8), "IPTV", font=font(36, True), fill=(255, 255, 255, 255))
    draw.text((80, 46), "P R O", font=font(19, True), fill=(255, 70, 70, 255))
    save(img, "plugin.png")
    return img


# ----------------------------------------------------------------------- main
def main():
    ensure()
    print("Generating assets ...")
    save(icon_live(), "live.png")
    save(icon_movies(), "movies.png")
    save(icon_series(), "series.png")
    save(icon_account(), "account.png")
    save(icon_server(), "server.png")
    save(icon_settings(), "settings.png")
    save(icon_reload(), "reload.png")
    save(icon_exit(), "exit.png")
    save(icon_channel(), "channel.png")
    save(icon_folder(), "folder.png")
    save(icon_star(), "star.png")
    save(icon_movie_card(), "movie.png")
    save(icon_series_card(), "series_card.png")
    save(icon_doc(), "m3u.png")
    save(icon_mag_box(), "mag.png")
    save(icon_more(), "more.png")
    save(icon_episode(), "episode.png")
    make_loading_assets()
    make_cards()
    make_background()
    make_logo()
    plugin = make_plugin_icon()
    plugin.save(os.path.join(ROOT, "src", "IPTVPlayerPro", "plugin.png"), "PNG")
    print("Done.")


if __name__ == "__main__":
    main()
