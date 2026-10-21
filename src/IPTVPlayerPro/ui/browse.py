# -*- coding: utf-8 -*-
"""Browse screens: live TV, movies and series."""

from __future__ import absolute_import

import os

from Components.ActionMap import HelpableActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Screens.VirtualKeyBoard import VirtualKeyBoard

from ..core.backends import source_label
from ..core.i18n import _
from ..core.util import human_count, safe_int, to_text
from .base import (AsyncScreen, ListScreen, LiveList, category_entry,
                   channel_entry, info_box, pixmap, play_url, row_entry)
from .info import InfoScreen
from .skins import LIVE_SKIN


class BackendScreen(ListScreen):
    """Base for screens that need a loaded backend catalogue."""

    def __init__(self, session, store, backend, title, subtitle=u"", hint=u""):
        ListScreen.__init__(self, session, title, subtitle, hint)
        self.store = store
        self.backend = backend
        self.started = False
        self.query = u""
        self.page = 1
        self.total = 0

    def shown_ready(self):
        if not self.started:
            self.started = True
            self.start()

    def start(self):
        if self.backend is None:
            info_box(self.session, _("No active playlist") + u"\n" + _("Open the server list and add an M3U playlist or a MAG portal first."))
            self.close()
            return
        if self.backend.is_ready():
            self.build()
        else:
            progress = {"text": _("Loading ...")}

            def report(text):
                progress["text"] = to_text(text)

            network_timeout = safe_int(self.store.settings.get("timeout"), 20)
            limit = max(45, network_timeout * 3 + 10)
            self.status_text(progress["text"])
            self.run_async(
                lambda: self.backend.refresh(progress=report),
                self._loaded,
                self._load_failed,
                timeout=limit,
                on_wait=lambda: self.status_text(progress["text"]),
            )

    def _loaded(self, _result):
        self.status_text(u"")
        self.build()

    def _load_failed(self, error):
        self.status_text(u"")
        self.show_error(error)

    def build(self):
        pass

    def open_child(self, screen_class, *args):
        self.session.openWithCallback(self.child_closed, screen_class, self.store, self.backend, *args)

    def child_closed(self, result=None):
        if result == "zapped":
            self.close("zapped")

    # ------------------------------------------------------------- playback
    def play_item(self, item):
        self.status_text(_("Resolving stream ..."))
        self.run_async(lambda: self.backend.resolve(item), lambda url: self._play(url, item), self._play_failed)

    def _play(self, url, item):
        self.status_text(u"")
        try:
            play_url(self.session, url, safe_int(self.store.settings.get("service_type"), 4097), item.get("name"))
        except Exception as error:  # noqa: BLE001
            self.show_error(error)
            return
        if self.store.settings.get("close_after_zap", True):
            self.close("zapped")

    def _play_failed(self, error):
        self.status_text(u"")
        self.show_error(error)

    # --------------------------------------------------------------- search
    def ask_search(self):
        self.session.openWithCallback(self.search_done, VirtualKeyBoard, title=_("Search ..."), text=self.query)

    def search_done(self, text):
        if text is None:
            return
        self.query = to_text(text).strip()
        self.build()

    # -------------------------------------------------------------- refresh
    def reload_backend(self):
        progress = {"text": _("Refreshing ...")}

        def report(text):
            progress["text"] = to_text(text)

        network_timeout = safe_int(self.store.settings.get("timeout"), 20)
        limit = max(45, network_timeout * 3 + 10)
        self.status_text(progress["text"])
        self.run_async(
            lambda: self.backend.refresh(force=True, progress=report),
            self._reloaded,
            self._load_failed,
            timeout=limit,
            on_wait=lambda: self.status_text(progress["text"]),
        )

    def _reloaded(self, _result):
        self.status_text(u"")
        self.build()


class LiveCategoriesScreen(BackendScreen):
    def __init__(self, session, store, backend):
        BackendScreen.__init__(self, session, store, backend, _("Live TV"),
                               source_label(store.active_source()), _("OK open  •  RED back"))
        self.set_hint(_("OK open  •  BLUE reload  •  RED back"))

    def build(self):
        categories = self.backend.live_categories()
        rows = []
        entries = []
        for category in categories:
            rows.append(category)
            icon = pixmap("star.png") if category.get("id") == "fav" else pixmap("folder.png")
            entries.append(row_entry(
                1200, 72, category.get("name") or "", icon=icon, icon_size=(44, 44),
                value=human_count(category.get("count")),
            ))
        self.set_entries(entries, rows)
        self.set_subtitle(u"{0} {1}".format(len(categories), _("categories")))
        if not categories:
            self.status_text(_("No channels"))

    def activate(self, row):
        if safe_int(row.get("count")) == 0 and row.get("id") == "fav":
            info_box(self.session, _("No channels"))
            return
        self.open_child(LiveScreen, row)

    def key_blue(self):
        self.reload_backend()


class LiveScreen(BackendScreen):
    def __init__(self, session, store, backend, category):
        BackendScreen.__init__(self, session, store, backend, category.get("name") or _("Live TV"),
                               u"", _("OK play  •  GREEN search  •  YELLOW favorite  •  BLUE reload  •  RED back"))
        self.category = category

    def build(self):
        items = self.backend.live_items(self.category.get("id") or "all", self.query)
        rows = []
        entries = []
        for item in items:
            rows.append(item)
            favorite = self.backend.is_favorite(item)
            subtitle = item.get("group") or _("Live TV")
            if item.get("number"):
                subtitle = u"{0}  \u2022  {1}".format(item["number"], subtitle)
            entries.append(row_entry(
                1200, 72, item.get("name") or "", subtitle=subtitle,
                icon=self._channel_icon(item), icon_size=(48, 48),
                badge=u"\u2605" if favorite else None,
            ))
        self.set_entries(entries, rows)
        subtitle = u"{0} {1}".format(len(items), _("channels"))
        if self.query:
            subtitle = u"{0}  \u2022  \"{1}\"".format(subtitle, self.query)
        self.set_subtitle(subtitle)
        if not items:
            self.status_text(_("No channels"))
        else:
            self.status_text(u"")

    def _channel_icon(self, item):
        logo = to_text(item.get("logo"))
        if logo:
            local = self.store.logo_file(logo)
            if os.path.exists(local):
                try:
                    from Tools.LoadPixmap import LoadPixmap
                    pointer = LoadPixmap(local)
                    if pointer is not None:
                        return pointer
                except Exception:
                    pass
        return pixmap("channel.png")

    def activate(self, item):
        self.play_item(item)

    def key_ok(self):
        item = self.current()
        if item is None:
            return
        self.play_item(item)

    def key_green(self):
        self.ask_search()

    def key_yellow(self):
        item = self.current()
        if item is None:
            return
        state = self.backend.toggle_favorite(item)
        self.build()
        try:
            self.status_text(_("Added to favorites") if state else _("Removed from favorites"))
        except Exception:
            pass

    def key_blue(self):
        self.query = u""
        self.reload_backend()


class LiveBrowserScreen(BackendScreen):
    """Three-column live TV browser.

    The layout intentionally follows the supplied Ibo Player Pro mock-up:
    categories on the left, numbered channels in the middle and a preview
    pane on the right.  It uses the same backend calls as the old two-screen
    flow, so M3U and MAG portals keep working unchanged.
    """

    skin = LIVE_SKIN

    def __init__(self, session, store, backend):
        AsyncScreen.__init__(self, session)
        self.skinName = "IPTVProLive"
        self.store = store
        self.backend = backend
        self.started = False
        self.query = u""
        self.page = 1
        self.total = 0
        self.categories = []
        self.items = []
        self.category_id = "all"
        self.focus = "categories"
        self._channel_request = 0

        self["bg"] = Pixmap()
        self["header"] = Pixmap()
        self["logo"] = Pixmap()
        self["navLive"] = Label()
        self["navMovies"] = Label()
        self["navSeries"] = Label()
        self["searchPill"] = Pixmap()
        self["searchText"] = Label()
        self["status"] = Label()
        self["source"] = Label()
        self["leftPanel"] = Pixmap()
        self["midPanel"] = Pixmap()
        self["rightPanel"] = Pixmap()
        self["catHeader"] = Label()
        self["categories"] = LiveList(52)
        self["chHeader"] = Label()
        self["channels"] = LiveList(52)
        self["preview"] = Pixmap()
        self["previewKind"] = Label()
        self["previewLogo"] = Pixmap()
        self["previewName"] = Label()
        self["previewMeta"] = Label()
        self["previewUrl"] = Label()
        self["previewFav"] = Label()
        self["playBg"] = Pixmap()
        self["playLabel"] = Label()
        self["favBg"] = Pixmap()
        self["favLabel"] = Label()
        self["hint"] = Label()

        self["actions"] = HelpableActionMap(self, [
            "NavigationActions", "OkCancelActions", "ColorActions", "MenuActions",
        ], {
            "up": self.key_up,
            "down": self.key_down,
            "pageUp": self.key_page_up,
            "pageDown": self.key_page_down,
            "top": self.key_top,
            "bottom": self.key_bottom,
            "left": self.key_left,
            "right": self.key_right,
            "ok": self.key_ok,
            "cancel": self.key_back,
            "red": self.key_red,
            "green": self.key_green,
            "yellow": self.key_yellow,
            "blue": self.key_blue,
            "menu": self.key_menu,
        }, prio=0, description=_("IPTV Player Pro"))

        self.onLayoutFinish.append(self._layout_ready)
        self.onShown.append(self.shown_ready)

    # -------------------------------------------------------------- layout
    def _layout_ready(self):
        self["bg"].instance.setPixmap(pixmap("live_bg.png"))
        self["header"].instance.setPixmap(pixmap("live_header.png"))
        self["logo"].instance.setPixmap(pixmap("logo_small.png"))
        self["leftPanel"].instance.setPixmap(pixmap("live_panel_left.png"))
        self["midPanel"].instance.setPixmap(pixmap("live_panel_mid.png"))
        self["rightPanel"].instance.setPixmap(pixmap("live_panel_right.png"))
        self["preview"].instance.setPixmap(pixmap("live_preview.png"))
        self["searchPill"].instance.setPixmap(pixmap("live_search.png"))
        self["playBg"].instance.setPixmap(pixmap("live_button.png"))
        self["favBg"].instance.setPixmap(pixmap("live_button_dark.png"))

        self["navLive"].setText(_("Live TV"))
        self["navMovies"].setText(_("Movies"))
        self["navSeries"].setText(_("Series"))
        self["searchText"].setText(u"GREEN  " + _("Search channels"))
        self["hint"].setText(_("OK play  •  GREEN search  •  YELLOW favorite  •  BLUE reload  •  RED back"))
        self["playLabel"].setText(u"OK  " + _("Play"))
        self["previewKind"].setText(_("CHANNEL PREVIEW"))
        self["previewName"].setText(_("Live TV"))
        self["previewMeta"].setText(u"")
        self["previewUrl"].setText(u"")
        self["previewFav"].setText(u"")
        self["previewLogo"].instance.setPixmap(pixmap("channel.png"))
        self["status"].setText(u"")
        self["source"].setText(u"")
        self.update_source()
        self.update_search_text()

        for name in ("categories", "channels"):
            try:
                self[name].enableAutoNavigation(False)
            except Exception:
                pass

        self.focus = "categories"
        self.update_headers()
        self.apply_focus()
        self.update_preview()

    # --------------------------------------------------------------- data
    def build(self):
        if self.backend is None:
            return
        self.update_source()
        self.categories = self.backend.live_categories()
        ids = [to_text(category.get("id")) for category in self.categories]
        if self.category_id not in ids:
            self.category_id = "all" if "all" in ids else (ids[0] if ids else "")
        self.render_categories()
        self.load_channels()

    def render_categories(self):
        entries = []
        for category in self.categories:
            entries.append(category_entry(
                292, 52, category.get("name") or u"",
                value=human_count(category.get("count")),
            ))
        self["categories"].setList(entries)
        index = 0
        for position, category in enumerate(self.categories):
            if to_text(category.get("id")) == self.category_id:
                index = position
                break
        if entries:
            try:
                self["categories"].setCurrentIndex(index)
            except Exception:
                pass
        self.update_headers()

    def _needs_async_channels(self):
        return (
            getattr(self.backend, "kind", "") == "mag"
            and not getattr(self.backend, "channels", None)
            and self.category_id not in ("all", "fav")
        )

    def load_channels(self, keep_key=None):
        if self.backend is None:
            self.items = []
            self.render_channels()
            return
        self._channel_request += 1
        request = self._channel_request
        category_id = self.category_id
        query = self.query
        self.status_text(_("Loading ..."))

        def done(items):
            if request != self._channel_request:
                return
            self.items = list(items)
            self.render_channels(keep_key)

        def failed(error):
            if request != self._channel_request:
                return
            self.status_text(u"")
            self.show_error(error)

        if self._needs_async_channels():
            # Do not leave the previous category's channels selectable while
            # the new MAG genre is still loading.
            self.items = []
            try:
                self["channels"].setList([])
            except Exception:
                pass
            self.update_headers()
            self.update_preview()
            network_timeout = safe_int(self.store.settings.get("timeout"), 20)
            limit = max(45, network_timeout * 3 + 10)
            self.run_async(
                lambda: self.backend.live_items(category_id, query),
                done, failed, timeout=limit,
            )
            return
        try:
            items = self.backend.live_items(category_id, query)
        except Exception as error:  # noqa: BLE001
            failed(error)
            return
        done(items)

    def render_channels(self, keep_key=None):
        entries = []
        target = 0
        for index, item in enumerate(self.items):
            favorite = False
            try:
                favorite = self.backend.is_favorite(item)
            except Exception:
                pass
            if keep_key and self._channel_key(item) == keep_key:
                target = index
            entries.append(channel_entry(
                412, 52, item.get("number") or index + 1,
                item.get("name") or u"", icon=self._channel_icon(item),
                favorite=favorite,
            ))
        self["channels"].setList(entries)
        if entries:
            try:
                self["channels"].setCurrentIndex(target)
            except Exception:
                pass
        self.update_headers()
        self.update_preview()
        if self.items:
            self.status_text(u"{0} {1}".format(len(self.items), _("channels")))
        else:
            self.status_text(_("No channels"))

    def _channel_key(self, item):
        return to_text(
            item.get("fav_key") or item.get("id") or item.get("url")
            or item.get("name")
        )

    def _channel_icon(self, item):
        logo = to_text(item.get("logo"))
        if logo:
            local = self.store.logo_file(logo)
            if os.path.exists(local):
                try:
                    from Tools.LoadPixmap import LoadPixmap
                    pointer = LoadPixmap(local)
                    if pointer is not None:
                        return pointer
                except Exception:
                    pass
        return pixmap("channel.png")

    # ------------------------------------------------------------ helpers
    def selected_category(self):
        try:
            index = self["categories"].getSelectedIndex()
        except Exception:
            return None
        if 0 <= index < len(self.categories):
            return self.categories[index]
        return None

    def selected_channel(self):
        try:
            index = self["channels"].getSelectedIndex()
        except Exception:
            return None
        if 0 <= index < len(self.items):
            return self.items[index]
        return None

    def current(self):
        return self.selected_channel()

    def update_headers(self):
        cat_prefix = u">  " if self.focus == "categories" else u""
        ch_prefix = u">  " if self.focus == "channels" else u""
        self["catHeader"].setText(u"{0}{1}  ({2})".format(
            cat_prefix, _("Categories"), len(self.categories)))
        self["chHeader"].setText(u"{0}{1}  ({2})".format(
            ch_prefix, _("Channels"), len(self.items)))

    def update_source(self):
        try:
            label = source_label(self.store.active_source())
        except Exception:
            label = u""
        label = to_text(label)
        if len(label) > 48:
            label = label[:45] + u"..."
        self["source"].setText(label)

    def update_search_text(self):
        if self.query:
            self["searchText"].setText(_("Search") + u": " + self.query)
        else:
            self["searchText"].setText(u"GREEN  " + _("Search channels"))

    def update_preview(self):
        item = self.selected_channel()
        category = self.selected_category()
        if item is None:
            name = (category or {}).get("name") or _("Live TV")
            self["previewKind"].setText(_("LIVE TV"))
            self["previewName"].setText(to_text(name))
            self["previewMeta"].setText(_("No channels"))
            self["previewUrl"].setText(u"")
            self["previewFav"].setText(u"")
            self["previewLogo"].instance.setPixmap(pixmap("channel.png"))
            self["playLabel"].setText(u"OK  " + _("Play"))
            self["favLabel"].setText(u"YELLOW  " + _("Add favorite"))
            return

        favorite = False
        try:
            favorite = self.backend.is_favorite(item)
        except Exception:
            pass
        meta = []
        if item.get("group"):
            meta.append(to_text(item["group"]))
        if item.get("number"):
            meta.append(u"#{0}".format(safe_int(item["number"])))
        self["previewKind"].setText(_("CHANNEL PREVIEW"))
        self["previewName"].setText(item.get("name") or u"")
        self["previewMeta"].setText(u"  \u2022  ".join(meta))
        url = to_text(item.get("url") or item.get("cmd") or u"")
        if len(url) > 62:
            url = url[:59] + u"..."
        self["previewUrl"].setText(url)
        self["previewFav"].setText(
            u"\u2605 " + _("Favorite") if favorite else u"")
        self["previewLogo"].instance.setPixmap(self._channel_icon(item))
        self["playLabel"].setText(u"OK  " + _("Play"))
        self["favLabel"].setText(
            u"YELLOW  " + (_("Remove favorite") if favorite else _("Add favorite")))

    def apply_focus(self):
        for name in ("categories", "channels"):
            try:
                self[name].selectionEnabled(name == self.focus)
            except Exception:
                pass

    def set_focus(self, focus):
        if focus == self.focus:
            return
        self.focus = focus
        self.apply_focus()
        self.update_headers()

    def category_changed(self, force=False):
        category = self.selected_category()
        if category is None:
            return
        new_id = to_text(category.get("id") or "all")
        if force or new_id != self.category_id:
            self.category_id = new_id
            self.load_channels()

    def move_selected(self, list_name, direction, page=False):
        widget = self[list_name]
        if direction == "up":
            widget.goLineUp()
        elif direction == "down":
            widget.goLineDown()
        elif direction == "page_up":
            widget.goPageUp()
        elif direction == "page_down":
            widget.goPageDown()
        elif direction == "top":
            widget.goTop()
        elif direction == "bottom":
            widget.goBottom()
        if list_name == "categories":
            self.category_changed()
        else:
            self.update_preview()

    # ------------------------------------------------------------- actions
    def key_up(self):
        self.move_selected("categories" if self.focus == "categories" else "channels", "up")

    def key_down(self):
        self.move_selected("categories" if self.focus == "categories" else "channels", "down")

    def key_page_up(self):
        self.move_selected("categories" if self.focus == "categories" else "channels", "page_up")

    def key_page_down(self):
        self.move_selected("categories" if self.focus == "categories" else "channels", "page_down")

    def key_top(self):
        self.move_selected("categories" if self.focus == "categories" else "channels", "top")

    def key_bottom(self):
        self.move_selected("categories" if self.focus == "categories" else "channels", "bottom")

    def key_left(self):
        if self.focus == "channels":
            self.set_focus("categories")

    def key_right(self):
        if self.focus == "categories":
            self.category_changed()
            self.set_focus("channels")

    def key_ok(self):
        if self.focus == "categories":
            self.category_changed()
            self.set_focus("channels")
            self.update_preview()
            return
        item = self.selected_channel()
        if item is not None:
            self.play_item(item)

    def key_back(self):
        self.close()

    def key_red(self):
        self.close()

    def key_green(self):
        self.ask_search()

    def key_yellow(self):
        item = self.selected_channel()
        if item is None:
            return
        key = self._channel_key(item)
        try:
            state = self.backend.toggle_favorite(item)
        except Exception as error:  # noqa: BLE001
            self.show_error(error)
            return
        try:
            self.categories = self.backend.live_categories()
        except Exception:
            pass
        self.render_categories()
        self.load_channels(keep_key=key)
        self.status_text(_("Added to favorites") if state else _("Removed from favorites"))

    def key_blue(self):
        self.query = u""
        self.update_search_text()
        self.reload_backend()

    def key_menu(self):
        pass

    def search_done(self, text):
        if text is None:
            return
        self.query = to_text(text).strip()
        self.update_search_text()
        self.load_channels()
        self.set_focus("channels")
        self.update_preview()


class VodCategoriesScreen(BackendScreen):
    def __init__(self, session, store, backend):
        BackendScreen.__init__(self, session, store, backend, _("Movies"),
                               source_label(store.active_source()), _("OK open  •  RED back"))
        self.set_hint(_("OK open  •  BLUE reload  •  RED back"))

    def build(self):
        categories = self.backend.vod_categories()
        rows = []
        entries = []
        for category in categories:
            rows.append(category)
            entries.append(row_entry(
                1200, 72, category.get("name") or "", icon=pixmap("folder.png"),
                icon_size=(44, 44), value=human_count(category.get("count")) if category.get("count") else None,
            ))
        self.set_entries(entries, rows)
        self.set_subtitle(u"{0} {1}".format(len(categories), _("categories")))
        if not rows:
            self.status_text(_("No movies"))

    def activate(self, row):
        self.open_child(VodScreen, row)

    def key_blue(self):
        self.reload_backend()


class VodScreen(BackendScreen):
    def __init__(self, session, store, backend, category):
        BackendScreen.__init__(self, session, store, backend, category.get("name") or _("Movies"),
                               u"", _("OK play  •  GREEN search  •  BLUE reload  •  RED back"))
        self.category = category
        self.items = []
        self.loaded_pages = 0

    def build(self):
        self.page = 1
        self.status_text(_("Loading ..."))
        self.run_async(lambda: self.backend.vod_items(self.category.get("id") or "all", u"", 1),
                       self._first_page, self._load_failed)

    def _first_page(self, result):
        items, total = result
        self.items = list(items)
        self.total = total
        self.loaded_pages = 1
        self.status_text(u"")
        self.render()

    def render(self):
        query = self.query.lower()
        visible = [item for item in self.items if not query or query in to_text(item.get("name")).lower()]
        rows = []
        entries = []
        for item in visible:
            rows.append(item)
            entries.append(row_entry(
                1200, 78, item.get("name") or "",
                subtitle=self._meta(item), icon=pixmap("movie.png"), icon_size=(46, 66),
            ))
        if len(self.items) < self.total:
            rows.append({"type": "more"})
            entries.append(row_entry(1200, 60, _("Load more ..."), icon=pixmap("more.png"), icon_size=(36, 36)))
        self.set_entries(entries, rows)
        subtitle = u"{0} {1}".format(self.total or len(self.items), _("movies"))
        if query:
            subtitle = u"{0}  \u2022  \"{1}\"".format(subtitle, self.query)
        self.set_subtitle(subtitle)
        if not visible and not (len(self.items) < self.total):
            self.status_text(_("No movies"))

    @staticmethod
    def _meta(item):
        parts = []
        if item.get("year"):
            parts.append(to_text(item["year"]))
        if item.get("genres"):
            parts.append(to_text(item["genres"]))
        if item.get("rating"):
            parts.append(u"\u2605 " + to_text(item["rating"]))
        return u"  \u2022  ".join(parts)

    def activate(self, row):
        if row.get("type") == "more":
            self.load_more()
            return
        self.open_child(InfoScreen, row)

    def load_more(self):
        self.page += 1
        self.status_text(_("Loading ..."))
        self.run_async(lambda: self.backend.vod_items(self.category.get("id") or "all", u"", self.page),
                       self._more_loaded, self._load_failed)

    def _more_loaded(self, result):
        items, total = result
        self.items.extend(items)
        self.total = total
        self.loaded_pages += 1
        self.status_text(u"")
        self.render()

    def key_green(self):
        self.ask_search()

    def key_blue(self):
        self.query = u""
        self.reload_backend()


class SeriesCategoriesScreen(BackendScreen):
    def __init__(self, session, store, backend):
        BackendScreen.__init__(self, session, store, backend, _("Series"),
                               source_label(store.active_source()), _("OK open  •  RED back"))
        self.set_hint(_("OK open  •  BLUE reload  •  RED back"))

    def build(self):
        categories = self.backend.series_categories()
        rows = []
        entries = []
        for category in categories:
            rows.append(category)
            entries.append(row_entry(
                1200, 72, category.get("name") or "", icon=pixmap("folder.png"),
                icon_size=(44, 44), value=human_count(category.get("count")) if category.get("count") else None,
            ))
        self.set_entries(entries, rows)
        self.set_subtitle(u"{0} {1}".format(len(categories), _("categories")))
        if not rows:
            self.status_text(_("No series"))

    def activate(self, row):
        self.open_child(SeriesScreen, row)

    def key_blue(self):
        self.reload_backend()


class SeriesScreen(BackendScreen):
    def __init__(self, session, store, backend, category):
        BackendScreen.__init__(self, session, store, backend, category.get("name") or _("Series"),
                               u"", _("OK open  •  GREEN search  •  BLUE reload  •  RED back"))
        self.category = category
        self.items = []
        self.total = 0

    def build(self):
        self.page = 1
        self.status_text(_("Loading ..."))
        self.run_async(lambda: self.backend.series_items(self.category.get("id") or "all", u"", 1),
                       self._first_page, self._load_failed)

    def _first_page(self, result):
        items, total = result
        self.items = list(items)
        self.total = total
        self.status_text(u"")
        self.render()

    def render(self):
        query = self.query.lower()
        visible = [item for item in self.items if not query or query in to_text(item.get("name")).lower()]
        rows = []
        entries = []
        for item in visible:
            rows.append(item)
            subtitle = u"{0} {1}".format(safe_int(item.get("count")), _("episodes"))
            if item.get("group"):
                subtitle = u"{0}  \u2022  {1}".format(item["group"], subtitle)
            entries.append(row_entry(
                1200, 78, item.get("name") or "", subtitle=subtitle,
                icon=pixmap("series_card.png"), icon_size=(46, 66),
            ))
        if len(self.items) < self.total:
            rows.append({"type": "more"})
            entries.append(row_entry(1200, 60, _("Load more ..."), icon=pixmap("more.png"), icon_size=(36, 36)))
        self.set_entries(entries, rows)
        subtitle = u"{0} {1}".format(self.total or len(self.items), _("series"))
        self.set_subtitle(subtitle)
        if not visible and not (len(self.items) < self.total):
            self.status_text(_("No series"))

    def activate(self, row):
        if row.get("type") == "more":
            self.load_more()
            return
        self.open_child(SeasonsScreen, row)

    def load_more(self):
        self.page += 1
        self.status_text(_("Loading ..."))
        self.run_async(lambda: self.backend.series_items(self.category.get("id") or "all", u"", self.page),
                       self._more_loaded, self._load_failed)

    def _more_loaded(self, result):
        items, total = result
        self.items.extend(items)
        self.total = total
        self.status_text(u"")
        self.render()

    def key_green(self):
        self.ask_search()

    def key_blue(self):
        self.query = u""
        self.reload_backend()


class SeasonsScreen(BackendScreen):
    def __init__(self, session, store, backend, series):
        BackendScreen.__init__(self, session, store, backend, series.get("name") or _("Series"),
                               u"", _("OK open  •  RED back"))
        self.series = series

    def build(self):
        self.status_text(_("Loading ..."))
        self.run_async(lambda: self.backend.seasons(self.series.get("id")), self._seasons_loaded, self._load_failed)

    def _seasons_loaded(self, seasons):
        self.status_text(u"")
        rows = []
        entries = []
        for season in seasons:
            rows.append(season)
            entries.append(row_entry(
                1200, 72, season.get("name") or "", icon=pixmap("folder.png"),
                icon_size=(44, 44), value=u"{0} {1}".format(safe_int(season.get("count")), _("episodes")),
            ))
        self.set_entries(entries, rows)
        self.set_subtitle(u"{0}  \u2022  {1} {2}".format(self.series.get("name") or "", len(seasons), _("Seasons")))
        if not rows:
            self.status_text(_("No episodes"))

    def activate(self, row):
        self.open_child(EpisodesScreen, self.series, row)


class EpisodesScreen(BackendScreen):
    def __init__(self, session, store, backend, series, season):
        BackendScreen.__init__(self, session, store, backend, series.get("name") or _("Series"),
                               u"", _("OK play  •  RED back"))
        self.series = series
        self.season = season
        self.items = []
        self.total = 0
        self.page = 1

    def build(self):
        self.status_text(_("Loading ..."))
        self.run_async(lambda: self.backend.episodes(self.series.get("id"), self.season.get("id"), 1),
                       self._first_page, self._load_failed)

    def _first_page(self, result):
        items, total = result
        self.items = list(items)
        self.total = total
        self.page = 1
        self.status_text(u"")
        self.render()

    def render(self):
        rows = []
        entries = []
        for item in self.items:
            rows.append(item)
            entries.append(row_entry(
                1200, 76, item.get("name") or "",
                subtitle=item.get("description") or item.get("genres") or _("Episode"),
                icon=pixmap("episode.png"), icon_size=(44, 44),
            ))
        if len(self.items) < self.total:
            rows.append({"type": "more"})
            entries.append(row_entry(1200, 60, _("Load more ..."), icon=pixmap("more.png"), icon_size=(36, 36)))
        self.set_entries(entries, rows)
        self.set_subtitle(u"{0}  \u2022  {1} {2}".format(
            self.season.get("name") or "", len(self.items), _("episodes")))
        if not rows:
            self.status_text(_("No episodes"))

    def activate(self, row):
        if row.get("type") == "more":
            self.page += 1
            self.status_text(_("Loading ..."))
            self.run_async(lambda: self.backend.episodes(self.series.get("id"), self.season.get("id"), self.page),
                           self._more_loaded, self._load_failed)
            return
        self.play_item(row)

    def _more_loaded(self, result):
        items, total = result
        self.items.extend(items)
        self.total = total
        self.status_text(u"")
        self.render()
