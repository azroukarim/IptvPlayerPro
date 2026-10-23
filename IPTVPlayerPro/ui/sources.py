# -*- coding: utf-8 -*-
"""Server / playlist management."""

from __future__ import absolute_import

import re

from Screens.ChoiceBox import ChoiceBox
from Screens.VirtualKeyBoard import VirtualKeyBoard

from ..core.backends import create_backend, source_summary
from ..core.epg import clean_epg_urls
from ..core.i18n import _
from ..core.mag import is_valid_mac, normalize_mac, normalize_portal
from ..core.util import human_age, human_expiry, is_expired, to_text
from .base import ListScreen, info_box, pixmap, row_entry, yes_no


def _valid_url(value):
    return bool(re.match(r"(?i)^https?://[^\s/]+", to_text(value).strip()))


class SourcesScreen(ListScreen):
    def __init__(self, session, store):
        ListScreen.__init__(self, session, _("Servers / Playlists"), _("Your playlists and portals"),
                            _("OK select  •  MENU edit  •  GREEN add M3U  •  BLUE add MAG  •  RED delete"))
        self.store = store
        self.changed = False
        self.rebuild()

    # -------------------------------------------------------------- render
    def rebuild(self):
        sources = self.store.sources
        active = self.store.active_id()
        rows = []
        entries = []
        for source in sources:
            rows.append(source)
            kind = _("MAG portal") if source.get("type") == "mag" else _("M3U playlist")
            subtitle = u"{0}  \u2022  {1}".format(kind, to_text(source.get("url")).split("//")[-1][:48])
            info = source.get("info") or {}
            value = ""
            if source.get("id") == active:
                value = u"\u25cf " + _("Active")
            elif source.get("type") == "mag" and info.get("expires"):
                value = human_expiry(info.get("expires"))
            elif info.get("updated"):
                value = human_age(info.get("updated"))
            entries.append(row_entry(
                1200, 76, source.get("name") or "", subtitle=subtitle,
                icon=pixmap("mag.png") if source.get("type") == "mag" else pixmap("m3u.png"),
                icon_size=(46, 46), value=value,
            ))
        if not sources:
            rows.append({"id": "", "type": "add_m3u", "name": _("Add M3U playlist")})
            entries.append(row_entry(1200, 76, _("Add M3U playlist"),
                                     subtitle=_("Add your first M3U playlist or MAG portal."),
                                     icon=pixmap("m3u.png"), icon_size=(46, 46)))
            rows.append({"id": "", "type": "add_mag", "name": _("Add MAG portal")})
            entries.append(row_entry(1200, 76, _("Add MAG portal"),
                                     subtitle=_("MAC based Stalker portal"),
                                     icon=pixmap("mag.png"), icon_size=(46, 46)))
        self.set_entries(entries, rows)
        self.set_subtitle(u"{0} {1}".format(len(sources), _("Servers / Playlists")))
        self.status_text(source_summary(self.store.active_source(), self.store) if sources else _("No sources yet"))

    # ------------------------------------------------------------- actions
    def activate(self, row):
        kind = row.get("type")
        if kind == "add_m3u":
            self.add_m3u()
            return
        if kind == "add_mag":
            self.add_mag()
            return
        self.store.set_active(row.get("id"))
        self.changed = True
        self.close("changed")

    def key_menu(self):
        source = self.current()
        if not source or not source.get("id"):
            return
        options = [
            (_("Change name"), "name"),
            (_("Change URL"), "url"),
        ]
        if source.get("type") == "mag":
            options.append((_("Change MAC"), "mac"))
        options += [
            (_("Change EPG URL"), "epg_url"),
            (_("Change user-agent"), "ua"),
            (_("Refresh now"), "refresh"),
            (_("Delete"), "delete"),
        ]
        self.session.openWithCallback(
            lambda result: self._edit_action(source.get("id"), result),
            ChoiceBox, title=_("Edit source"), list=options,
        )

    def _edit_action(self, source_id, action):
        source = self.store.get_source(source_id)
        if not source or not action:
            return
        if action == "delete":
            yes_no(self.session, _("Delete this source?") + u"\n" + to_text(source.get("name")),
                   lambda answer: self._delete_confirmed(source_id, answer))
        elif action == "name":
            self._ask(_("Change name"), source.get("name") or "", lambda text: self._save_name(source_id, text))
        elif action == "url":
            self._ask(_("Change URL"), source.get("url") or "", lambda text: self._save_url(source_id, text))
        elif action == "mac":
            self._ask(_("MAC address"), source.get("mac") or "00:1A:79:", lambda text: self._save_mac(source_id, text))
        elif action == "epg_url":
            self._ask(_("EPG URL (optional)"), source.get("epg_url") or "",
                      lambda text: self._save_epg_url(source_id, text))
        elif action == "ua":
            self._ask(_("User-Agent (optional)"), source.get("ua") or "", lambda text: self._save_ua(source_id, text))
        elif action == "refresh":
            self._refresh(source_id)

    def _delete_confirmed(self, source_id, answer):
        if not answer:
            return
        self.store.delete_source(source_id)
        self.changed = True
        self.rebuild()
        info_box(self.session, _("Saved"))

    def _save_name(self, source_id, text):
        if text is None:
            return
        name = to_text(text).strip()
        if not name:
            return
        self.store.update_source(source_id, name=name)
        self.changed = True
        self.rebuild()

    def _save_url(self, source_id, text):
        if text is None:
            return
        source = self.store.get_source(source_id)
        value = to_text(text).strip()
        if not _valid_url(value):
            info_box(self.session, _("Invalid URL") + u"\n" + _("The address must start with http:// or https://"))
            self._ask(_("Change URL"), value, lambda again: self._save_url(source_id, again))
            return
        if source.get("type") == "mag":
            value = normalize_portal(value)
        self.store.update_source(source_id, url=value)
        self.store.clear_cache(source_id)
        self.changed = True
        self.rebuild()
        info_box(self.session, _("Saved"))

    def _save_mac(self, source_id, text):
        if text is None:
            return
        mac = normalize_mac(text)
        if not is_valid_mac(mac):
            info_box(self.session, _("Invalid MAC address") + u"\n" + _("Enter a valid address like 00:1A:79:12:34:56"))
            self._ask(_("MAC address"), to_text(text), lambda again: self._save_mac(source_id, again))
            return
        self.store.update_source(source_id, mac=mac)
        self.store.clear_cache(source_id)
        self.changed = True
        self.rebuild()
        info_box(self.session, _("Saved"))

    def _save_epg_url(self, source_id, text):
        if text is None:
            return
        value = to_text(text).strip()
        if value and not clean_epg_urls(value):
            info_box(self.session, _("Invalid URL") + u"\n" + _("The address must start with http:// or https://"))
            self._ask(_("EPG URL (optional)"), value,
                      lambda again: self._save_epg_url(source_id, again))
            return
        self.store.update_source(source_id, epg_url=value)
        self.store.clear_epg_cache(source_id)
        self.changed = True
        self.rebuild()
        info_box(self.session, _("Saved"))

    def _save_ua(self, source_id, text):
        if text is None:
            return
        self.store.update_source(source_id, ua=to_text(text).strip())
        self.changed = True
        self.rebuild()

    # --------------------------------------------------------------- adders
    def key_green(self):
        self.add_m3u()

    def key_blue(self):
        self.add_mag()

    def key_back(self):
        self.close("changed" if self.changed else None)

    def key_red(self):
        source = self.current()
        if source and source.get("id"):
            yes_no(self.session, _("Delete this source?") + u"\n" + to_text(source.get("name")),
                   lambda answer: self._delete_confirmed(source.get("id"), answer))
        else:
            self.close()

    def add_m3u(self):
        self._ask(_("Playlist name"), "", self._m3u_name)

    def _m3u_name(self, name):
        if name is None:
            return
        name = to_text(name).strip() or "M3U"
        self._ask(_("Playlist URL (m3u / m3u8)"), "http://", lambda url: self._m3u_url(name, url))

    def _m3u_url(self, name, url):
        if url is None:
            return
        url = to_text(url).strip()
        if not _valid_url(url):
            info_box(self.session, _("Invalid URL") + u"\n" + _("The address must start with http:// or https://"))
            self._ask(_("Playlist URL (m3u / m3u8)"), url, lambda again: self._m3u_url(name, again))
            return
        self._ask(_("User-Agent (optional)"), "", lambda ua: self._create("m3u", name, url, "", ua))

    def add_mag(self):
        self._ask(_("Portal name"), "", self._mag_name)

    def _mag_name(self, name):
        if name is None:
            return
        name = to_text(name).strip() or "MAG"
        self._ask(_("Portal URL"), "http://", lambda url: self._mag_url(name, url))

    def _mag_url(self, name, url):
        if url is None:
            return
        url = to_text(url).strip()
        if not _valid_url(url):
            info_box(self.session, _("Invalid URL") + u"\n" + _("The address must start with http:// or https://"))
            self._ask(_("Portal URL"), url, lambda again: self._mag_url(name, again))
            return
        self._ask(_("MAC address"), "00:1A:79:", lambda mac: self._mag_mac(name, url, mac))

    def _mag_mac(self, name, url, mac):
        if mac is None:
            return
        mac = normalize_mac(mac)
        if not is_valid_mac(mac):
            info_box(self.session, _("Invalid MAC address") + u"\n" + _("Enter a valid address like 00:1A:79:12:34:56"))
            self._ask(_("MAC address"), to_text(mac), lambda again: self._mag_mac(name, url, again))
            return
        self._create("mag", name, normalize_portal(url), mac, "")

    def _create(self, kind, name, url, mac, ua):
        source = self.store.new_source(kind, name, url, mac, to_text(ua).strip())
        self.store.set_active(source.get("id"))
        self.store.clear_cache(source.get("id"))
        self.changed = True
        self.close("changed")

    # ------------------------------------------------------------- helpers
    def _ask(self, title, initial, callback):
        self.session.openWithCallback(callback, VirtualKeyBoard, title=title, text=initial or "")

    def _refresh(self, source_id):
        source = self.store.get_source(source_id)
        if not source:
            return
        backend = create_backend(source, self.store)
        self.status_text(_("Refreshing ..."))
        self.run_async(lambda: backend.refresh(force=True), self._refresh_done, self._refresh_failed)

    def _refresh_done(self, _result):
        self.status_text(u"")
        self.changed = True
        self.rebuild()
        info_box(self.session, _("Refresh finished"))

    def _refresh_failed(self, error):
        self.status_text(u"")
        self.show_error(error)
