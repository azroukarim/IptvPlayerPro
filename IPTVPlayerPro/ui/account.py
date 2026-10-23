# -*- coding: utf-8 -*-
"""Account screen: portal details, reload and account check."""

from __future__ import absolute_import

import time

from Components.ActionMap import HelpableActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ScrollLabel import ScrollLabel

from ..core.backends import source_label, source_summary
from ..core.i18n import _
from ..core.util import human_age, human_expiry, is_expired, safe_int, to_text
from .base import (AsyncScreen, MultiList, info_box, pixmap, row_entry,
                   set_background, set_logo, yes_no)
from .skins import ACCOUNT_SKIN


class AccountScreen(AsyncScreen):
    skin = ACCOUNT_SKIN

    def __init__(self, session, store, backend):
        AsyncScreen.__init__(self, session)
        self.skinName = "IPTVProAccount"
        self.store = store
        self.backend = backend
        self.rows = []

        self["bg"] = Pixmap()
        self["logo"] = Pixmap()
        self["title"] = Label()
        self["subtitle"] = Label()
        self["status"] = Label()
        self["details"] = ScrollLabel()
        self["hint"] = Label()
        self["list"] = MultiList(54)

        self["title"].setText(_("Account information"))
        self["hint"].setText(_("OK select  •  RED back"))
        self["actions"] = HelpableActionMap(self, [
            "NavigationActions", "OkCancelActions", "ColorActions",
        ], {
            "up": self.key_up,
            "down": self.key_down,
            "ok": self.key_ok,
            "cancel": self.close,
            "red": self.close,
        }, prio=0, description=_("IPTV Player Pro"))

        self.build_actions()
        self.onLayoutFinish.append(self.layout_ready)

    def layout_ready(self):
        set_background(self)
        set_logo(self)
        try:
            self["list"].enableAutoNavigation(False)
        except Exception:
            pass
        self.refresh_details()

    # -------------------------------------------------------------- details
    def refresh_details(self):
        source = self.store.active_source()
        if not source:
            self["subtitle"].setText(_("No playlist selected"))
            self["status"].setText(u"")
            self["details"].setText(_("No active playlist"))
            return
        self["subtitle"].setText(source_label(source))
        self["status"].setText(source_summary(source, self.store))
        info = source.get("info") or {}
        expires = info.get("expires") or ""
        status = info.get("status") or ""
        if status == "expired" or is_expired(expires):
            status_text = _("Expired")
        elif status == "error":
            status_text = _("Portal error")
        elif source.get("type") == "m3u":
            status_text = _("Active") if safe_int(info.get("channels")) else _("Not loaded yet")
        else:
            status_text = _("Active") if status else _("Unknown")
        lines = [
            u"{0}: {1}".format(_("Source"), source.get("name") or ""),
            u"{0}: {1}".format(_("Type"), _("MAG portal") if source.get("type") == "mag" else _("M3U playlist")),
            u"{0}: {1}".format(_("URL"), source.get("url") or ""),
        ]
        if source.get("type") == "mag":
            lines.append(u"{0}: {1}".format(_("MAC"), source.get("mac") or ""))
        lines.append(u"{0}: {1}".format(_("Status"), status_text))
        if expires:
            lines.append(u"{0}: {1}".format(_("Expires"), human_expiry(expires)))
        counts = self.backend.counts() if self.backend else {}
        channels = safe_int(info.get("channels")) or safe_int(counts.get("live"))
        movies = safe_int(info.get("vod")) or safe_int(counts.get("vod"))
        series = safe_int(info.get("series")) or safe_int(counts.get("series"))
        lines.append(u"{0}: {1}   \u2022   {2}: {3}   \u2022   {4}: {5}".format(
            _("Channels"), channels, _("Movies"), movies, _("Series"), series))
        updated = info.get("updated") or source.get("updated")
        if updated:
            try:
                stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(safe_int(updated)))
            except Exception:
                stamp = human_age(updated)
            lines.append(u"{0}: {1}".format(_("Last update"), stamp))
        self["details"].setText(u"\n".join(lines))

    # -------------------------------------------------------------- actions
    def build_actions(self):
        actions = []
        if self.backend is not None:
            actions.append({"key": "reload", "name": _("Reload portal"), "icon": "reload.png"})
            actions.append({"key": "check", "name": _("Check account"), "icon": "account.png"})
        actions.append({"key": "server", "name": _("Change Server"), "icon": "server.png"})
        actions.append({"key": "close", "name": _("Close"), "icon": "exit.png"})
        self.rows = actions
        entries = []
        for action in actions:
            entries.append(row_entry(1200, 54, action["name"], icon=pixmap(action["icon"]), icon_size=(32, 32)))
        self["list"].setList(entries)
        if entries:
            self["list"].setCurrentIndex(0)

    def key_up(self):
        self["list"].goLineUp()

    def key_down(self):
        self["list"].goLineDown()

    def key_ok(self):
        try:
            index = self["list"].getSelectedIndex()
        except Exception:
            index = -1
        if 0 <= index < len(self.rows):
            self.activate(self.rows[index])

    def activate(self, row):
        key = row.get("key")
        if key == "close":
            self.close()
        elif key == "server":
            from .sources import SourcesScreen
            self.session.openWithCallback(self.sources_closed, SourcesScreen, self.store)
        elif key == "reload":
            yes_no(self.session, _("Reload portal") + u"?", self._reload_confirmed)
        elif key == "check":
            self.check_account()

    def sources_closed(self, result=None):
        if result == "zapped":
            self.close("zapped")
        elif result == "changed":
            self.close("changed")

    def _reload_confirmed(self, answer):
        if not answer or self.backend is None:
            return
        self["status"].setText(_("Reloading portal ..."))
        self.run_async(lambda: self.backend.refresh(force=True), self._reloaded, self._failed)

    def _reloaded(self, _result):
        self.refresh_details()
        info_box(self.session, _("Refresh finished"))
        self.build_actions()

    def _failed(self, error):
        self.refresh_details()
        self.show_error(error)

    def check_account(self):
        source = self.store.active_source()
        if not source:
            return
        if source.get("type") != "mag":
            info_box(self.session, _("This source is an M3U playlist and has no portal account."))
            return
        if self.backend is None:
            return
        self["status"].setText(_("Checking account ..."))
        self.run_async(lambda: self.backend.check_account(), self._checked, self._failed)

    def _checked(self, info):
        self.refresh_details()
        expires = (info or {}).get("expires") or ""
        if expires and is_expired(expires):
            message = _("Account has expired") + u"\n" + _("Expires") + ": " + human_expiry(expires)
        elif expires:
            message = _("Account is active") + u"\n" + _("Expires") + ": " + human_expiry(expires)
        else:
            message = _("Account status unknown")
        info_box(self.session, message, timeout=8)
