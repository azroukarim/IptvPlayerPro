# -*- coding: utf-8 -*-
"""Quick layout preview of the main menu (build time only)."""

import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "src", "IPTVPlayerPro", "images")


def load(name):
    return Image.open(os.path.join(IMG, name)).convert("RGBA")


def main():
    canvas = Image.new("RGBA", (1280, 720))
    canvas.alpha_composite(load("bg.png").resize((1280, 720), Image.LANCZOS))
    canvas.alpha_composite(load("logo.png").resize((320, 118), Image.LANCZOS), (480, 10))

    tiles = [
        (0, "big", (60, 250, 300, 300), (140, 286, 140, 140), "live.png", (60, 448, 300, 58), "Live TV", 30),
        (1, "small", (390, 230, 200, 140), (462, 246, 56, 56), "movies.png", (390, 320, 200, 36), "Movies", 22),
        (2, "small", (610, 230, 200, 140), (682, 246, 56, 56), "series.png", (610, 320, 200, 36), "Series", 22),
        (3, "small", (390, 390, 200, 140), (462, 406, 56, 56), "account.png", (390, 480, 200, 36), "Account", 22),
        (4, "small", (610, 390, 200, 140), (682, 406, 56, 56), "server.png", (610, 480, 200, 36), "Change Server", 22),
        (5, "wide", (850, 230, 370, 70), (868, 246, 38, 38), "settings.png", (920, 230, 280, 70), "Settings", 24),
        (6, "wide", (850, 330, 370, 70), (868, 346, 38, 38), "reload.png", (920, 330, 280, 70), "Reload Portal", 24),
        (7, "wide", (850, 430, 370, 70), (868, 446, 38, 38), "exit.png", (920, 430, 280, 70), "Exit", 24),
    ]
    font_path = "C:/Windows/Fonts/arial.ttf"
    for index, card, tpos, ipos, icon, lpos, label, size in tiles:
        focused = index == 0
        name = "card_{0}{1}.png".format(card, "_f" if focused else "")
        canvas.alpha_composite(load(name).resize((tpos[2], tpos[3]), Image.LANCZOS), (tpos[0], tpos[1]))
        canvas.alpha_composite(load(icon).resize((ipos[2], ipos[3]), Image.LANCZOS), (ipos[0], ipos[1]))
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.truetype(font_path, size)
        if card == "wide":
            draw.text((lpos[0], lpos[1] + lpos[3] / 2), label, font=font,
                      fill=(255, 255, 255, 255), anchor="lm")
        else:
            draw.text((lpos[0] + lpos[2] / 2, lpos[1] + lpos[3] / 2), label, font=font,
                      fill=(255, 255, 255, 255), anchor="mm")
    draw = ImageDraw.Draw(canvas)
    status = ImageFont.truetype(font_path, 19)
    small = ImageFont.truetype(font_path, 16)
    draw.text((1234, 60), "Current Playlist: My Portal", font=status, fill=(210, 210, 210, 255), anchor="rm")
    draw.text((1234, 87), "Expires: 2027-01-01", font=small, fill=(163, 124, 124, 255), anchor="rm")
    hint = ImageFont.truetype(font_path, 17)
    draw.text((640, 665), "OK select  -  MENU servers  -  BACK exit", font=hint,
              fill=(143, 143, 143, 255), anchor="mm")
    out = os.path.join(ROOT, "docs", "main_menu_preview.png")
    if not os.path.isdir(os.path.dirname(out)):
        os.makedirs(os.path.dirname(out))
    canvas.convert("RGB").save(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
