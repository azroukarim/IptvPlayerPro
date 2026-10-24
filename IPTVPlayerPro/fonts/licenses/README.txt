Bundled Fonts
=============

The following fonts are distributed under the SIL Open Font License 1.1.
The full license text for each family is included next to this file.

- Cairo
- Changa
- El Messiri
- Lemonada
- Tajawal
- Almarai

Source: https://github.com/google/fonts/tree/main/ofl

Cairo, Changa, El Messiri and Lemonada are static Regular instances
generated from the official Google Fonts variable fonts at weight 400.
Tajawal and Almarai are the official static Regular files.

Enigma2's Arabic shaper uses Unicode presentation forms.  The modern
Google fonts keep the base Arabic glyphs in cmap and build joined shapes
with GSUB, so the missing isolated presentation forms were mapped to their
corresponding base glyphs.  This keeps standalone and non-joining Arabic
letters rendering correctly on the receiver.

DejaVu Sans
-----------
DejaVuSans.ttf and DejaVuSans-Bold.ttf are DejaVu Sans 2.37.

License: Bitstream Vera Fonts Copyright (see DejaVu-LICENSE.txt).
Source: https://github.com/dejavu-fonts/dejavu-fonts

DejaVu Sans provides both Arabic and Latin glyphs, including the Arabic
presentation forms required by Enigma2's legacy shaper.  The Regular and
Bold faces are registered as separate Enigma2 aliases so headings can use
the bold face while values use the regular face.

The beIN Normal and Premier League fonts in the parent directory are
provided separately and are not part of this license collection.
