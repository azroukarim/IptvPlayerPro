# -*- coding: utf-8 -*-
"""Main menu (the tile screen)."""

from __future__ import absolute_import

from Components.ActionMap import HelpableActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Screens.Screen import Screen

from ..core.backends import active_backend, source_summary
from ..core.i18n import _, set_language
from ..core.store import Store
from ..core.util import is_expired, to_text
from .base import AsyncScreen, info_box, pixmap, set_background, set_logo, yes_no
from .skins import MAIN_SKIN


TILES = [
    {"key": "live", "index": 0, "card": "big", "label": "Live TV", "icon": "live.png"},
    {"key": "movies", "index": 1, "card": "small", "label": "Movies", "icon": "movies.png"},
    {"key": "series", "index": 2, "card": "small", "label": "Series", "icon": "series.png"},
    {"key": "account", "index": 3, "card": "small", "label": "Account", "icon": "account.png"},
    {"key": "server", "index": 4, "card": "small", "label": "Change Server", "icon": "server.png"},
    {"key": "settings", "index": 5, "card": "wide", "label": "Settings", "icon": "settings.png"},
    {"key": "reload", "index": 6, "card": "wide", "label": "Reload Portal", "icon": "reload.png"},
    {"key": "exit", "index": 7, "card": "wide", "label": "Exit", "icon": "exit.png"},
]

NAV = {
    "live": {"left": "server", "right": "movies", "up": "settings", "down": "account"},
    "movies": {"left": "live", "right": "settings", "up": "movies", "down": "account"},
    "series": {"left": "movies", "right": "settings", "up": "series", "down": "server"},
    "account": {"left": "live", "right": "reload", "up": "movies", "down": "account"},
    "server": {"left": "live", "right": "reload", "up": "series", "down": "server"},
    "settings": {"left": "movies", "right": "settings", "up": "settings", "down": "reload"},
    "reload": {"left": "server", "right": "reload", "up": "settings", "down": "exit"},
    "exit": {"left": "server", "right": "exit", "up": "reload", "down": "exit"},
}


class MainMenu(AsyncScreen):
    skin = MAIN_SKIN

    def __init__(self, session):
        AsyncScreen.__init__(self, session)
        self.skinName = "IPTVProMain"
        self.store = Store()
        set_language(self.store.settings.get("language") or "ar")
        self.backend = active_backend(self.store)
        self.focus = 0

        self["bg"] = Pixmap()
        self["logo"] = Pixmap()
        self["status1"] = Label()
        self["status2"] = Label()
        self["hint"] = Label()
        for tile in TILES:
            index = tile["index"]
            self["t{0}".format(index)] = Pixmap()
            self["i{0}".format(index)] = Pixmap()
            self["l{0}".format(index)] = Label()

        self["actions"] = HelpableActionMap(self, [
            "NavigationActions", "OkCancelActions", "MenuActions",
        ], {
            "up": self.move_up,
            "down": self.move_down,
            "left": self.move_left,
            "right": self.move_right,
            "ok": self.select,
            "cancel": self.close,
            "menu": self.open_sources,
        }, prio=0, description=_("IPTV Player Pro"))

        self.onLayoutFinish.append(self.layout_ready)
        self.onShown.append(self.update_status)

    # -------------------------------------------------------------- layout
    def layout_ready(self):
        set_background(self)
        set_logo(self, "logo.png")
        self["hint"].setText(_("OK select  •  MENU servers  •  BACK exit"))
        for tile in TILES:
            index = tile["index"]
            self["t{0}".format(index)].instance.setPixmap(pixmap("card_{0}.png".format(tile["card"])))
            self["i{0}".format(index)].instance.setPixmap(pixmap(tile["icon"]))
            self["l{0}".format(index)].setText(_(tile["label"]))
        self._set_focus(0)
        self.update_status()

    def apply_language(self):
        for tile in TILES:
            self["l{0}".format(tile["index"])].setText(_(tile["label"]))
        if self.instance:
            self["hint"].setText(_("OK select  •  MENU servers  •  BACK exit"))
        self.update_status()

    def update_status(self):
        source = self.store.active_source()
        if source is None:
            self["status1"].setText(_("No playlist selected"))
            self["status2"].setText(_("Press MENU for the server list"))
            return
        self["status1"].setText(u"{0}: {1}".format(_("Current playlist"), source.get("name") or ""))
        self["status2"].setText(source_summary(source, self.store))

    # ------------------------------------------------------------- actions
    def _set_focus(self, index):
        old = self.focus
        self.focus = index
        for tile in TILES:
            if tile["index"] in (old, index):
                suffix = "_f" if tile["index"] == index else ""
                self["t{0}".format(tile["index"])].instance.setPixmap(
                    pixmap("card_{0}{1}.png".format(tile["card"], suffix)))

    def move(self, direction):
        key = TILES[self.focus]["key"]
        target = NAV.get(key, {}).get(direction)
        if not target or target == key:
            return
        for tile in TILES:
            if tile["key"] == target:
                self._set_focus(tile["index"])
                return

    def move_up(self):
        self.move("up")

    def move_down(self):
        self.move("down")

    def move_left(self):
        self.move("left")

    def move_right(self):
        self.move("right")

    def select(self):
        key = TILES[self.focus]["key"]
        if key == "exit":
            self.close()
        elif key == "server":
            self.open_sources()
        elif key == "settings":
            self.open_settings()
        elif key == "account":
            self.open_account()
        elif key == "reload":
            self.reload_portal()
        else:
            self.open_browser(key)

    def open_sources(self):
        from .sources import SourcesScreen
        self.session.openWithCallback(self.sources_closed, SourcesScreen, self.store)

    def sources_closed(self, result=None):
        # The source may have been edited or deleted, so always rebuild.
        self.backend = active_backend(self.store)
        self.update_status()
        if result == "zapped":
            self.close()

    def open_settings(self):
        from .settings import SettingsScreen
        self.session.openWithCallback(self.settings_closed, SettingsScreen, self.store)

    def settings_closed(self, result=None):
        set_language(self.store.settings.get("language") or "ar")
        self.apply_language()
        if result == "zapped":
            self.close()

    def open_account(self):
        from .account import AccountScreen
        self.session.openWithCallback(self.child_closed, AccountScreen, self.store, self.backend)

    def child_closed(self, result=None):
        if result == "zapped":
            self.close()
        elif result == "changed":
            self.backend = active_backend(self.store)
        self.update_status()
    def open_browser(self, key):
        if self.backend is None:
            info_box(self.session, _("No active playlist") + u"\n" + _("Open the server list and add an M3U playlist or a MAG portal first."))
            self.open_sources()
            return
        if key == "live":
            from .browse import LiveCategoriesScreen
            screen = LiveCategoriesScreen
        elif key == "movies":
            from .browse import VodCategoriesScreen
            screen = VodCategoriesScreen
        else:
            from .browse import SeriesCategoriesScreen
            screen = SeriesCategoriesScreen
        self.session.openWithCallback(self.child_closed, screen, self.store, self.backend)
        self.update_status()

    def reload_portal(self):
        if self.backend is None:
            info_box(self.session, _("No active playlist"))
            self.open_sources()
            return
        yes_no(self.session, _("Reload portal") + u"?", self._reload_confirmed)

    def _reload_confirmed(self, answer):
        if not answer:
            return
        self["status2"].setText(_("Refreshing ..."))
        self.run_async(lambda: self.backend.refresh(force=True), self._reloaded, self._reload_failed)

    def _reloaded(self, _result):
        self.update_status()
        source = self.store.active_source()
        info = (source or {}).get("info") or {}
        message = _("Refresh finished")
        if source and source.get("type") == "mag":
            expires = info.get("expires") or ""
            if expires:
                message = u"{0}\n{1}: {2}".format(message, _("Expires"), expires)
                if is_expired(expires):
                    message = u"{0}\n{1}".format(_("Account has expired"), _("Expires") + ": " + expires)
            else:
                message = u"{0}\n{1}".format(message, to_text(info.get("channels") or 0) + u" " + _("channels"))
        else:
            message = u"{0}\n{1} {2}  \u2022  {3} {4}  \u2022  {5} {6}".format(
                message, info.get("channels") or 0, _("channels"),
                info.get("vod") or 0, _("movies"), info.get("series") or 0, _("series"))
        info_box(self.session, message, timeout=7)

    def _reload_failed(self, error):
        self.update_status()
        self.show_error(error)

    def key_menu(self):
        self.open_sources()
