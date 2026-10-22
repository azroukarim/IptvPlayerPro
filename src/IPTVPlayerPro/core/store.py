# -*- coding: utf-8 -*-
"""Configuration, per source cache and favorites."""

from __future__ import absolute_import

import os
import re
import shutil
import threading

from .util import (atomic_write, ensure_dir, md5, now, read_json, safe_int,
                   short_hash, to_text, write_json)


# The Enigma2 UI and the optional web server write the same JSON file from
# different threads.  This lock serialises read-modify-write cycles, and each
# mutation reloads the file first so one writer cannot drop another's changes.
_STORE_LOCK = threading.RLock()


VERSION = "1.2.2"

CONFIG_CANDIDATES = [
    "/etc/enigma2/iptvplayerpro",
    "/etc/iptvplayerpro",
    "/home/root/.config/iptvplayerpro",
]
CACHE_CANDIDATES = [
    "/tmp/iptvplayerpro",
    "/var/volatile/tmp/iptvplayerpro",
    "/dev/shm/iptvplayerpro",
]

SERVER_FILE_DIR = "/etc/enigma2/IPTVPlayerPro"
DEFAULT_M3U_FILE = SERVER_FILE_DIR + "/m3u.txt"
DEFAULT_MAC_FILE = SERVER_FILE_DIR + "/mac.txt"

DEFAULT_SETTINGS = {
    "language": "ar",
    "service_type": 4097,
    "timeout": 20,
    "page_size": 300,
    "hide_adult": True,
    "logos": True,
    "close_after_zap": True,
    "cache_hours": 12,
    "web_enabled": True,
    "web_port": 8099,
    "web_pin": "",
    "m3u_file": DEFAULT_M3U_FILE,
    "mac_file": DEFAULT_MAC_FILE,
}


def _clean_field(value):
    return to_text(value).replace("|", " ").replace("\r", " ").replace("\n", " ").strip()


def _clean_url(value):
    text = to_text(value).replace("\r", "").replace("\n", "").strip()
    return text.replace("|", "%7C")


def _normalize_mac(value):
    text = re.sub(r"[^0-9A-Fa-f]", "", to_text(value))
    if len(text) != 12:
        return ""
    text = text.upper()
    return ":".join(text[index:index + 2] for index in range(0, 12, 2))


def _valid_http_url(value):
    text = to_text(value).strip().lower()
    return text.startswith("http://") or text.startswith("https://")


def _storage_ready(path):
    """Do not create /media/hdd or /media/usb when the device is absent."""
    parent = os.path.dirname(path) or "."
    for mount in ("/media/hdd", "/media/usb"):
        if parent == mount or parent.startswith(mount + "/"):
            return os.path.isdir(mount)
    return True


def _read_server_file(path):
    try:
        handle = open(path, "rb")
        try:
            raw = handle.read()
        finally:
            handle.close()
    except Exception:
        return None
    text = to_text(raw)
    if text.startswith(u"\ufeff"):
        text = text[1:]
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)
    return lines


def _parse_m3u_line(line):
    parts = [part.strip() for part in line.split("|")]
    if len(parts) == 1:
        return u"", _clean_url(parts[0]), u""
    if len(parts) == 2:
        return _clean_field(parts[0]), _clean_url(parts[1]), u""
    return _clean_field(parts[0]), _clean_url(parts[1]), _clean_field(u"|".join(parts[2:]))


def _parse_mac_line(line):
    parts = [part.strip() for part in line.split("|")]
    if len(parts) == 2:
        return u"", parts[0], parts[1], u""
    if len(parts) == 3:
        if _normalize_mac(parts[1]):
            # portal|mac|user-agent
            return u"", parts[0], parts[1], parts[2]
        if _normalize_mac(parts[2]):
            # name|portal|mac
            return parts[0], parts[1], parts[2], u""
        return None
    if len(parts) >= 4:
        return parts[0], parts[1], parts[2], u"|".join(parts[3:])
    return None


def _default_name(kind, url, mac):
    host = _clean_url(url).split("//", 1)[-1].split("/", 1)[0]
    if not host:
        host = mac
    return (u"MAG - {0}" if kind == "mag" else u"M3U - {0}").format(host)


def _first_writable(candidates, suffix=""):
    for base in candidates:
        folder = base + suffix
        if ensure_dir(folder):
            probe = os.path.join(folder, ".write-test")
            try:
                handle = open(probe, "wb")
                handle.write(b"1")
                handle.close()
                os.remove(probe)
                return folder
            except Exception:
                continue
    return candidates[0] + suffix


def _merge(defaults, values):
    result = dict(defaults)
    if isinstance(values, dict):
        for key, value in values.items():
            if key in defaults:
                result[key] = value
    return result


class Store(object):
    def __init__(self, config_dir=None, cache_dir=None):
        self.config_dir = config_dir or _first_writable(CONFIG_CANDIDATES)
        self.cache_dir = cache_dir or _first_writable(CACHE_CANDIDATES)
        self.config_path = os.path.join(self.config_dir, "config.json")
        self.logo_dir = os.path.join(self.cache_dir, "logos")
        self.poster_dir = os.path.join(self.cache_dir, "posters")
        self._data = None
        self.load()

    # ------------------------------------------------------------------ io
    def load(self):
        with _STORE_LOCK:
            return self._load_unlocked()

    def _load_unlocked(self):
        data = read_json(self.config_path, None)
        if not isinstance(data, dict):
            data = {}
        data.setdefault("version", 1)
        data["settings"] = _merge(DEFAULT_SETTINGS, data.get("settings"))
        sources = data.get("sources")
        if not isinstance(sources, list):
            sources = []
        cleaned = []
        for source in sources:
            if not isinstance(source, dict) or not source.get("id"):
                continue
            source.setdefault("type", "m3u")
            source.setdefault("name", source.get("id"))
            source.setdefault("url", "")
            source.setdefault("mac", "")
            source.setdefault("ua", "")
            source.setdefault("favorites", [])
            if not isinstance(source["favorites"], list):
                source["favorites"] = []
            source.setdefault("info", {})
            source.setdefault("updated", 0)
            cleaned.append(source)
        data["sources"] = cleaned
        active = data.get("active")
        if active not in [s["id"] for s in cleaned]:
            data["active"] = cleaned[0]["id"] if cleaned else ""
        self._data = data
        return data

    def save(self):
        with _STORE_LOCK:
            ensure_dir(self.config_dir)
            return write_json(self.config_path, self._data)

    def _sync_server_files(self):
        results = []
        specs = (
            ("m3u", to_text(self.settings.get("m3u_file")).strip() or DEFAULT_M3U_FILE),
            ("mag", to_text(self.settings.get("mac_file")).strip() or DEFAULT_MAC_FILE),
        )
        for kind, path in specs:
            if not path:
                continue
            if not _storage_ready(path):
                results.append({"path": path, "ok": False, "error": u"media path is not mounted"})
                continue
            try:
                folder = os.path.dirname(path)
                if folder and not ensure_dir(folder):
                    raise IOError(u"cannot create folder: " + folder)
                lines = []
                if kind == "m3u":
                    lines.append(u"# IPTV Player Pro - M3U servers")
                    lines.append(u"# name|url|user-agent")
                else:
                    lines.append(u"# IPTV Player Pro - MAG/Stalker servers")
                    lines.append(u"# name|portal|mac|user-agent")
                for source in self.sources:
                    if to_text(source.get("type")) != kind:
                        continue
                    name = _clean_field(source.get("name")) or _clean_field(source.get("id"))
                    url = _clean_url(source.get("url"))
                    ua = _clean_field(source.get("ua"))
                    if kind == "m3u":
                        lines.append(u"{0}|{1}|{2}".format(name, url, ua))
                    else:
                        lines.append(u"{0}|{1}|{2}|{3}".format(
                            name, url, _normalize_mac(source.get("mac")), ua))
                data = u"\n".join(lines) + u"\n"
                if not atomic_write(path, data):
                    raise IOError(u"cannot write file")
                results.append({"path": path, "ok": True, "error": u""})
            except Exception as error:
                results.append({"path": path, "ok": False, "error": to_text(error)})
        return results

    def sync_server_files(self):
        """Rewrite both text files and return one result per file."""
        with _STORE_LOCK:
            self.load()
            return self._sync_server_files()

    def import_server_files(self):
        """Import lines from the configured m3u.txt / mac.txt files."""
        with _STORE_LOCK:
            self.load()
            result = {"added": 0, "updated": 0, "errors": [], "files": []}
            rows = []
            specs = (
                ("m3u", to_text(self.settings.get("m3u_file")).strip() or DEFAULT_M3U_FILE),
                ("mag", to_text(self.settings.get("mac_file")).strip() or DEFAULT_MAC_FILE),
            )
            for kind, path in specs:
                lines = _read_server_file(path)
                if lines is None:
                    result["files"].append({"path": path, "ok": False, "error": u"file not found"})
                    result["errors"].append(u"{0}: file not found".format(path))
                    continue
                result["files"].append({"path": path, "ok": True, "error": u""})
                for number, line in enumerate(lines, 1):
                    if kind == "m3u":
                        parsed = _parse_m3u_line(line)
                        name, url, mac, ua = parsed[0], parsed[1], u"", parsed[2]
                    else:
                        parsed = _parse_mac_line(line)
                        if parsed is None:
                            result["errors"].append(
                                u"{0}:{1}: invalid line".format(path, number))
                            continue
                        name, url, mac, ua = parsed
                        try:
                            from .mag import normalize_portal
                            url = normalize_portal(url)
                        except Exception:
                            url = url.rstrip("/")
                        mac = _normalize_mac(mac)
                    if not _valid_http_url(url) or (kind == "mag" and not mac):
                        result["errors"].append(
                            u"{0}:{1}: invalid line".format(path, number))
                        continue
                    rows.append((kind, name, url, mac, ua))

            for kind, name, url, mac, ua in rows:
                existing = self._find_source(kind, url, mac)
                if existing is not None:
                    existing["name"] = name or existing.get("name") or _default_name(kind, url, mac)
                    existing["url"] = url
                    existing["mac"] = mac
                    existing["ua"] = ua
                    self.clear_cache(existing.get("id"))
                    result["updated"] += 1
                else:
                    source = self._build_source(kind, name, url, mac, ua)
                    self.sources.append(source)
                    result["added"] += 1

            if result["added"] or result["updated"]:
                if not self._data.get("active") and self.sources:
                    self._data["active"] = self.sources[0]["id"]
                self.save()
                self._sync_server_files()
            return result

    # ------------------------------------------------------------ settings
    @property
    def settings(self):
        return self._data["settings"]

    def set_setting(self, key, value):
        with _STORE_LOCK:
            self.load()
            self.settings[key] = value
            self.save()

    # ------------------------------------------------------------- sources
    @property
    def sources(self):
        return self._data["sources"]

    def get_source(self, source_id):
        for source in self.sources:
            if source.get("id") == source_id:
                return source
        return None

    def active_id(self):
        return self._data.get("active") or ""

    def active_source(self):
        return self.get_source(self.active_id())

    def set_active(self, source_id):
        with _STORE_LOCK:
            self.load()
            if self.get_source(source_id):
                self._data["active"] = source_id
                self.save()
                return True
            return False

    def _build_source(self, kind, name, url, mac="", ua=""):
        ident = "{0}_{1}".format(kind, short_hash("{0}|{1}|{2}".format(kind, url, mac), 10))
        while self.get_source(ident):
            ident = "{0}_{1}".format(kind, short_hash("{0}|{1}|{2}|{3}".format(kind, url, mac, now()), 10))
        return {
            "id": ident,
            "type": kind,
            "name": name or _default_name(kind, url, mac),
            "url": url,
            "mac": mac,
            "ua": ua,
            "favorites": [],
            "info": {},
            "updated": 0,
            "created": now(),
        }

    def new_source(self, kind, name, url, mac="", ua=""):
        with _STORE_LOCK:
            self.load()
            source = self._build_source(kind, name, url, mac, ua)
            self.sources.append(source)
            if not self._data.get("active"):
                self._data["active"] = source["id"]
            self.save()
            self._sync_server_files()
            return source

    def _find_source(self, kind, url, mac):
        for source in self.sources:
            if to_text(source.get("type")) != kind:
                continue
            if _clean_url(source.get("url")) != _clean_url(url):
                continue
            if kind == "mag" and _normalize_mac(source.get("mac")) != _normalize_mac(mac):
                continue
            return source
        return None

    def update_source(self, source_id, **values):
        with _STORE_LOCK:
            self.load()
            source = self.get_source(source_id)
            if not source:
                return None
            for key, value in values.items():
                source[key] = value
            self.save()
            self._sync_server_files()
            return source

    def delete_source(self, source_id):
        with _STORE_LOCK:
            self.load()
            source = self.get_source(source_id)
            if not source:
                return False
            self.sources.remove(source)
            self.clear_cache(source_id)
            if self._data.get("active") == source_id:
                self._data["active"] = self.sources[0]["id"] if self.sources else ""
            self.save()
            self._sync_server_files()
            return True

    # -------------------------------------------------------- source cache
    def cache_file(self, source_id):
        return os.path.join(self.cache_dir, "cache_{0}.json".format(source_id))

    def load_cache(self, source_id):
        payload = read_json(self.cache_file(source_id), None)
        if not isinstance(payload, dict):
            return None
        return payload

    def save_cache(self, source_id, payload):
        ensure_dir(self.cache_dir)
        payload["ts"] = safe_int(payload.get("ts")) or now()
        return write_json(self.cache_file(source_id), payload)

    def cache_age(self, source_id):
        payload = read_json(self.cache_file(source_id), None)
        if not isinstance(payload, dict):
            return -1
        ts = safe_int(payload.get("ts"))
        if ts <= 0:
            return -1
        return max(0, now() - ts)

    def clear_cache(self, source_id=None):
        if source_id:
            try:
                os.remove(self.cache_file(source_id))
            except Exception:
                pass
            return
        for name in os.listdir(self.cache_dir) if os.path.isdir(self.cache_dir) else []:
            if name.startswith("cache_") and name.endswith(".json"):
                try:
                    os.remove(os.path.join(self.cache_dir, name))
                except Exception:
                    pass
        for folder in (self.logo_dir, self.poster_dir):
            try:
                shutil.rmtree(folder)
            except Exception:
                pass

    def logo_file(self, url, kind="logo"):
        folder = self.poster_dir if kind == "poster" else self.logo_dir
        ensure_dir(folder)
        return os.path.join(folder, md5(url))

    def update_info(self, source_id, **values):
        with _STORE_LOCK:
            self.load()
            source = self.get_source(source_id)
            if not source:
                return
            info = source.get("info")
            if not isinstance(info, dict):
                info = {}
            info.update(values)
            source["info"] = info
            source["updated"] = now()
            self.save()

    # ----------------------------------------------------------- favorites
    def favorites(self, source_id):
        source = self.get_source(source_id)
        if not source:
            return []
        return source.get("favorites") or []

    def is_favorite(self, source_id, key):
        return key in self.favorites(source_id)

    def toggle_favorite(self, source_id, key):
        with _STORE_LOCK:
            self.load()
            source = self.get_source(source_id)
            if not source:
                return False
            favorites = source.setdefault("favorites", [])
            if key in favorites:
                favorites.remove(key)
                state = False
            else:
                favorites.append(key)
                state = True
            self.save()
            return state
