# -*- coding: utf-8 -*-
"""Main menu (the tile screen)."""

from __future__ import absolute_import

import time

from enigma import eTimer

from Components.ActionMap import HelpableActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Screens.Screen import Screen

from ..core import prefetch
from ..core.backends import active_backend, source_summary
from ..core.i18n import _, set_language
from ..core.store import Store
from ..core.util import is_expired, to_text
from .base import (AsyncScreen, info_box, pixmap, set_active_font,
                   set_background, set_logo, yes_no)
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
    "live": {"left": "server", "right": "movies", "up": "settings", "down": "exit"},
    "movies": {"left": "live", "right": "series", "up": "movies", "down": "account"},
    "series": {"left": "movies", "right": "settings", "up": "series", "down": "server"},
    "account": {"left": "live", "right": "server", "up": "movies", "down": "account"},
    "server": {"left": "live", "right": "reload", "up": "series", "down": "server"},
    "settings": {"left": "movies", "right": "live", "up": "settings", "down": "reload"},
    "reload": {"left": "server", "right": "live", "up": "settings", "down": "exit"},
    "exit": {"left": "server", "right": "live", "up": "reload", "down": "exit"},
}


class MainMenu(AsyncScreen):
    skin = MAIN_SKIN

    def __init__(self, session):
        AsyncScreen.__init__(self, session)
        self.skinName = "IPTVProMain"
        self.store = Store()
        set_active_font(self.store.settings.get("font") or "default")
        set_language(self.store.settings.get("language") or "ar")
        prefetch.reconcile(self.store)
        self.backend = active_backend(self.store)
        self.focus = 0
        self._prefetch_timer = None
        self._prefetch_state = ""
        self._loading_timer = None
        self._loading_key = ""
        self._loading_title = u""
        self._loading_text = u""
        self._loading_display = 0.0
        self._loading_target = 0
        self._loading_finished = False
        self._loading_opened = False
        self._loading_started = 0.0
        self._loading_hold = 0
        self._loading_source_id = ""

        self["bg"] = Pixmap()
        self["logo"] = Pixmap()
        self["status1"] = Label()
        self["status2"] = Label()
        self["hint"] = Label()
        self["loadingBg"] = Pixmap()
        self["loadingTitle"] = Label()
        self["loadingPercent"] = Label()
        self["loadingBar"] = Pixmap()
        self["loadingText"] = Label()
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
        self.onShown.append(self.on_shown)

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
        self["loadingBg"].instance.setPixmap(pixmap("loading_panel.png"))
        self["loadingBar"].instance.setPixmap(pixmap("loadbar_00.png"))
        self._hide_loading_widgets()
        self._set_focus(0)
        self.update_status()
        self.ensure_web_interface()
        self._start_prefetch_timer()

    def on_shown(self):
        # The web interface writes the same config file.  Reload it so a
        # source added from a browser is visible immediately.
        try:
            self.store.load()
        except Exception:
            pass
        set_language(self.store.settings.get("language") or "ar")
        prefetch.reconcile(self.store)
        self.backend = active_backend(self.store)
        try:
            self.backend.ensure_fresh()
        except Exception:
            pass
        self._prefetch_state = self._prefetch_info_state()
        self.apply_language()
        self.ensure_web_interface()

    def ensure_web_interface(self):
        try:
            from ..web.server import manager
            manager.ensure(self.store)
        except Exception:
            pass

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
        text = prefetch.status_text(source.get("id"))
        self["status2"].setText(text or source_summary(source, self.store))

    def _prefetch_info_state(self):
        source = self.store.active_source() or {}
        return to_text((source.get("info") or {}).get("prefetch"))

    def _start_prefetch_timer(self):
        if self._prefetch_timer is None:
            try:
                self._prefetch_timer = eTimer()
                self._prefetch_timer.callback.append(self._prefetch_tick)
                self._timers.append(self._prefetch_timer)
            except Exception:
                self._prefetch_timer = None
        if self._prefetch_timer is not None:
            try:
                self._prefetch_timer.start(1500, False)
            except Exception:
                pass

    def _prefetch_tick(self):
        if not getattr(self, "_alive", True):
            return
        source = self.store.active_source()
        if source is None:
            return
        text = prefetch.status_text(source.get("id"))
        if text:
            self["status2"].setText(text)
            self._prefetch_state = "running"
            return
        state = self._prefetch_info_state()
        if state != self._prefetch_state:
            self._prefetch_state = state
            self.update_status()

    # ------------------------------------------------------------- loading
    def _hide_loading_widgets(self):
        for name in ("loadingBg", "loadingTitle", "loadingPercent",
                     "loadingBar", "loadingText"):
            widget = self.get(name)
            if widget is not None:
                try:
                    widget.hide()
                except Exception:
                    pass
        for name in ("status1", "status2"):
            widget = self.get(name)
            if widget is not None:
                try:
                    widget.show()
                except Exception:
                    pass

    def _show_loading_widgets(self):
        for name in ("loadingBg", "loadingTitle", "loadingPercent",
                     "loadingBar", "loadingText"):
            widget = self.get(name)
            if widget is not None:
                try:
                    widget.show()
                except Exception:
                    pass
        for name in ("status1", "status2"):
            widget = self.get(name)
            if widget is not None:
                try:
                    widget.hide()
                except Exception:
                    pass

    def _start_loading_timer(self):
        if self._loading_timer is None:
            try:
                self._loading_timer = eTimer()
                self._loading_timer.callback.append(self._loading_tick)
                self._timers.append(self._loading_timer)
            except Exception:
                self._loading_timer = None
        if self._loading_timer is not None:
            try:
                self._loading_timer.start(80, False)
            except Exception:
                pass

    def _reset_loading(self):
        self._loading_key = ""
        self._loading_title = u""
        self._loading_text = u""
        self._loading_display = 0.0
        self._loading_target = 0
        self._loading_finished = False
        self._loading_opened = False
        self._loading_hold = 0
        self._loading_source_id = ""
        if self._loading_timer is not None:
            try:
                self._loading_timer.stop()
            except Exception:
                pass

    def _backend_ready(self, key):
        backend = self.backend
        if backend is None:
            return False
        try:
            if key == "live":
                check = getattr(backend, "is_live_ready", None)
                return bool(check() if check else backend.is_ready())
            if key == "movies":
                check = getattr(backend, "is_vod_categories_ready", None)
                if check:
                    return bool(check())
                return bool(backend.is_vod_ready())
            check = getattr(backend, "is_series_categories_ready", None)
            if check:
                return bool(check())
            return bool(backend.is_series_ready())
        except Exception:
            return False

    def _update_loading_ui(self):
        percent = max(0, min(100, int(self._loading_display)))
        self["loadingTitle"].setText(self._loading_title)
        self["loadingPercent"].setText(u"{0}/100".format(percent))
        self["loadingText"].setText(self._loading_text or _("Please wait ..."))
        frame = max(0, min(20, percent // 5))
        self["loadingBar"].instance.setPixmap(
            pixmap("loadbar_{0:02d}.png".format(frame)))

    def _show_loading(self, key):
        if self._loading_key:
            return
        titles = {
            "live": _("Loading Live TV ..."),
            "movies": _("Loading Movies ..."),
            "series": _("Loading Series ..."),
        }
        self._loading_key = key
        self._loading_title = titles.get(key, _("Loading ..."))
        self._loading_text = _("Please wait ...")
        self._loading_display = 0.0
        self._loading_target = 0
        self._loading_finished = False
        self._loading_opened = False
        self._loading_started = time.time()
        self._loading_hold = 0
        source = self.store.active_source() or {}
        self._loading_source_id = to_text(source.get("id"))
        self._show_loading_widgets()
        self._update_loading_ui()
        self._start_loading_timer()
        self._begin_loading(key)

    def _begin_loading(self, key):
        if self._backend_ready(key):
            self._loading_text = _("Ready")
            self._loading_target = 100
            self._loading_finished = True
            return
        # Do not wait for the full MAG catalogue here.  Preparing every VOD
        # and series page can take minutes on a large portal.  Each section is
        # prepared directly below, and Movies/Series load their items lazily.
        self._loading_refresh()

    def _loading_refresh(self):
        progress = {"text": _("Loading ..."), "percent": 0}
        if self._loading_target >= 100:
            self._loading_target = 95

        def report(text, percent=None):
            progress["text"] = to_text(text)
            if percent is not None:
                try:
                    value = max(0, min(95, int(percent)))
                except Exception:
                    value = progress["percent"]
                progress["percent"] = max(progress["percent"], value)
            self._loading_text = progress["text"]
            if progress["percent"] > self._loading_target:
                self._loading_target = progress["percent"]

        self._loading_text = progress["text"]
        network_timeout = 20
        try:
            network_timeout = int(self.store.settings.get("timeout") or 20)
        except Exception:
            pass
        # Section-specific loading should be fast (live channels only).
        # Use a shorter timeout to fail fast on bad portals.
        limit = max(20, network_timeout * 2 + 5)

        def prepare():
            prepare_section = getattr(self.backend, "prepare_section", None)
            if prepare_section:
                return prepare_section(self._loading_key, progress=report)
            return self.backend.refresh(progress=report)

        self.run_async(
            prepare,
            self._loading_refresh_done,
            self._loading_failed,
            timeout=limit,
            on_wait=self._loading_refresh_wait,
        )

    def _loading_refresh_wait(self):
        # The report callback already updates the labels; this hook keeps the
        # timer alive and lets the animation advance while the network works.
        pass

    def _loading_refresh_done(self, _result):
        if not self._backend_ready(self._loading_key):
            self._loading_failed(_("Preparation failed"))
            return
        self._loading_text = _("Ready")
        self._loading_target = 100
        self._loading_finished = True

    def _loading_failed(self, error):
        if self._backend_ready(self._loading_key):
            self._loading_text = _("Ready")
            self._loading_target = 100
            self._loading_finished = True
            return
        self._hide_loading_widgets()
        self._reset_loading()
        self.show_error(error)

    def _loading_tick(self):
        if not self._loading_key or not getattr(self, "_alive", True):
            return
        if not self._loading_finished:
            elapsed = max(0.0, time.time() - self._loading_started)
            # Progress based on actual backend progress, not fake animation.
            # The backend's progress callback updates _loading_target.
            # We animate smoothly towards that target.
            target = self._loading_target
        else:
            target = 100
        if self._loading_display < target:
            gap = target - self._loading_display
            step = max(0.8, gap * 0.22)
            if self._loading_finished:
                step = max(step, 2.2)
            self._loading_display = min(target, self._loading_display + step)
        elif self._loading_finished:
            self._loading_display = 100.0
        self._update_loading_ui()
        if self._loading_finished and self._loading_display >= 99.9:
            self._loading_hold += 1
            if self._loading_hold >= 4:
                self._open_after_loading()

    def _open_after_loading(self):
        if self._loading_opened:
            return
        self._loading_opened = True
        key = self._loading_key
        self._hide_loading_widgets()
        self._reset_loading()
        try:
            self.backend.ensure_fresh()
        except Exception:
            pass
        self.backend = active_backend(self.store) or self.backend
        self.update_status()
        if key == "live":
            from .browse import LiveBrowserScreen
            screen = LiveBrowserScreen
        elif key == "movies":
            from .browse import VodCategoriesScreen
            screen = VodCategoriesScreen
        else:
            from .browse import SeriesCategoriesScreen
            screen = SeriesCategoriesScreen
        self.session.openWithCallback(self.child_closed, screen, self.store, self.backend)

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
        if self._loading_key:
            return
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
        if self._loading_key:
            return
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
        if self._loading_key:
            return
        from .sources import SourcesScreen
        self.session.openWithCallback(self.sources_closed, SourcesScreen, self.store)

    def sources_closed(self, result=None):
        # The source may have been edited or deleted, so always rebuild.
        self.backend = active_backend(self.store)
        try:
            self.backend.ensure_fresh()
        except Exception:
            pass
        self.update_status()
        if result == "zapped":
            self.close()

    def open_settings(self):
        if self._loading_key:
            return
        from .settings import SettingsScreen
        self.session.openWithCallback(self.settings_closed, SettingsScreen, self.store)

    def settings_closed(self, result=None):
        set_language(self.store.settings.get("language") or "ar")
        self.apply_language()
        if result == "zapped":
            self.close()

    def open_account(self):
        if self._loading_key:
            return
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
        self._show_loading(key)

    def reload_portal(self):
        if self._loading_key:
            return
        if self.backend is None:
            info_box(self.session, _("No active playlist"))
            self.open_sources()
            return
        yes_no(self.session, _("Reload portal") + u"?", self._reload_confirmed)

    def _reload_confirmed(self, answer):
        if not answer:
            return
        source = self.store.active_source() or {}
        source_id = to_text(source.get("id"))
        if source_id and prefetch.enabled(self.store):
            if prefetch.start(self.store, source_id, force=True):
                self["status2"].setText(
                    prefetch.status_text(source_id) or _("Preparing ..."))
                info_box(self.session, _("Refresh started in the background"),
                         timeout=5)
                self._prefetch_state = "running"
                return
            if prefetch.running(source_id):
                self["status2"].setText(
                    prefetch.status_text(source_id) or _("Preparing ..."))
                info_box(self.session, _("The source is already being prepared."),
                         timeout=5)
                self._prefetch_state = "running"
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
