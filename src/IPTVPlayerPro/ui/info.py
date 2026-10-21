# -*- coding: utf-8 -*-
"""Movie / stream details screen."""

from __future__ import absolute_import

import os

from Components.ActionMap import HelpableActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ScrollLabel import ScrollLabel

from ..core.i18n import _
from ..core.util import safe_int, to_text
from .base import (AsyncScreen, PosterLoader, download_poster, pixmap, play_url,
                   set_background, set_logo)
from .skins import INFO_SKIN


class InfoScreen(AsyncScreen):
    skin = INFO_SKIN

    def __init__(self, session, store, backend, item):
        AsyncScreen.__init__(self, session)
        self.skinName = "IPTVProInfo"
        self.store = store
        self.backend = backend
        self.item = item
        self.poster = None

        self["bg"] = Pixmap()
        self["logo"] = Pixmap()
        self["title"] = Label()
        self["meta"] = Label()
        self["poster"] = Pixmap()
        self["description"] = ScrollLabel()
        self["hint"] = Label()

        self["title"].setText(to_text(item.get("name") or ""))
        self["meta"].setText(self._meta())
        self["description"].setText(to_text(item.get("description") or _("No description available.")))
        self["hint"].setText(_("OK play  •  BACK close"))

        self["actions"] = HelpableActionMap(self, [
            "NavigationActions", "OkCancelActions", "ColorActions",
        ], {
            "up": self.scroll_up,
            "down": self.scroll_down,
            "pageUp": self.page_up,
            "pageDown": self.page_down,
            "ok": self.play,
            "cancel": self.close,
            "red": self.close,
            "green": self.play,
            "blue": self.play,
        }, prio=0, description=_("IPTV Player Pro"))

        self.onLayoutFinish.append(self.layout_ready)
        self.onClose.append(self._stop_poster)

    def _stop_poster(self):
        if self.poster is not None:
            self.poster.stop()

    def _meta(self):
        item = self.item
        parts = []
        if item.get("year"):
            parts.append(to_text(item["year"]))
        if item.get("genres"):
            parts.append(to_text(item["genres"]))
        if item.get("rating"):
            parts.append(u"\u2605 " + to_text(item["rating"]))
        if item.get("time"):
            parts.append(to_text(item["time"]))
        if item.get("group"):
            parts.append(to_text(item["group"]))
        return u"   \u2022   ".join(parts)

    def layout_ready(self):
        set_background(self)
        set_logo(self)
        self.poster = PosterLoader(self, "poster")
        logo = to_text(self.item.get("logo"))
        if not logo:
            return
        cached = self.store.logo_file(logo, "poster")
        if os.path.exists(cached) and os.path.getsize(cached) > 256:
            self.poster.load(cached)
            return
        self.run_async(lambda: download_poster(logo, self.store), self._poster_ready, lambda error: None)

    def _poster_ready(self, path):
        if path:
            self.poster.load(path)

    # ------------------------------------------------------------- actions
    def scroll_up(self):
        try:
            self["description"].moveUp()
        except Exception:
            pass

    def scroll_down(self):
        try:
            self["description"].moveDown()
        except Exception:
            pass

    def page_up(self):
        try:
            self["description"].pageUp()
        except Exception:
            pass

    def page_down(self):
        try:
            self["description"].pageDown()
        except Exception:
            pass

    def play(self):
        self["hint"].setText(_("Resolving stream ..."))
        self.run_async(lambda: self.backend.resolve(self.item), self._play, self._play_failed)

    def _play(self, url):
        try:
            play_url(self.session, url, safe_int(self.store.settings.get("service_type"), 4097),
                     self.item.get("name"))
        except Exception as error:  # noqa: BLE001
            self["hint"].setText(_("OK play  •  BACK close"))
            self.show_error(error)
            return
        if self.store.settings.get("close_after_zap", True):
            self.close("zapped")
        else:
            self["hint"].setText(_("Playing ..."))

    def _play_failed(self, error):
        self["hint"].setText(_("OK play  •  BACK close"))
        self.show_error(error)
