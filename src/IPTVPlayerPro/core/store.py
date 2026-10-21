# -*- coding: utf-8 -*-
"""Configuration, per source cache and favorites."""

from __future__ import absolute_import

import os
import shutil

from .util import (ensure_dir, md5, now, read_json, safe_int, short_hash,
                   write_json)


VERSION = "1.0.0"

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

DEFAULT_SETTINGS = {
    "language": "ar",
    "service_type": 4097,
    "timeout": 20,
    "page_size": 300,
    "hide_adult": True,
    "logos": True,
    "close_after_zap": True,
    "cache_hours": 12,
}


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
        ensure_dir(self.config_dir)
        return write_json(self.config_path, self._data)

    # ------------------------------------------------------------ settings
    @property
    def settings(self):
        return self._data["settings"]

    def set_setting(self, key, value):
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
        if self.get_source(source_id):
            self._data["active"] = source_id
            self.save()
            return True
        return False

    def new_source(self, kind, name, url, mac="", ua=""):
        ident = "{0}_{1}".format(kind, short_hash("{0}|{1}|{2}".format(kind, url, mac), 10))
        while self.get_source(ident):
            ident = "{0}_{1}".format(kind, short_hash("{0}|{1}|{2}|{3}".format(kind, url, mac, now()), 10))
        source = {
            "id": ident,
            "type": kind,
            "name": name,
            "url": url,
            "mac": mac,
            "ua": ua,
            "favorites": [],
            "info": {},
            "updated": 0,
            "created": now(),
        }
        self.sources.append(source)
        if not self._data.get("active"):
            self._data["active"] = ident
        self.save()
        return source

    def update_source(self, source_id, **values):
        source = self.get_source(source_id)
        if not source:
            return None
        for key, value in values.items():
            source[key] = value
        self.save()
        return source

    def delete_source(self, source_id):
        source = self.get_source(source_id)
        if not source:
            return False
        self.sources.remove(source)
        self.clear_cache(source_id)
        if self._data.get("active") == source_id:
            self._data["active"] = self.sources[0]["id"] if self.sources else ""
        self.save()
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
