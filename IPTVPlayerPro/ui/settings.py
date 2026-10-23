# -*- coding: utf-8 -*-
"""Player settings screen (self contained, no ConfigList dependency)."""

from __future__ import absolute_import

from ..core.i18n import _, language_label, set_language
from ..core.store import VERSION
from ..core.util import safe_int, to_text
from .base import ListScreen, info_box, row_entry, yes_no


SERVICE_TYPES = [
    (4097, u"4097  \u2022  GStreamer"),
    (5001, u"5001  \u2022  ExtePlayer3"),
    (5002, u"5002  \u2022  ExtePlayer3 (alt)"),
    (1, u"1  \u2022  DVB"),
]
TIMEOUTS = [10, 15, 20, 30, 45, 60]
CACHE_HOURS = [0, 1, 3, 6, 12, 24, 48]
WEB_PORTS = [8099, 8088, 8080, 9090, 8000]
M3U_FILES = [
    "/etc/enigma2/IPTVPlayerPro/m3u.txt",
    "/media/hdd/IPTVPlayerPro/m3u.txt",
    "/media/usb/IPTVPlayerPro/m3u.txt",
    "/media/usb/m3u.txt",
]
MAC_FILES = [
    "/etc/enigma2/IPTVPlayerPro/mac.txt",
    "/media/hdd/IPTVPlayerPro/mac.txt",
    "/media/usb/IPTVPlayerPro/mac.txt",
    "/media/usb/mac.txt",
]


def storage_label(value):
    text = value or ""
    for prefix, label in (("/etc/enigma2/", "flash: "), ("/media/hdd/", "hdd: "),
                          ("/media/usb/", "usb: ")):
        if text.startswith(prefix):
            return label + text[len(prefix):]
    return text


class SettingsScreen(ListScreen):
    item_height = 72

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
            {
                "key": "m3u_file", "label": _("M3U servers file"),
                "values": M3U_FILES,
                "display": storage_label,
            },
            {
                "key": "mac_file", "label": _("MAG servers file"),
                "values": MAC_FILES,
                "display": storage_label,
            },
            {"key": "import_files", "label": _("Import from server files"), "action": True},
            {"key": "sync_files", "label": _("Sync server files now"), "action": True},
            {
                "key": "web_enabled", "label": _("Enable web interface"),
                "values": [True, False],
                "display": lambda value: _("Yes") if value else _("No"),
            },
            {
                "key": "web_port", "label": _("Web interface port"),
                "values": WEB_PORTS,
                "display": lambda value: u"{0}".format(value),
            },
            {"key": "web_info", "label": _("Web interface address"), "action": True},
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
            yes_no(self.session, _("Clear the cached playlists, EPG and logos?"), self._clear_confirmed)
            return
        if key == "about":
            info_box(self.session, u"{0}\n{1}\n\n{2}".format(
                _("IPTV Player Pro"), _("Version") + u" " + VERSION,
                _("A fast M3U and MAG/Stalker player for Enigma2.")), timeout=8)
            return
        if key == "web_info":
            self.show_web_info()
            return
        if key == "import_files":
            yes_no(self.session, _("Import servers from the selected text files?"),
                   self._import_confirmed)
            return
        if key == "sync_files":
            self.sync_files()
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
        elif key in ("web_enabled", "web_port"):
            started = self.apply_web()
            if key == "web_enabled" and value and started:
                self.show_web_info()
        elif key in ("m3u_file", "mac_file"):
            self.sync_files()
        self.render()

    def apply_web(self):
        try:
            from ..web.server import manager
            if self.store.settings.get("web_enabled", True):
                return manager.ensure(self.store)
            manager.stop()
            return True
        except Exception:
            return False

    def show_web_info(self):
        if not self.store.settings.get("web_enabled", True):
            info_box(self.session, _("Web interface is disabled"))
            return
        try:
            from ..web.server import manager
        except Exception as error:
            info_box(self.session, _("Web server could not start") + u"\n" + u"{0}".format(error))
            return
        if not self.apply_web():
            info_box(self.session, _("Web server could not start") + u"\n" + to_text(manager.last_error))
            return
        urls = manager.urls()
        text = _("Open this address from a browser on the same network:") + u"\n\n" + u"\n".join(urls)
        pin = to_text(self.store.settings.get("web_pin")).strip()
        if pin:
            text += u"\n\n" + _("A PIN is required to access the web interface.")
        info_box(self.session, text, timeout=20)

    def _file_results(self, results):
        lines = []
        for item in results:
            lines.append(item.get("path") or u"")
            if item.get("ok"):
                lines.append(_("OK"))
            else:
                lines.append(_("Error") + u": " + to_text(item.get("error")))
        return u"\n".join(lines)

    def sync_files(self):
        results = self.store.sync_server_files()
        info_box(self.session, _("Server files updated") + u"\n\n" + self._file_results(results),
                 timeout=20)

    def _import_confirmed(self, answer):
        if not answer:
            return
        result = self.store.import_server_files()
        text = [
            _("Import completed"),
            _("Added: {0}").format(result.get("added", 0)),
            _("Updated: {0}").format(result.get("updated", 0)),
        ]
        errors = result.get("errors") or []
        if errors:
            text.append(_("Errors: {0}").format(len(errors)))
            text.extend(errors[:8])
        info_box(self.session, u"\n".join(text), timeout=25)

    def _clear_confirmed(self, answer):
        if not answer:
            return
        self.store.clear_cache()
        info_box(self.session, _("Cache cleared"))

    def key_red(self):
        self.close()

    def key_back(self):
        self.close()
