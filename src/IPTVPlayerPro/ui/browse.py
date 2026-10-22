# -*- coding: utf-8 -*-
"""Browse screens: live TV, movies and series."""

from __future__ import absolute_import

import os

from enigma import eRect, eTimer

from Components.ActionMap import HelpableActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.VideoWindow import VideoWindow
from Screens.VirtualKeyBoard import VirtualKeyBoard

from ..core.backends import source_label
from ..core.i18n import _
from ..core.util import human_count, safe_int, to_text
from .base import (AsyncScreen, ListScreen, LiveList, category_entry,
                   channel_entry, info_box, pixmap, play_url, row_entry)
from .info import InfoScreen
from .skins import LIVE_SKIN


# Channel logos are decoded at their original size.  Some providers ship very
# large PNGs, so loading a logo for every channel in a big playlist can exhaust
# the 32-bit Python process.  Keep real logos only around the selected row; the
# rest of the list uses the small built-in placeholder.
LIVE_ICON_RADIUS = 12

# The preview rectangle in the 1280x720 skin.  The matching skin widget owns
# the actual hardware video window; this constant documents the geometry used
# by the background images as well.
LIVE_VIDEO_RECT = (744, 104, 512, 300)


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
        user_agent, options = self.stream_options(item)
        try:
            play_url(self.session, url, safe_int(self.store.settings.get("service_type"), 4097),
                     item.get("name"), user_agent, options)
        except Exception as error:  # noqa: BLE001
            self.show_error(error)
            return
        if self.store.settings.get("close_after_zap", True):
            self.close("zapped")

    def stream_options(self, item):
        try:
            return self.backend.stream_options(item)
        except Exception:
            return (to_text(item.get("ua") or item.get("stream_ua")),
                    to_text(item.get("opts") or item.get("stream_opts")))

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
                    pointer = LoadPixmap(local, cached=False)
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
        self.browser_items = []
        self.category_id = "all"
        self.focus = "categories"
        self._channel_request = 0
        self._channel_source = []
        self._row_offset = 0
        self._icon_start = 0
        self._icon_end = 0
        self._preview_active = False
        self._preview_timer = None
        self._preview_attempts = 0

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
        # decoder=0 is the main video decoder.  The widget only moves the live
        # video plane into the right-hand preview rectangle; it does not start
        # a second stream or a second decoder.  It is hidden until the user
        # selects a channel so the current TV service stays untouched while
        # browsing.
        self["previewVideo"] = VideoWindow(decoder=0, fb_width=1280, fb_height=720)
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
        # Returning from a dialog re-shows the screen.  Re-apply the preview
        # immediately instead of waiting for the keep-alive timer.
        self.onShow.append(self._preview_shown)
        # Restore the main video plane before the screen and its video widget
        # are destroyed, otherwise some Broadcom images leave the selected
        # service in the small preview rectangle.
        self.onClose.append(self.stop_preview)
        # Clear the page rows while the screen is being destroyed: doing this
        # immediately after playService() can disturb the freshly started
        # service on some images.
        self.onClose.append(self.release_channel_rows)

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
        self["hint"].setText(_("OK mini TV  •  GREEN search  •  YELLOW favorite  •  BLUE reload  •  RED back"))
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
        # The video widget is part of the widget tree but must stay inactive
        # until a channel is explicitly played in the mini TV.
        self._restore_fullscreen_video()

    # ---------------------------------------------------------- mini TV
    def _video_instance(self):
        widget = self.get("previewVideo")
        return getattr(widget, "instance", None) if widget is not None else None

    def _set_visible(self, name, visible):
        widget = self.get(name)
        if widget is None:
            return
        try:
            if visible:
                widget.show()
            else:
                widget.hide()
        except Exception:
            pass

    def _aml_video(self):
        return os.path.exists("/sys/class/video/axis")

    def _preview_rect(self):
        """Return the preview rectangle in the destination coordinate space.

        Amlogic images take skin coordinates in setFullScreenPosition() and
        scale them to the desktop.  Broadcom and other legacy images use the
        720x576 video destination space directly.
        """
        left, top, width, height = LIVE_VIDEO_RECT
        if self._aml_video():
            return eRect(left, top, width, height)
        return eRect(
            left * 720 // 1280,
            top * 576 // 720,
            width * 720 // 1280,
            height * 576 // 720,
        )

    def _legacy_rect_matches(self, left, top, width, height):
        """Return True when the Broadcom destination already has this rect.

        Checking first avoids re-writing /proc (and potentially glitching the
        picture) on every keep-alive tick once the stream has settled.
        """
        if self._aml_video():
            return False
        base = "/proc/stb/vmpeg/0/dst_"
        for name, expected in (("left", left), ("top", top),
                               ("width", width), ("height", height)):
            try:
                handle = open(base + name, "r")
                try:
                    current = int(handle.read().strip(), 16)
                finally:
                    handle.close()
            except Exception:
                return False
            if current != int(expected):
                return False
        return True

    def _write_legacy_video_rect(self, left, top, width, height):
        """Write the Broadcom /proc destination directly.

        This bypasses older eVideoWidget implementations that only remember
        setFullScreenPosition() without applying it.  It also survives the
        destination resets that some 4097 handlers perform while starting a
        stream.  Amlogic and any image without these proc files are untouched.
        """
        if self._aml_video():
            return False
        base = "/proc/stb/vmpeg/0/dst_"
        if not os.path.exists(base + "left"):
            return False
        values = (("left", left), ("top", top), ("width", width),
                  ("height", height), ("apply", 1))
        try:
            for name, value in values:
                handle = open(base + name, "w")
                try:
                    handle.write("%08x\n" % int(value))
                finally:
                    handle.close()
            return True
        except Exception:
            return False

    def _apply_preview_video(self):
        """Force the main video plane into the preview pane.

        The skin widget applies its rectangle when shown, but some 4097
        service handlers reset the destination after the stream starts.  Some
        images also ignore the geometry of a widget that was hidden during
        layout.  Set the widget geometry explicitly, write the hardware
        destination, and keep re-applying it while the stream settles.
        """
        widget = self.get("previewVideo")
        instance = self._video_instance()
        if widget is None or instance is None:
            self._log_preview("no video widget")
            return

        # Show the widget so the OSD keeps its video cut-out.  Do not move or
        # resize it here: the skin engine has already scaled its rectangle to
        # the real desktop, while LIVE_VIDEO_RECT is in 1280x720 skin
        # coordinates.  Moving it with skin coordinates would shift the
        # cut-out on FHD/UHD desktops.
        try:
            widget.show()
        except Exception:
            pass

        rect = self._preview_rect()
        if not self._legacy_rect_matches(rect.left(), rect.top(),
                                         rect.width(), rect.height()):
            try:
                instance.setFullScreenPosition(rect)
            except Exception as error:  # noqa: BLE001
                self._log_preview("setFullScreenPosition failed: {0}".format(error))

            if not self._aml_video():
                # Older Broadcom images apply the stored rectangle through
                # restoreFullsize(); current images are already handled above.
                try:
                    instance.restoreFullsize()
                except Exception:
                    pass
                self._write_legacy_video_rect(rect.left(), rect.top(),
                                              rect.width(), rect.height())

    def _restore_fullscreen_video(self):
        widget = self.get("previewVideo")
        instance = self._video_instance()
        if instance is not None:
            # setFullScreenPosition() writes the legacy 720x576 destination
            # immediately and scales correctly on AML.  It also stores the
            # position used by the widget's delayed restore timer.
            aml = self._aml_video()
            full = eRect(0, 0, 1280, 720) if aml else eRect(0, 0, 720, 576)
            try:
                instance.setFullScreenPosition(full)
            except Exception:
                pass
            try:
                instance.restoreFullsize()
            except Exception:
                pass
            if not aml:
                self._write_legacy_video_rect(0, 0, 720, 576)
        if widget is not None:
            try:
                widget.hide()
            except Exception:
                pass

    def _log_preview(self, message):
        """Write a few diagnostics lines that can be collected from /tmp."""
        try:
            instance = self._video_instance()
            parts = [message]
            if instance is not None:
                try:
                    position = instance.position()
                    size = instance.size()
                    parts.append("widget={0},{1} {2}x{3}".format(
                        position.x(), position.y(), size.width(), size.height()))
                except Exception:
                    pass
            parts.append("aml={0}".format(self._aml_video()))
            for name in ("left", "top", "width", "height"):
                try:
                    handle = open("/proc/stb/vmpeg/0/dst_" + name, "r")
                    try:
                        parts.append("{0}={1}".format(name, handle.read().strip()))
                    finally:
                        handle.close()
                except Exception:
                    break
            handle = open("/tmp/iptvplayerpro-mini.log", "ab")
            try:
                handle.write((u" | ".join(parts) + u"\n").encode("utf-8"))
            finally:
                handle.close()
        except Exception:
            pass

    def _preview_shown(self):
        if self._preview_active:
            self._apply_preview_video()

    def _show_preview_video(self):
        self._preview_active = True
        self._set_visible("preview", False)
        self._set_visible("previewLogo", False)
        self._set_visible("previewKind", False)
        self._apply_preview_video()
        self._log_preview("preview start")
        if self._preview_timer is None:
            try:
                self._preview_timer = eTimer()
                self._preview_timer.callback.append(self._reapply_preview)
            except Exception:
                self._preview_timer = None
        if self._preview_timer is not None:
            try:
                self._preview_timer.stop()
            except Exception:
                pass
            # Some stream handlers reset the destination after playService()
            # and some reset it again while zapping.  Poll quickly while the
            # stream starts, then keep a slow keep-alive for the whole preview.
            # On Broadcom the apply method reads /proc first and only writes
            # when the rectangle changed.  On Amlogic repeated axis writes can
            # be visible, so stop after the initial ten seconds there.
            self._preview_attempts = 20
            try:
                self._preview_timer.start(500, False)
            except Exception:
                self._preview_attempts = 0

    def _reapply_preview(self):
        if not self._preview_active:
            try:
                self._preview_timer.stop()
            except Exception:
                pass
            return
        self._apply_preview_video()
        if self._preview_attempts > 0:
            self._preview_attempts -= 1
            if self._preview_attempts == 0:
                try:
                    if self._aml_video():
                        self._preview_timer.stop()
                    else:
                        self._preview_timer.start(2000, False)
                except Exception:
                    pass

    def stop_preview(self):
        self._preview_active = False
        self._preview_attempts = 0
        if self._preview_timer is not None:
            try:
                self._preview_timer.stop()
            except Exception:
                pass
            self._preview_timer = None
        self._restore_fullscreen_video()
        self._log_preview("preview stop")
        self._set_visible("previewVideo", False)
        self._set_visible("preview", True)
        self._set_visible("previewLogo", True)
        self._set_visible("previewKind", True)

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

    def channel_page_size(self):
        size = safe_int(self.store.settings.get("page_size"), 300)
        return max(50, min(1000, size))

    def load_channels(self, keep_key=None, keep_page=False):
        if self.backend is None:
            self._channel_source = []
            self.total = 0
            self.browser_items = []
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
            self.apply_channel_items(items, keep_key=keep_key, keep_page=keep_page)

        def failed(error):
            if request != self._channel_request:
                return
            self._channel_source = []
            self.total = 0
            self.browser_items = []
            try:
                self["channels"].setList([])
            except Exception:
                pass
            self.update_headers()
            self.update_preview()
            self.status_text(u"")
            self.show_error(error)

        if self._needs_async_channels():
            # Do not leave the previous category's channels selectable while
            # the new MAG genre is still loading.
            self._channel_source = []
            self.total = 0
            self.browser_items = []
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

    def apply_channel_items(self, items, keep_key=None, keep_page=False):
        """Keep only one page of rows in the list widget.

        A large M3U file can contain tens of thousands of channels.  Building
        a MultiContent row for every one of them at once can exhaust memory on
        a 32-bit receiver, so rows are loaded a page at a time.  The full
        channel list is only kept as references for paging and searching.
        """
        self._channel_source = items
        self.total = len(items)
        size = self.channel_page_size()
        page = 1
        target = 0
        if keep_key:
            for index, item in enumerate(items):
                if self._channel_key(item) == keep_key:
                    target = index
                    page = index // size + 1
                    break
        elif keep_page:
            pages = max(1, (self.total + size - 1) // size)
            page = max(1, min(self.page, pages))
        start = (page - 1) * size
        self.page = page
        self._row_offset = start
        self.browser_items = items[start:start + size]
        target_index = max(0, target - start)
        if target_index >= len(self.browser_items):
            target_index = 0
        self.render_channels(select_index=target_index)

    def load_more_channels(self):
        if len(self.browser_items) >= self.total:
            return
        start = len(self.browser_items)
        end = start + self.channel_page_size()
        more = self._channel_source[start:end]
        if not more:
            return
        self.page += 1
        self.browser_items.extend(more)
        self.render_channels(select_index=start)

    def render_channels(self, keep_key=None, select_index=None):
        target = 0
        if select_index is not None:
            target = max(0, select_index)
        elif keep_key:
            for index, item in enumerate(self.browser_items):
                if self._channel_key(item) == keep_key:
                    target = index
                    break
        if self.browser_items:
            target = min(target, len(self.browser_items) - 1)
        else:
            target = 0
        self._icon_start = max(0, target - LIVE_ICON_RADIUS)
        self._icon_end = min(len(self.browser_items), target + LIVE_ICON_RADIUS + 1)
        placeholder = pixmap("channel.png")
        entries = []
        for index, item in enumerate(self.browser_items):
            favorite = False
            try:
                favorite = self.backend.is_favorite(item)
            except Exception:
                pass
            icon = placeholder
            if self._icon_start <= index < self._icon_end:
                icon = self._channel_icon(item)
            entries.append(channel_entry(
                412, 52, item.get("number") or (self._row_offset + index + 1),
                item.get("name") or u"", icon=icon,
                favorite=favorite,
            ))
        if len(self.browser_items) < self.total:
            entries.append(channel_entry(
                412, 52, 0, _("Load more ..."),
                icon=pixmap("more.png"),
            ))
        self["channels"].setList(entries)
        if entries:
            try:
                self["channels"].setCurrentIndex(target)
            except Exception:
                pass
        self.update_headers()
        self.update_preview()
        if self.browser_items:
            loaded = self.loaded_count()
            if loaded < self.total:
                self.status_text(u"{0} / {1} {2}".format(
                    loaded, self.total, _("channels")))
            else:
                self.status_text(u"{0} {1}".format(self.total, _("channels")))
        else:
            self.status_text(_("No channels"))

    def release_channel_rows(self):
        """Drop the page data before handing the screen back to Enigma2."""
        self._channel_source = []
        self.total = 0
        self.browser_items = []
        self._row_offset = 0
        self._icon_start = 0
        self._icon_end = 0
        try:
            self["channels"].setList([])
        except Exception:
            pass
        try:
            self["previewLogo"].instance.setPixmap(pixmap("channel.png"))
        except Exception:
            pass

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
                    pointer = LoadPixmap(local, cached=False)
                    if pointer is not None:
                        return pointer
                except Exception:
                    pass
        return pixmap("channel.png")

    def _play(self, url, item):
        """Play a Live TV channel in the right-hand mini TV pane.

        The old two-screen flow closed the list after a successful zap.  The
        three-column browser must stay open so the user can keep browsing
        while the channel is visible in the preview pane.  Movies and series
        retain their normal full-screen playback behaviour.
        """
        self.status_text(u"")
        user_agent, options = self.stream_options(item)
        service_type = safe_int(self.store.settings.get("service_type"), 4097)
        self._log_preview("play engine={0}".format(service_type))
        try:
            play_url(self.session, url, service_type,
                     item.get("name"), user_agent, options)
        except Exception as error:  # noqa: BLE001
            # A failed stream must never close the plugin.  Restore the
            # placeholder and leave the browser usable.
            self.stop_preview()
            self.show_error(error)
            return
        self._show_preview_video()
        self.status_text(_("Playing in mini TV"))

    def refresh_icon_window(self):
        """Load logos only for a small window around the selected channel."""
        if not self.browser_items:
            return
        try:
            index = self["channels"].getSelectedIndex()
        except Exception:
            return
        if index >= len(self.browser_items):
            # The "Load more ..." row has no channel logo.
            return
        if self._icon_start <= index < self._icon_end:
            return
        item = self.selected_channel()
        key = self._channel_key(item) if item is not None else None
        self.render_channels(keep_key=key)

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
        if 0 <= index < len(self.browser_items):
            return self.browser_items[index]
        return None

    def selected_is_more(self):
        if len(self.browser_items) >= self.total:
            return False
        try:
            index = self["channels"].getSelectedIndex()
        except Exception:
            return False
        return index >= len(self.browser_items)

    def loaded_count(self):
        return min(self.total, self._row_offset + len(self.browser_items))

    def current(self):
        return self.selected_channel()

    def update_headers(self):
        cat_prefix = u">  " if self.focus == "categories" else u""
        ch_prefix = u">  " if self.focus == "channels" else u""
        loaded = self.loaded_count()
        if loaded < self.total:
            channel_count = u"{0}/{1}".format(loaded, self.total)
        else:
            channel_count = u"{0}".format(self.total or loaded)
        self["catHeader"].setText(u"{0}{1}  ({2})".format(
            cat_prefix, _("Categories"), len(self.categories)))
        self["chHeader"].setText(u"{0}{1}  ({2})".format(
            ch_prefix, _("Channels"), channel_count))

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
        if self.selected_is_more():
            self["previewKind"].setText(_("Channels"))
            self["previewName"].setText(_("Load more ..."))
            self["previewMeta"].setText(u"{0} / {1} {2}".format(
                self.loaded_count(), self.total, _("channels")))
            self["previewUrl"].setText(u"")
            self["previewFav"].setText(u"")
            self["previewLogo"].instance.setPixmap(pixmap("more.png"))
            self["playLabel"].setText(u"OK  " + _("Load more ..."))
            self["favLabel"].setText(u"")
            return
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
            self.refresh_icon_window()
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
        if self.selected_is_more():
            self.load_more_channels()
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
        if self.selected_is_more():
            return
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
        self.load_channels(keep_key=key, keep_page=True)
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
        self.browser_items = []
        self.loaded_pages = 0

    def build(self):
        self.page = 1
        self.status_text(_("Loading ..."))
        self.run_async(lambda: self.backend.vod_items(self.category.get("id") or "all", self.query, 1),
                       self._first_page, self._load_failed)

    def _first_page(self, result):
        items, total = result
        self.browser_items = list(items)
        self.total = total
        self.loaded_pages = 1
        self.status_text(u"")
        self.render()

    def render(self):
        query = self.query.lower()
        visible = [item for item in self.browser_items if not query or query in to_text(item.get("name")).lower()]
        rows = []
        entries = []
        for item in visible:
            rows.append(item)
            entries.append(row_entry(
                1200, 78, item.get("name") or "",
                subtitle=self._meta(item), icon=pixmap("movie.png"), icon_size=(46, 66),
            ))
        if len(self.browser_items) < self.total:
            rows.append({"type": "more"})
            entries.append(row_entry(1200, 60, _("Load more ..."), icon=pixmap("more.png"), icon_size=(36, 36)))
        self.set_entries(entries, rows)
        subtitle = u"{0} {1}".format(self.total or len(self.browser_items), _("movies"))
        if query:
            subtitle = u"{0}  \u2022  \"{1}\"".format(subtitle, self.query)
        self.set_subtitle(subtitle)
        if not visible and not (len(self.browser_items) < self.total):
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
        self.run_async(lambda: self.backend.vod_items(self.category.get("id") or "all", self.query, self.page),
                       self._more_loaded, self._load_failed)

    def _more_loaded(self, result):
        items, total = result
        self.browser_items.extend(items)
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
        self.browser_items = []
        self.total = 0

    def build(self):
        self.page = 1
        self.status_text(_("Loading ..."))
        self.run_async(lambda: self.backend.series_items(self.category.get("id") or "all", self.query, 1),
                       self._first_page, self._load_failed)

    def _first_page(self, result):
        items, total = result
        self.browser_items = list(items)
        self.total = total
        self.status_text(u"")
        self.render()

    def render(self):
        query = self.query.lower()
        visible = [item for item in self.browser_items if not query or query in to_text(item.get("name")).lower()]
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
        if len(self.browser_items) < self.total:
            rows.append({"type": "more"})
            entries.append(row_entry(1200, 60, _("Load more ..."), icon=pixmap("more.png"), icon_size=(36, 36)))
        self.set_entries(entries, rows)
        subtitle = u"{0} {1}".format(self.total or len(self.browser_items), _("series"))
        self.set_subtitle(subtitle)
        if not visible and not (len(self.browser_items) < self.total):
            self.status_text(_("No series"))

    def activate(self, row):
        if row.get("type") == "more":
            self.load_more()
            return
        self.open_child(SeasonsScreen, row)

    def load_more(self):
        self.page += 1
        self.status_text(_("Loading ..."))
        self.run_async(lambda: self.backend.series_items(self.category.get("id") or "all", self.query, self.page),
                       self._more_loaded, self._load_failed)

    def _more_loaded(self, result):
        items, total = result
        self.browser_items.extend(items)
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
        self.browser_items = []
        self.total = 0
        self.page = 1

    def build(self):
        self.status_text(_("Loading ..."))
        self.run_async(lambda: self.backend.episodes(self.series.get("id"), self.season.get("id"), 1),
                       self._first_page, self._load_failed)

    def _first_page(self, result):
        items, total = result
        self.browser_items = list(items)
        self.total = total
        self.page = 1
        self.status_text(u"")
        self.render()

    def render(self):
        rows = []
        entries = []
        for item in self.browser_items:
            rows.append(item)
            entries.append(row_entry(
                1200, 76, item.get("name") or "",
                subtitle=item.get("description") or item.get("genres") or _("Episode"),
                icon=pixmap("episode.png"), icon_size=(44, 44),
            ))
        if len(self.browser_items) < self.total:
            rows.append({"type": "more"})
            entries.append(row_entry(1200, 60, _("Load more ..."), icon=pixmap("more.png"), icon_size=(36, 36)))
        self.set_entries(entries, rows)
        self.set_subtitle(u"{0}  \u2022  {1} {2}".format(
            self.season.get("name") or "", len(self.browser_items), _("episodes")))
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
        self.browser_items.extend(items)
        self.total = total
        self.status_text(u"")
        self.render()
