# -*- coding: utf-8 -*-
"""Player settings screen (self contained, no ConfigList dependency)."""

from __future__ import absolute_import

from ..core.i18n import _, language_label, set_language
from ..core.store import VERSION
from ..core.util import safe_int
from .base import ListScreen, info_box, row_entry, yes_no


SERVICE_TYPES = [
    (4097, u"4097  \u2022  GStreamer"),
    (5001, u"5001  \u2022  ExtePlayer3"),
    (5002, u"5002  \u2022  ExtePlayer3 (alt)"),
    (1, u"1  \u2022  DVB"),
]
TIMEOUTS = [10, 15, 20, 30, 45, 60]
CACHE_HOURS = [0, 1, 3, 6, 12, 24, 48]


class SettingsScreen(ListScreen):
    item_height = 66

    def __init__(self, session, store):
        ListScreen.__init__(self, session, _("Player settings"), u"", _("OK change  •  RED close"))
        self.store = store
        self.options = []
        self.build_options()
        self.render()

    # --------------------------------------------------------------- build
    def build_options(self):
        settings = self.store.settings
        language = set_language(settings.get("language") or "ar")
        options = [
            {
                "key": "language", "label": _("Language"),
                "values": ["ar", "en"],
                "display": lambda value: language_label(value),
            },
            {
                "key": "service_type", "label": _("Stream engine"),
                "values": [item[0] for item in SERVICE_TYPES],
                "display": lambda value: [text for item, text in SERVICE_TYPES if item == value][0],
            },
            {
                "key": "timeout", "label": _("HTTP timeout (seconds)"),
                "values": TIMEOUTS,
                "display": lambda value: u"{0} s".format(value),
            },
            {
                "key": "hide_adult", "label": _("Hide adult categories"),
                "values": [True, False],
                "display": lambda value: _("Yes") if value else _("No"),
            },
            {
                "key": "close_after_zap", "label": _("Close lists after zap"),
                "values": [True, False],
                "display": lambda value: _("Yes") if value else _("No"),
            },
            {
                "key": "cache_hours", "label": _("Cache validity (hours)"),
                "values": CACHE_HOURS,
                "display": lambda value: u"{0} h".format(value),
            },
            {"key": "clear_cache", "label": _("Clear cache"), "action": True},
            {"key": "about", "label": _("About"), "action": True},
        ]
        self.options = options
        self.language = language

    def render(self):
        settings = self.store.settings
        rows = []
        entries = []
        for option in self.options:
            rows.append(option)
            if option.get("action"):
                value = u""
            else:
                value = option["display"](settings.get(option["key"]))
            entries.append(row_entry(1200, 66, option["label"], value=value))
        self.set_entries(entries, rows)
        self.set_title(_("Player settings"))
        self.set_subtitle(_("IPTV Player Pro") + u"  \u2022  " + _("Version") + u" " + VERSION)
        self.set_hint(_("OK change  •  RED close"))

    # ------------------------------------------------------------- actions
    def activate(self, row):
        key = row.get("key")
        if key == "clear_cache":
            yes_no(self.session, _("Clear the cached playlists and logos?"), self._clear_confirmed)
            return
        if key == "about":
            info_box(self.session, u"{0}\n{1}\n\n{2}".format(
                _("IPTV Player Pro"), _("Version") + u" " + VERSION,
                _("A fast M3U and MAG/Stalker player for Enigma2.")), timeout=8)
            return
        values = row.get("values") or []
        if not values:
            return
        current = self.store.settings.get(key)
        try:
            index = values.index(current)
        except ValueError:
            index = -1
        value = values[(index + 1) % len(values)]
        self.store.set_setting(key, value)
        if key == "language":
            set_language(value)
            self.build_options()
        self.render()

    def _clear_confirmed(self, answer):
        if not answer:
            return
        self.store.clear_cache()
        info_box(self.session, _("Cache cleared"))

    def key_red(self):
        self.close()

    def key_back(self):
        self.close()
