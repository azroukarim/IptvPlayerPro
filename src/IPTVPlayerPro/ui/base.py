# -*- coding: utf-8 -*-
"""Shared UI building blocks for IPTV Player Pro."""

from __future__ import absolute_import

import os
import threading
import time

from enigma import (RT_HALIGN_CENTER, RT_HALIGN_LEFT, RT_HALIGN_RIGHT,
                    RT_VALIGN_CENTER, eListboxPythonMultiContent, ePicLoad,
                    eServiceReference, eTimer, gFont)

try:
    from urllib.parse import quote
except ImportError:  # Python 2
    from urllib import quote

from Components.ActionMap import HelpableActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import (MultiContentEntryPixmapAlphaTest,
                                     MultiContentEntryRectangle,
                                     MultiContentEntryText)
from Components.Pixmap import Pixmap
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.LoadPixmap import LoadPixmap

from ..core.i18n import _
from ..core.net import Http, NetError
from ..core.util import md5, safe_int, stream_url_with_headers, to_text

PLUGIN_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE_PATH = os.path.join(PLUGIN_PATH, "images")
FONT_PATH = os.path.join(PLUGIN_PATH, "fonts")

# Fonts shipped with the plugin.  The key is the value stored in the settings;
# the tuple is (file name, alias registered with Enigma2).
FONT_FILES = {
    "dejavu": ("DejaVuSans.ttf", "IPTVPlayerPro_DejaVu"),
    "bein": ("beIN Normal.ttf", "IPTVPlayerPro_beIN"),
    "premier": ("Premier_League.ttf", "IPTVPlayerPro_Premier"),
    "cairo": ("Cairo-Regular.ttf", "IPTVPlayerPro_Cairo"),
    "tajawal": ("Tajawal-Regular.ttf", "IPTVPlayerPro_Tajawal"),
    "almarai": ("Almarai-Regular.ttf", "IPTVPlayerPro_Almarai"),
    "changa": ("Changa-Regular.ttf", "IPTVPlayerPro_Changa"),
    "elmessiri": ("ElMessiri-Regular.ttf", "IPTVPlayerPro_ElMessiri"),
    "lemonada": ("Lemonada-Regular.ttf", "IPTVPlayerPro_Lemonada"),
}

# Families that ship a real bold face.  Enigma2 selects a font by alias, so
# register the bold file separately and let font() use it for bold text.
FONT_BOLD_FILES = {
    "dejavu": ("DejaVuSans-Bold.ttf", "IPTVPlayerPro_DejaVu_Bold"),
}

# Display order in Settings.  A tuple keeps the order stable on Python 2.
FONT_ORDER = ("dejavu", "bein", "premier", "cairo", "tajawal", "almarai",
              "changa", "elmessiri", "lemonada")

WHITE = "#ffffff"
GREY = "#b8b8b8"
DIM = "#8a8a8a"
RED = "#e0b0b0"
ROW_BG = "#15151f"
ROW_SEL = "#7d0f0f"
ROW_BG_ALT = "#111119"

# Three-column live browser.  Keep the live screen on the same deep-red
# palette as the main menu so the mini TV, lists and panels feel like one UI.
LIVE_ROW_BG = "#1f0d11"
LIVE_ROW_SEL = "#7d0f0f"
LIVE_TEXT = "#ffffff"
LIVE_MUTED = "#c9a7a7"
LIVE_ACCENT = "#f0b34a"

_PIXMAPS = {}
_FONTS = {}
_ACTIVE_FONT = None
_ACTIVE_BOLD_FONT = None
_REGISTERED_FONTS = set()
_REGISTERED_BOLD_FONTS = set()


def image(name):
    return os.path.join(IMAGE_PATH, name)


def pixmap(name, cache=True):
    path = name if os.path.isabs(name) else image(name)
    if cache:
        ptr = _PIXMAPS.get(path)
        if ptr is not None:
            return ptr
        ptr = LoadPixmap(path)
        if ptr is not None:
            _PIXMAPS[path] = ptr
        return ptr
    return LoadPixmap(path)


def _add_font(filename, alias):
    """Register one bundled font face with Enigma2."""
    try:
        from enigma import addFont
    except Exception:
        return False
    path = os.path.join(FONT_PATH, filename)
    if not os.path.isfile(path):
        return False
    try:
        addFont(path, alias, 100, False, 0)
        return True
    except Exception:
        # Older Enigma2 versions expose addFont with four arguments.
        try:
            addFont(path, alias, 100, 0)
            return True
        except Exception:
            return False


def register_fonts():
    """Register the custom fonts bundled with the plugin."""
    if (len(_REGISTERED_FONTS) >= len(FONT_FILES) and
            len(_REGISTERED_BOLD_FONTS) >= len(FONT_BOLD_FILES)):
        return
    for key, (filename, alias) in FONT_FILES.items():
        if key not in _REGISTERED_FONTS and _add_font(filename, alias):
            _REGISTERED_FONTS.add(key)
    for key, (filename, alias) in FONT_BOLD_FILES.items():
        if key not in _REGISTERED_BOLD_FONTS and _add_font(filename, alias):
            _REGISTERED_BOLD_FONTS.add(key)


def set_active_font(key):
    """Select the font used by the plugin's list entries.

    ``key`` is one of the values stored in settings: ``default``, ``dejavu``,
    ``bein``, ``premier`` or one of the additional bundled fonts.  Unknown or
    unavailable fonts fall back to the receiver's default face.
    """
    global _ACTIVE_FONT, _ACTIVE_BOLD_FONT
    if key not in FONT_FILES:
        _ACTIVE_FONT = None
        _ACTIVE_BOLD_FONT = None
        return None
    register_fonts()
    _ACTIVE_FONT = FONT_FILES[key][1] if key in _REGISTERED_FONTS else None
    bold = FONT_BOLD_FILES.get(key)
    _ACTIVE_BOLD_FONT = (bold[1] if bold and key in _REGISTERED_BOLD_FONTS
                         else None)
    return _ACTIVE_FONT


def active_font():
    return _ACTIVE_FONT


def active_bold_font():
    return _ACTIVE_BOLD_FONT


def skin_factor():
    """Return the receiver's skin scale (the screens target 720p)."""
    try:
        from enigma import getDesktop
        return max(0.5, getDesktop(0).size().height() / 720.0)
    except Exception:
        return 1.0


def font(size, bold=False, font_name=None):
    if font_name:
        name = font_name
    elif bold and _ACTIVE_BOLD_FONT:
        name = _ACTIVE_BOLD_FONT
    else:
        name = _ACTIVE_FONT or ("Bold" if bold else "Regular")
    key = (size, name)
    ptr = _FONTS.get(key)
    if ptr is None:
        try:
            ptr = gFont(name, size)
        except Exception:
            ptr = gFont("Regular", size)
        _FONTS[key] = ptr
    return ptr


def set_background(screen, name="bg.png"):
    widget = screen.get("bg")
    if widget is not None:
        widget.instance.setPixmap(pixmap(name))


def set_logo(screen, name="logo_small.png"):
    widget = screen.get("logo")
    if widget is not None:
        widget.instance.setPixmap(pixmap(name))


class MultiList(MenuList):
    """MultiContent list with the three fonts used by the plugin."""

    def __init__(self, item_height=72):
        MenuList.__init__(self, [], False, eListboxPythonMultiContent)
        self.l.setItemHeight(item_height)
        self.apply_fonts()

    def apply_fonts(self):
        self.l.setFont(0, font(22))
        self.l.setFont(1, font(16))
        self.l.setFont(2, font(23, True))
        self.l.setFont(3, font(26, True))


class LiveList(MenuList):
    """Compact list used by the three-column live browser."""

    def __init__(self, item_height=48):
        MenuList.__init__(self, [], False, eListboxPythonMultiContent)
        self.l.setItemHeight(item_height)
        self.apply_fonts()

    def apply_fonts(self):
        self.l.setFont(0, font(20))
        self.l.setFont(1, font(16))
        # Category and channel names use a noticeably larger face so the
        # three-column browser stays readable from a normal viewing distance.
        self.l.setFont(2, font(26, True))
        self.l.setFont(3, font(28, True))
        # Counts and channel numbers are secondary information: a slightly
        # smaller face leaves more room for the actual name.
        self.l.setFont(4, font(16))


def category_entry(width, height, title, value=None):
    """A category row with the count pinned to the far right edge without obscuring text."""
    title = to_text(title)
    value = to_text(value) if value else u""
    entries = [
        MultiContentEntryRectangle(
            pos=(0, 1), size=(width, height - 2),
            backgroundColor=LIVE_ROW_BG, backgroundColorSelected=LIVE_ROW_SEL,
        )
    ]
    value_width = 46 if value else 0
    text_width = width - value_width - 12 if value else width - 12
    entries.append(MultiContentEntryText(
        pos=(8, 0), size=(text_width, height),
        font=2, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
        text=title, color=LIVE_TEXT, color_sel=WHITE,
    ))
    if value:
        val_x = width - value_width - 4
        entries.append(MultiContentEntryText(
            pos=(val_x, 0), size=(value_width, height),
            font=4, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER,
            text=value, color=LIVE_MUTED, color_sel=WHITE,
        ))
    return entries


def channel_entry(width, height, number, title, icon=None, favorite=False,
                  bg=LIVE_ROW_BG, selected_bg=LIVE_ROW_SEL):
    """A numbered channel row with icon, clean title and number pinned to the far right."""
    title = to_text(title)
    number = safe_int(number)
    entries = [
        MultiContentEntryRectangle(
            pos=(0, 1), size=(width, height - 2),
            backgroundColor=bg, backgroundColorSelected=selected_bg,
        )
    ]
    number_text = u"{0}".format(number) if number else u""
    number_width = 44 if number_text else 0
    badge_width = 20 if favorite else 0
    right_space = number_width + badge_width + 12

    icon_x = 8
    icon_w = 32
    if icon is not None:
        entries.append(MultiContentEntryPixmapAlphaTest(
            pos=(icon_x, (height - 32) // 2), size=(icon_w, 32), png=icon,
        ))
    text_x = icon_x + icon_w + 8
    text_w = width - text_x - right_space

    entries.append(MultiContentEntryText(
        pos=(text_x, 0), size=(text_w, height),
        font=2, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
        text=title, color=LIVE_TEXT, color_sel=WHITE,
    ))
    if favorite:
        fav_x = width - number_width - badge_width - 6
        entries.append(MultiContentEntryText(
            pos=(fav_x, 0), size=(badge_width, height),
            font=2, flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER,
            text=u"\u2605", color=LIVE_ACCENT, color_sel=WHITE,
        ))
    if number_text:
        num_x = width - number_width - 6
        entries.append(MultiContentEntryText(
            pos=(num_x, 0), size=(number_width, height),
            font=4, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER,
            text=number_text, color=LIVE_MUTED, color_sel=WHITE,
        ))
    return entries



def row_entry(width, height, title, subtitle=None, icon=None, icon_size=(44, 44),
              value=None, badge=None, selected_bg=ROW_SEL, bg=ROW_BG,
              value_size=16):
    title = to_text(title)
    subtitle = to_text(subtitle) if subtitle else u""
    value = to_text(value) if value else u""
    badge = to_text(badge) if badge else u""
    entries = [
        MultiContentEntryRectangle(
            pos=(0, 1), size=(width, height - 2),
            backgroundColor=bg, backgroundColorSelected=selected_bg,
        )
    ]
    text_x = 14
    if icon is not None:
        icon_w, icon_h = icon_size
        entries.append(MultiContentEntryPixmapAlphaTest(
            pos=(12, (height - icon_h) // 2), size=(icon_w, icon_h), png=icon,
        ))
        text_x = 12 + icon_w + 14
    value_width = 0
    if value:
        char_width = max(11, int(value_size * 0.65))
        value_width = min(360, max(90, len(to_text(value)) * char_width + 24))
        entries.append(MultiContentEntryText(
            pos=(width - value_width - 16, 0), size=(value_width, height),
            font=1, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER,
            text=value, color="#cfcfcf", color_sel="#ffffff",
        ))
    badge_width = 0
    if badge:
        badge_width = 34
        entries.append(MultiContentEntryText(
            pos=(width - value_width - badge_width - 16, 0), size=(badge_width, height),
            font=2, flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER,
            text=badge, color="#ffcc55", color_sel="#ffffff",
        ))
    text_width = width - text_x - value_width - badge_width - 24
    if subtitle:
        entries.append(MultiContentEntryText(
            pos=(text_x, 7), size=(text_width, height - 34),
            font=2, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
            text=title, color=WHITE, color_sel=WHITE,
        ))
        entries.append(MultiContentEntryText(
            pos=(text_x, height - 33), size=(text_width, 26),
            font=1, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
            text=subtitle, color=GREY, color_sel="#f0dada",
        ))
    else:
        entries.append(MultiContentEntryText(
            pos=(text_x, 0), size=(text_width, height),
            font=2, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
            text=title, color=WHITE, color_sel=WHITE,
        ))
    return entries


def label_entry(width, height, text, font_index=2, color=WHITE, align=RT_HALIGN_LEFT):
    return [
        MultiContentEntryText(
            pos=(16, 0), size=(width - 32, height), font=font_index,
            flags=align | RT_VALIGN_CENTER, text=text,
            color=color, color_sel=color,
        )
    ]


class AsyncScreen(Screen):
    """Screen with a tiny helper to run blocking work in a thread.

    Enigma2 screens inherit from ``dict``.  Never assign attributes such as
    ``items``, ``keys`` or ``values`` on a screen: they hide the inherited
    ``dict`` methods, and ``Screen.doClose()`` calls ``self.items()`` while
    deleting the GUI.  Use a distinct name like ``browser_items`` instead.
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self._alive = True
        self._timers = []
        self.onClose.append(self._async_cleanup)

    def _async_cleanup(self):
        self._alive = False
        for timer in self._timers:
            try:
                timer.stop()
            except Exception:
                pass
        self._timers = []

    def run_async(self, fn, on_done, on_error=None, timeout=None, on_wait=None):
        """Run *fn* in a worker thread and deliver the result on the UI thread.

        The timer is deliberately re-armed after every poll.  Some older
        Enigma2 images only support single-shot timers, and relying on the
        repeating flag could leave a screen on "Loading ..." forever.
        """
        box = {"done": False, "result": None, "error": None}
        started = time.time()

        def worker():
            try:
                box["result"] = fn()
            except Exception as error:  # noqa: BLE001 - forwarded to the UI
                box["error"] = error
            box["done"] = True

        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()

        timer = eTimer()

        def arm():
            # One argument works on every eTimer version; the poll function
            # re-arms the timer when the worker is not finished yet.
            timer.start(120)

        def finish():
            try:
                timer.stop()
            except Exception:
                pass
            try:
                self._timers.remove(timer)
            except Exception:
                pass

        def fail(error):
            if not self._alive:
                return
            if on_error:
                on_error(error)
            else:
                self.show_error(error)

        def poll():
            if not box["done"]:
                if timeout and time.time() - started >= timeout:
                    finish()
                    fail(NetError(_("Loading took too long. Check the connection and try again.")))
                    return
                if on_wait is not None:
                    try:
                        on_wait()
                    except Exception:
                        pass
                arm()
                return
            finish()
            if not self._alive:
                return
            if box["error"] is not None:
                fail(box["error"])
            else:
                try:
                    on_done(box["result"])
                except Exception as error:  # noqa: BLE001
                    self.show_error(error)

        timer.callback.append(poll)
        self._timers.append(timer)
        arm()

    def show_error(self, error):
        message = _(to_text(error) or _("Error"))
        if isinstance(error, NetError):
            message = u"{0}\n\n{1}".format(_("Network error"), message)
        self.session.open(MessageBox, message, MessageBox.TYPE_ERROR, timeout=10)

    def show_info(self, message, timeout=5):
        self.session.open(MessageBox, to_text(message), MessageBox.TYPE_INFO, timeout=timeout)

    def status_text(self, text):
        widget = self.get("status")
        if widget is not None:
            widget.setText(to_text(text))


class ListScreen(AsyncScreen):
    """One list, a title, a status and a footer hint."""

    skin = """
    <screen name="IPTVProList" position="0,0" size="1280,720" resolution="1280,720" title="IPTV Player Pro" flags="wfNoBorder">
        <widget name="bg" position="0,0" size="1280,720" scale="1" />
        <widget name="logo" position="40,16" size="160,59" alphatest="blend" scale="1" />
        <widget name="title" position="40,86" size="800,40" font="Regular;30" halign="left" valign="center" foregroundColor="#ffffff" transparent="1" />
        <widget name="subtitle" position="40,126" size="900,26" font="Regular;18" halign="left" valign="center" foregroundColor="#bdbdbd" transparent="1" />
        <widget name="status" position="860,90" size="380,26" font="Regular;18" halign="right" valign="center" foregroundColor="#d8a8a8" transparent="1" />
        <widget name="list" position="40,168" size="1200,430" scrollbarMode="showOnDemand" />
        <widget name="hint" position="40,632" size="1200,32" font="Regular;18" halign="center" valign="center" foregroundColor="#9a9a9a" transparent="1" />
    </screen>
    """

    item_height = 72
    list_class = MultiList

    def __init__(self, session, title=u"", subtitle=u"", hint=u""):
        AsyncScreen.__init__(self, session)
        self.skinName = "IPTVProList"
        self["bg"] = Pixmap()
        self["logo"] = Pixmap()
        self["title"] = Label()
        self["subtitle"] = Label()
        self["status"] = Label()
        self["hint"] = Label()
        self["list"] = self.list_class(self.item_height)
        self.rows = []
        self["title"].setText(to_text(title))
        self["subtitle"].setText(to_text(subtitle))
        self["hint"].setText(to_text(hint))
        self["status"].setText(u"")
        self["actions"] = HelpableActionMap(self, [
            "NavigationActions", "OkCancelActions", "ColorActions", "MenuActions",
        ], {
            "up": self.key_up,
            "down": self.key_down,
            "left": self.key_left,
            "right": self.key_right,
            "pageUp": self.key_page_up,
            "pageDown": self.key_page_down,
            "top": self.key_top,
            "bottom": self.key_bottom,
            "ok": self.key_ok,
            "cancel": self.key_back,
            "red": self.key_red,
            "green": self.key_green,
            "yellow": self.key_yellow,
            "blue": self.key_blue,
            "menu": self.key_menu,
        }, prio=0, description=_("IPTV Player Pro"))
        self.onLayoutFinish.append(self._layout_ready)
        self.onShown.append(self._shown)

    # -------------------------------------------------------------- layout
    def _layout_ready(self):
        set_background(self)
        set_logo(self)
        self.apply_label_fonts()
        try:
            self["list"].enableAutoNavigation(False)
        except Exception:
            pass
        self.layout_ready()

    def _shown(self):
        try:
            self["list"].apply_fonts()
        except Exception:
            pass
        self.apply_label_fonts()
        self.shown_ready()

    def apply_label_fonts(self):
        """Apply the selected font to the skin-drawn labels.

        The inline skins are written for 1280x720, so their font sizes must
        be multiplied by the receiver's skin factor before being passed to
        gFont().
        """
        scale = skin_factor()
        for name, size in (("title", 30), ("subtitle", 18),
                           ("status", 18), ("hint", 18)):
            widget = self.get(name)
            instance = getattr(widget, "instance", None) if widget is not None else None
            if instance is None:
                continue
            try:
                instance.setFont(font(int(round(size * scale))))
            except Exception:
                pass

    def layout_ready(self):
        pass

    def shown_ready(self):
        pass

    # ------------------------------------------------------------- helpers
    def set_title(self, title):
        self["title"].setText(to_text(title))

    def set_subtitle(self, subtitle):
        self["subtitle"].setText(to_text(subtitle))

    def set_hint(self, hint):
        self["hint"].setText(to_text(hint))

    def set_rows(self, rows, entries, keep_position=False):
        index = 0
        if keep_position:
            try:
                index = self["list"].getSelectedIndex()
            except Exception:
                index = 0
        self.rows = rows
        self["list"].setList(entries)
        if not entries:
            return
        try:
            if keep_position:
                self["list"].setCurrentIndex(min(index, len(entries) - 1))
            else:
                self["list"].setCurrentIndex(0)
        except Exception:
            pass

    def set_entries(self, entries, rows=None, keep_position=False):
        if rows is None:
            rows = entries
        self.set_rows(rows, entries, keep_position)

    def current(self):
        try:
            index = self["list"].getSelectedIndex()
        except Exception:
            return None
        if 0 <= index < len(self.rows):
            return self.rows[index]
        return None

    # ------------------------------------------------------------- actions
    def key_up(self):
        self["list"].goLineUp()

    def key_down(self):
        self["list"].goLineDown()

    def key_left(self):
        pass

    def key_right(self):
        pass

    def key_page_up(self):
        self["list"].goPageUp()

    def key_page_down(self):
        self["list"].goPageDown()

    def key_top(self):
        self["list"].goTop()

    def key_bottom(self):
        self["list"].goBottom()

    def key_ok(self):
        row = self.current()
        if row is not None:
            self.activate(row)

    def key_back(self):
        self.close()

    def key_red(self):
        self.close()

    def key_green(self):
        pass

    def key_yellow(self):
        pass

    def key_blue(self):
        pass

    def key_menu(self):
        pass

    def activate(self, row):
        pass


class PosterLoader(object):
    """Loads one local image into a Pixmap widget (scaled)."""

    def __init__(self, screen, widget_name="poster"):
        self.screen = screen
        self.widget_name = widget_name
        self.picload = ePicLoad()
        self.picload.PictureData.get().append(self._picture_data)
        self.size = (280, 400)

    def load(self, path, size=None):
        if size:
            self.size = size
        if not path or not os.path.exists(path):
            return
        try:
            self.picload.setPara([self.size[0], self.size[1], 1, 1, 0, 1, "#00000000"])
            self.picload.startDecode(path)
        except Exception:
            pass

    def _picture_data(self, picInfo=None):
        try:
            if not self.screen._alive:
                return
            ptr = self.picload.getData()
        except Exception:
            return
        if ptr is None:
            return
        widget = self.screen.get(self.widget_name)
        if widget is not None:
            widget.instance.setPixmap(ptr)

    def stop(self):
        try:
            self.picload.PictureData.get().remove(self._picture_data)
        except Exception:
            pass


def download_poster(url, store, timeout=15):
    """Download artwork to the cache and return the local file."""
    return download_logo(url, store, kind="poster", timeout=timeout)


_DOWNLOADING_LOGOS = set()
_LOGO_LOCK = threading.Lock()

def download_logo(url, store, kind="logo", timeout=10):
    """Download channel logo or poster to local cache."""
    url = to_text(url).strip()
    if not url or not url.startswith(("http://", "https://")):
        return ""
    target = store.logo_file(url, kind=kind)
    if os.path.exists(target) and os.path.getsize(target) > 128:
        return target
    with _LOGO_LOCK:
        if url in _DOWNLOADING_LOGOS:
            return ""
        _DOWNLOADING_LOGOS.add(url)
    try:
        http = Http(timeout=timeout, retries=1)
        data, _handle = http.request(url)
        if not data or len(data) < 64:
            return ""
        tmp = target + ".part"
        with open(tmp, "wb") as handle:
            handle.write(data)
        if os.path.exists(target):
            try:
                os.remove(target)
            except Exception:
                pass
        os.rename(tmp, target)
        return target
    except Exception:
        return ""
    finally:
        with _LOGO_LOCK:
            _DOWNLOADING_LOGOS.discard(url)


def play_url(session, url, service_type=4097, name=u"", item_ua=None, item_opts=None):
    url = stream_url_with_headers(url, item_ua, item_opts)
    if not url:
        raise NetError(_("This stream is not playable"))
    # Preferred path: pass the URL directly to eServiceReference(type, flags,
    # path).  The string parser treats a raw "http://" as a path delimiter and
    # truncates it unless the colons are percent-encoded.  The three-argument
    # constructor keeps the complete URL, including spaces in HTTP headers.
    try:
        service = eServiceReference(int(service_type), 0, url)
    except TypeError:
        # Very old images only expose the string constructor.  Encode the
        # colons so the path is not mistaken for a service reference field.
        safe_url = quote(url, safe="%/?&=+,;@!$'()*[]~-._")
        reference = u"{0}:0:1:0:0:0:0:0:0:0:{1}".format(int(service_type), safe_url)
        service = eServiceReference(reference)
    if name:
        try:
            service.setName(to_text(name))
        except Exception:
            pass
    try:
        result = session.nav.playService(service)
    except Exception as error:
        raise NetError(to_text(error))
    # Navigation.playService() returns 1 when the service could not be
    # started (or when the request was refused).  Older images return None;
    # only an explicit 1 is treated as a failure, except when the same service
    # is already playing (that is a harmless "ignored" result).
    current = None
    has_current = False
    try:
        getter = getattr(session.nav, "getCurrentlyPlayingServiceOrGroup", None)
        if getter is not None:
            current = getter()
            has_current = True
    except Exception:
        current = None
        has_current = False
    if result == 1:
        if current is None or to_text(current.toString()) != to_text(service.toString()):
            raise NetError(_("Could not open the stream"))
    elif has_current and current is None:
        # A successful Navigation.playService() call leaves the new service
        # as the current one.  Some images return 0 even after a native tune
        # failure and clear the reference instead; do not close the plugin in
        # that case.
        raise NetError(_("Could not open the stream"))
    return result


def yes_no(session, text, callback):
    session.openWithCallback(callback, MessageBox, to_text(text), MessageBox.TYPE_YESNO, timeout=-1)


def info_box(session, text, timeout=6):
    session.open(MessageBox, to_text(text), MessageBox.TYPE_INFO, timeout=timeout)
