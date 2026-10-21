# -*- coding: utf-8 -*-
"""Backends that expose a single interface to the UI.

* M3UBackend  : downloads and parses a playlist once, then answers locally.
* MagBackend  : talks to a Stalker portal (live channels cached, VOD pages
                fetched on demand).
"""

from __future__ import absolute_import

import re

from .i18n import _
from .mag import (MagClient, MagError, is_valid_mac, normalize_mac,
                  normalize_portal, portal_logo)
from .m3u import (build_catalogue, favourite_key, is_adult_category,
                  parse_playlist)
from .net import Http, NetError
from .util import (clean_html, human_age, is_expired, now, safe_int,
                   short_hash, to_text)


def _match(text, query):
    if not query:
        return True
    return to_text(query).lower() in to_text(text).lower()


def _sort_key(name):
    return to_text(name).lower()


class BaseBackend(object):
    kind = ""

    def __init__(self, source, store):
        self.source = source
        self.store = store
        self.settings = store.settings
        self.source_id = source.get("id") or ""
        self.error = ""

    # ------------------------------------------------------------------ api
    @property
    def name(self):
        return self.source.get("name") or self.source_id

    def is_ready(self):
        return False

    def refresh(self, force=False, progress=None):
        return False

    def counts(self):
        return {}

    def live_categories(self):
        return []

    def live_items(self, category_id, query=""):
        return []

    def vod_categories(self):
        return []

    def vod_items(self, category_id, query="", page=1):
        return [], 0

    def series_categories(self):
        return []

    def series_items(self, category_id, query="", page=1):
        return [], 0

    def seasons(self, series_id):
        return []

    def episodes(self, series_id, season_id, page=1):
        return [], 0

    def resolve(self, item):
        raise NotImplementedError

    def account(self):
        info = self.source.get("info") or {}
        return {
            "expires": info.get("expires") or "",
            "status": info.get("status") or "",
            "updated": safe_int(info.get("updated")) or safe_int(self.source.get("updated")),
        }

    def is_favorite(self, item):
        return self.store.is_favorite(self.source_id, self.favorite_key(item))

    def favorite_key(self, item):
        return item.get("fav_key") or ""

    def toggle_favorite(self, item):
        return self.store.toggle_favorite(self.source_id, self.favorite_key(item))

    def favorites_count(self):
        return len(self.store.favorites(self.source_id))

    def check_account(self):
        return self.account()

    def cache_hours(self):
        return safe_int(self.settings.get("cache_hours"), 12)

    def hide_adult(self):
        return bool(self.settings.get("hide_adult", True))

    def _category(self, cat_id, name, count=0):
        return {"id": to_text(cat_id), "name": name, "count": safe_int(count)}


class M3UBackend(BaseBackend):
    kind = "m3u"

    def __init__(self, source, store):
        BaseBackend.__init__(self, source, store)
        self.live = []
        self.vod = []
        self.series = []
        self._series_index = {}
        self.loaded = False

    # ------------------------------------------------------------- loading
    def is_ready(self):
        return self.loaded

    def _cache_usable(self, payload=None):
        hours = self.cache_hours()
        if hours <= 0:
            return False
        ts = safe_int((payload or {}).get("ts"))
        age = max(0, now() - ts) if ts > 0 else self.store.cache_age(self.source_id)
        return age >= 0 and age <= hours * 3600

    def refresh(self, force=False, progress=None):
        if not force and self.loaded:
            return True
        payload = None if force else self.store.load_cache(self.source_id)
        if payload and self._cache_usable(payload) and payload.get("kind") == "m3u":
            self._apply(payload)
            return True
        if progress:
            progress(_("Downloading playlist ..."))
        url = to_text(self.source.get("url")).strip()
        if not url:
            raise NetError(_("Invalid URL"))
        timeout = safe_int(self.settings.get("timeout"), 20)
        headers = {}
        if self.source.get("ua"):
            headers["User-Agent"] = self.source.get("ua")
        # A failed playlist download must fail visibly instead of keeping the
        # screen on "Loading ..." for several retry cycles.  BLUE reload gives
        # the user an explicit retry.
        http = Http(timeout=timeout, user_agent=headers.get("User-Agent"), retries=0)
        text = http.get_text(url, headers=headers)
        if progress:
            progress(_("Reading playlist ..."))
        items = parse_playlist(text, base_url=url)
        if not items:
            raise NetError(_("The playlist is empty."))
        catalogue = build_catalogue(items, meta={"kind": "m3u", "url": url})
        self._apply(catalogue)
        self.store.save_cache(self.source_id, catalogue)
        self.store.update_info(
            self.source_id,
            channels=catalogue["counts"]["live"],
            vod=catalogue["counts"]["vod"],
            series=catalogue["counts"]["series"],
            episodes=catalogue["counts"]["episodes"],
            updated=now(),
            status="loaded",
        )
        return True

    def _apply(self, payload):
        self.live = payload.get("live") or []
        self.vod = payload.get("vod") or []
        self.series = payload.get("series") or []
        self._series_index = {}
        for entry in self.series:
            self._series_index[entry.get("id")] = entry
        self.loaded = True

    def counts(self):
        return {
            "live": len(self.live),
            "vod": len(self.vod),
            "series": len(self.series),
            "episodes": sum([len(entry.get("episodes") or []) for entry in self.series]),
        }

    # ---------------------------------------------------------------- live
    def live_categories(self):
        groups = []
        seen = set()
        for item in self.live:
            group = item.get("group") or "Live TV"
            if group not in seen:
                seen.add(group)
                groups.append(group)
        groups.sort(key=_sort_key)
        categories = [
            self._category("all", _("All channels"), len(self.live)),
            self._category("fav", u"\u2605 " + _("Favorites"), self.favorites_count()),
        ]
        for group in groups:
            if self.hide_adult() and is_adult_category(group):
                continue
            count = len([item for item in self.live if (item.get("group") or "") == group])
            categories.append(self._category("g:" + group, group, count))
        return categories

    def live_items(self, category_id, query=""):
        if category_id == "fav":
            favorites = set(self.store.favorites(self.source_id))
            items = [item for item in self.live if self.favorite_key(item) in favorites]
        elif category_id.startswith("g:"):
            group = category_id[2:]
            items = [item for item in self.live if (item.get("group") or "") == group]
        else:
            items = list(self.live)
        if query:
            items = [item for item in items if _match(item.get("name"), query)]
        return items

    def favorite_key(self, item):
        return favourite_key(item)

    # ----------------------------------------------------------------- vod
    def vod_categories(self):
        groups = []
        seen = set()
        for item in self.vod:
            group = item.get("group") or "Movies"
            if group not in seen:
                seen.add(group)
                groups.append(group)
        groups.sort(key=_sort_key)
        categories = [self._category("all", _("All"), len(self.vod))]
        for group in groups:
            if self.hide_adult() and is_adult_category(group):
                continue
            count = len([item for item in self.vod if (item.get("group") or "") == group])
            categories.append(self._category("g:" + group, group, count))
        return categories

    def _page_slice(self, items, page):
        size = max(50, min(1000, safe_int(self.settings.get("page_size"), 300)))
        page = max(1, safe_int(page, 1))
        start = (page - 1) * size
        return items[start:start + size], len(items)

    def vod_items(self, category_id, query="", page=1):
        if category_id.startswith("g:"):
            group = category_id[2:]
            items = [item for item in self.vod if (item.get("group") or "") == group]
        else:
            items = list(self.vod)
        if query:
            items = [item for item in items if _match(item.get("name"), query)]
        return self._page_slice(items, page)

    # -------------------------------------------------------------- series
    def series_categories(self):
        groups = []
        seen = set()
        for entry in self.series:
            group = entry.get("group") or "Series"
            if group not in seen:
                seen.add(group)
                groups.append(group)
        groups.sort(key=_sort_key)
        categories = [self._category("all", _("All"), len(self.series))]
        for group in groups:
            if self.hide_adult() and is_adult_category(group):
                continue
            count = len([entry for entry in self.series if (entry.get("group") or "") == group])
            categories.append(self._category("g:" + group, group, count))
        return categories

    def series_items(self, category_id, query="", page=1):
        if category_id.startswith("g:"):
            group = category_id[2:]
            items = [entry for entry in self.series if (entry.get("group") or "") == group]
        else:
            items = list(self.series)
        if query:
            items = [item for item in items if _match(item.get("name"), query)]
        return self._page_slice(items, page)

    def seasons(self, series_id):
        entry = self._series_index.get(series_id)
        if not entry:
            return []
        seasons = []
        for episode in entry.get("episodes") or []:
            season = safe_int(episode.get("season"), 0)
            if season not in [item["season"] for item in seasons]:
                seasons.append({"season": season})
        seasons.sort(key=lambda item: item["season"])
        return [{
            "id": str(item["season"]),
            "name": (_("Season {0}").format(item["season"]) if item["season"] else _("All episodes")),
            "count": len([episode for episode in entry.get("episodes") or []
                          if safe_int(episode.get("season"), 0) == item["season"]]),
        } for item in seasons]

    def episodes(self, series_id, season_id, page=1):
        entry = self._series_index.get(series_id)
        if not entry:
            return [], 0
        season = safe_int(season_id, 0)
        episodes = [episode for episode in entry.get("episodes") or []
                    if safe_int(episode.get("season"), 0) == season]
        return episodes, len(episodes)

    def resolve(self, item):
        url = to_text(item.get("url")).strip()
        if not url:
            raise NetError(_("This stream is not playable"))
        return url

    def account(self):
        info = self.source.get("info") or {}
        return {
            "expires": "",
            "status": "loaded" if self.loaded else "",
            "updated": safe_int(info.get("updated")) or safe_int(self.source.get("updated")),
            "channels": safe_int(info.get("channels")),
            "vod": safe_int(info.get("vod")),
            "series": safe_int(info.get("series")),
            "episodes": safe_int(info.get("episodes")),
        }


class MagBackend(BaseBackend):
    kind = "mag"

    def __init__(self, source, store):
        BaseBackend.__init__(self, source, store)
        self.client = None
        self.genres_itv = []
        self.genres_vod = []
        self.channels = []
        self.loaded = False
        self._vod_cache = {}
        self._series_cache = {}

    # ------------------------------------------------------------- helpers
    def _make_client(self):
        if self.client is None:
            self.client = MagClient(
                self.source.get("url"),
                self.source.get("mac"),
                serial=self.source.get("serial") or None,
                device_id=self.source.get("device_id") or None,
                timeout=safe_int(self.settings.get("timeout"), 20),
            )
        return self.client

    def _cache_usable(self, payload=None):
        hours = self.cache_hours()
        if hours <= 0:
            return False
        ts = safe_int((payload or {}).get("ts"))
        age = max(0, now() - ts) if ts > 0 else self.store.cache_age(self.source_id)
        return age >= 0 and age <= hours * 3600

    def is_ready(self):
        return self.loaded

    def refresh(self, force=False, progress=None):
        if self.loaded and not force:
            return True
        payload = None if force else self.store.load_cache(self.source_id)
        if payload and payload.get("kind") == "mag" and self._cache_usable(payload):
            self._apply(payload)
            return True
        client = self._make_client()
        if progress:
            progress(_("Connecting to the portal ..."))
        try:
            client.auth()
            if progress:
                progress(_("Reading portal categories ..."))
            genres_itv = client.itv_genres()
            genres_vod = client.vod_categories()
            if progress:
                progress(_("Reading channels ..."))
            try:
                channels = client.all_channels()
            except MagError:
                channels = []
            payload = {
                "kind": "mag",
                "ts": now(),
                "genres_itv": genres_itv,
                "genres_vod": genres_vod,
                "channels": channels,
                "portal": client.portal,
                "mac": client.mac,
            }
            self._apply(payload)
            self.store.save_cache(self.source_id, payload)
            info = client.account or {}
            expires = _expiry_of(info)
            status = "expired" if is_expired(expires) else ("active" if expires else "active")
            self.store.update_info(
                self.source_id,
                channels=len(channels),
                expires=expires,
                status=status,
                account_name=to_text(info.get("name") or ""),
                updated=now(),
            )
            return True
        except MagError as error:
            self.error = to_text(error)
            info = self.source.get("info") or {}
            info["status"] = "error"
            self.store.update_info(self.source_id, **info)
            raise

    def _apply(self, payload):
        self.genres_itv = payload.get("genres_itv") or []
        self.genres_vod = payload.get("genres_vod") or []
        self.channels = payload.get("channels") or []
        self.loaded = True

    def counts(self):
        info = self.source.get("info") or {}
        return {
            "live": len(self.channels) or safe_int(info.get("channels")),
            "vod": safe_int(info.get("vod")),
            "series": safe_int(info.get("series")),
        }

    # ---------------------------------------------------------------- live
    def live_categories(self):
        categories = [
            self._category("all", _("All channels"), len(self.channels)),
            self._category("fav", u"\u2605 " + _("Favorites"), self.favorites_count()),
        ]
        for genre in self.genres_itv:
            if self.hide_adult() and (genre.get("censored") or is_adult_category(genre.get("name"))):
                continue
            count = len([item for item in self.channels if to_text(item.get("tv_genre_id")) == genre["id"]])
            categories.append(self._category("g:" + genre["id"], genre["name"], count))
        return categories

    def live_items(self, category_id, query=""):
        items = []
        for raw in self.channels:
            group = to_text(raw.get("tv_genre_id") or raw.get("genre_id") or "")
            kind = "live"
            item = self._channel(raw, group, kind)
            if category_id == "fav":
                if not self.is_favorite(item):
                    continue
            elif category_id.startswith("g:"):
                if group != category_id[2:]:
                    continue
            if query and not _match(item.get("name"), query):
                continue
            items.append(item)
        if not self.channels and category_id not in ("all", "fav"):
            # Portal without get_all_channels: ask for the genre page by page.
            genre = category_id[2:] if category_id.startswith("g:") else category_id
            page = 1
            while page <= 8:
                raws, total = self._make_client().ordered_list("itv", genre, page)
                for raw in raws:
                    item = self._channel(raw, genre, "live")
                    if query and not _match(item.get("name"), query):
                        continue
                    items.append(item)
                if page * safe_int(self.settings.get("page_size"), 300) >= total:
                    break
                page += 1
        return items

    def _channel(self, raw, group, kind):
        ident = to_text(raw.get("id") or raw.get("ch_id") or "")
        name = to_text(raw.get("name") or raw.get("title") or "?")
        logo = portal_logo(self.source.get("url"), raw.get("logo") or raw.get("tv_genre_logo") or "")
        item = {
            "id": ident,
            "name": name,
            "logo": logo,
            "group": to_text(group),
            "kind": kind,
            "cmd": to_text(raw.get("cmd") or ""),
            "raw": raw,
            "fav_key": "mag:" + (ident or short_hash(name, 10)),
            "number": safe_int(raw.get("number")),
        }
        return item

    # ----------------------------------------------------------------- vod
    def vod_categories(self):
        categories = [self._category("all", _("All"), safe_int((self.source.get("info") or {}).get("vod")))]
        for genre in self.genres_vod:
            if self.hide_adult() and (genre.get("censored") or is_adult_category(genre.get("name"))):
                continue
            categories.append(self._category("g:" + genre["id"], genre["name"]))
        return categories

    def vod_items(self, category_id, query="", page=1):
        genre = category_id[2:] if category_id.startswith("g:") else "*"
        key = "vod|{0}|{1}".format(genre, page)
        cached = self._vod_cache.get(key)
        if cached is None:
            raws, total = self._make_client().ordered_list("vod", genre, page)
            items = [self._vod(raw, genre, "vod") for raw in raws]
            self._vod_cache[key] = (items, total)
        else:
            items, total = cached
        if query:
            items = [item for item in items if _match(item.get("name"), query)]
        return items, total

    def _vod(self, raw, group, kind):
        ident = to_text(raw.get("id") or "")
        name = to_text(raw.get("name") or raw.get("title") or "?")
        screenshot = raw.get("screenshot_uri") or raw.get("cover") or raw.get("logo") or raw.get("poster") or ""
        item = {
            "id": ident,
            "name": name,
            "logo": portal_logo(self.source.get("url"), screenshot),
            "group": to_text(group),
            "kind": kind,
            "cmd": to_text(raw.get("cmd") or ""),
            "raw": raw,
            "fav_key": "mag:" + (ident or short_hash(name, 10)),
            "year": to_text(raw.get("year") or ""),
            "rating": to_text(raw.get("rating_imdb") or raw.get("rating") or ""),
            "description": clean_html(raw.get("description") or raw.get("descr") or ""),
            "genres": to_text(raw.get("genres_str") or raw.get("category") or ""),
            "director": to_text(raw.get("director") or ""),
            "actors": to_text(raw.get("actors") or ""),
            "time": to_text(raw.get("time") or raw.get("duration") or ""),
            "series_flag": safe_int(raw.get("is_series") or 0),
        }
        return item

    # -------------------------------------------------------------- series
    def series_categories(self):
        return self.vod_categories()

    def series_items(self, category_id, query="", page=1):
        genre = category_id[2:] if category_id.startswith("g:") else "*"
        key = "series|{0}|{1}".format(genre, page)
        cached = self._series_cache.get(key)
        if cached is None:
            raws, total = self._make_client().series_page(genre, page)
            items = [self._vod(raw, genre, "series") for raw in raws]
            if not items and page == 1:
                # Portal without is_series support: filter the normal VOD list.
                raws, total = self._make_client().ordered_list("vod", genre, page)
                items = [self._vod(raw, genre, "series") for raw in raws
                         if safe_int(raw.get("is_series")) or raw.get("series")]
            self._series_cache[key] = (items, total)
        else:
            items, total = cached
        if query:
            items = [item for item in items if _match(item.get("name"), query)]
        return items, total

    def seasons(self, series_id):
        client = self._make_client()
        raws, _total = client.series_page("*", 1, movie_id=series_id, season_id=0)
        seasons = []
        if raws and any(raw.get("series") for raw in raws):
            for raw in raws:
                seasons.append({
                    "id": to_text(raw.get("id") or ""),
                    "name": to_text(raw.get("name") or _("Season")),
                    "count": len(raw.get("series") or []),
                })
            return seasons
        # Flat episode list: derive the seasons from season_id fields.
        seasons_map = {}
        for raw in raws:
            season = to_text(raw.get("season_id") or raw.get("season") or "0")
            seasons_map.setdefault(season, 0)
            seasons_map[season] += 1
        for season in sorted(seasons_map.keys(), key=lambda value: safe_int(value)):
            seasons.append({
                "id": season,
                "name": (_("Season {0}").format(season) if safe_int(season) else _("All episodes")),
                "count": seasons_map[season],
            })
        return seasons

    def episodes(self, series_id, season_id, page=1):
        client = self._make_client()
        raws, total = client.series_page("*", page, movie_id=series_id, season_id=season_id)
        items = []
        for raw in raws:
            item = self._vod(raw, "", "episode")
            item["season_id"] = to_text(season_id)
            item["series_id"] = to_text(series_id)
            if not item.get("name") or item.get("name").isdigit():
                number = safe_int(raw.get("episode") or raw.get("series_number") or raw.get("id"))
                item["name"] = u"{0} {1}".format(_("Episode"), number or len(items) + 1)
            items.append(item)
        return items, total

    # ------------------------------------------------------------ playback
    def resolve(self, item):
        cmd = to_text(item.get("cmd") or "").strip()
        raw = item.get("raw") or {}
        if not cmd:
            cmd = to_text(raw.get("cmd") or raw.get("link") or "")
        if not cmd:
            raise MagError(_("This stream is not playable"))
        client = self._make_client()
        if not client.token:
            client.handshake()
        kind = item.get("kind") or "vod"
        series_id = 0
        if kind == "episode":
            series_id = safe_int(item.get("series_id") or raw.get("movie_id") or raw.get("series_id"), 0)
        try:
            return client.create_link(kind, cmd, series=series_id)
        except MagError:
            if series_id:
                return client.create_link(kind, cmd, series=0)
            raise

    def favorite_key(self, item):
        return item.get("fav_key") or "mag:" + md5_key(item)

    def check_account(self):
        client = self._make_client()
        client.auth()
        info = client.account or {}
        expires = _expiry_of(info)
        status = "expired" if is_expired(expires) else ("active" if expires else "active")
        self.store.update_info(self.source_id, expires=expires, status=status,
                               account_name=to_text(info.get("name") or ""),
                               checked=now())
        return {
            "expires": expires,
            "status": status,
            "updated": now(),
            "name": to_text(info.get("name") or ""),
            "mac": to_text(info.get("mac") or self.source.get("mac")),
        }


def md5_key(item):
    return short_hash(to_text(item.get("name")) + "|" + to_text(item.get("cmd")), 10)


def _expiry_of(info):
    if not isinstance(info, dict):
        return ""
    for key in ("end_date", "expire_billing_date", "tariff_expired_date", "expires", "exp_date"):
        value = info.get(key)
        if value not in (None, "", 0, "0", "null", "0000-00-00 00:00:00"):
            return to_text(value)
    return ""


def create_backend(source, store):
    if not source:
        return None
    if source.get("type") == "mag":
        return MagBackend(source, store)
    return M3UBackend(source, store)


def active_backend(store):
    source = store.active_source()
    if not source:
        return None
    return create_backend(source, store)


def source_label(source):
    if not source:
        return ""
    kind = _("MAG portal") if source.get("type") == "mag" else _("M3U playlist")
    return u"{0}  \u2022  {1}".format(source.get("name") or "", kind)


def source_summary(source, store):
    """One line shown on the main menu."""
    if not source:
        return _("No playlist selected")
    info = source.get("info") or {}
    if source.get("type") == "mag":
        expires = info.get("expires") or ""
        status = info.get("status") or ""
        if status == "expired" or is_expired(expires):
            return u"{0}: {1}".format(_("Expired"), expires or source.get("mac") or "")
        if expires:
            return u"{0}: {1}".format(_("Expires"), expires)
        if status == "error":
            return _("Portal error")
        if status == "active":
            channels = safe_int(info.get("channels"))
            line = _("Active")
            if channels:
                line += u"  \u2022  {0} {1}".format(channels, _("channels"))
            return line
        return u"{0}  \u2022  {1}".format(source.get("mac") or "", _("Not checked"))
    channels = safe_int(info.get("channels"))
    vod = safe_int(info.get("vod"))
    series = safe_int(info.get("series"))
    stamp = human_age(info.get("updated") or source.get("updated"))
    if not channels and not vod and not series:
        return _("Not loaded yet")
    line = u"{0} {1}  \u2022  {2} {3}".format(channels, _("channels"), vod, _("movies"))
    if series:
        line += u"  \u2022  {0} {1}".format(series, _("series"))
    if stamp:
        line += u"  \u2022  " + stamp
    return line
