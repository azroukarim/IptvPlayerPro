# -*- coding: utf-8 -*-
"""Backends that expose a single interface to the UI.

* M3UBackend  : downloads and parses a playlist once, then answers locally.
* MagBackend  : talks to a Stalker portal (live channels cached, VOD pages
                fetched on demand).
"""

from __future__ import absolute_import

import re

from .epg import (EpgGuide, clean_epg_urls, derive_epg_url, now_next,
                  playlist_epg_urls)
from .i18n import _
from .mag import (MagClient, MagError, is_valid_mac, normalize_mac,
                  normalize_portal, portal_logo)
from .m3u import (build_catalogue, favourite_key, is_adult_category,
                  parse_playlist)
from .net import Http, NetError
from .util import (PrefetchCancelled, clean_html, human_age, is_expired, now,
                   safe_int, short_hash, to_text)
import logging
_logger = logging.getLogger('iptvplayerpro.backends')
try:
    _handler = logging.FileHandler('/tmp/iptvplayerpro-backends.log')
    _handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    _logger.addHandler(_handler)
    _logger.setLevel(logging.DEBUG)
except Exception:
    pass


def _match(text, query):
    if not query:
        return True
    return to_text(query).lower() in to_text(text).lower()


def _sort_key(name):
    return to_text(name).lower()


def _group_items(items, default_group):
    """Build one list per group so category switches never rescan a catalogue."""
    groups = {}
    for item in items:
        group = to_text(item.get("group") or default_group)
        groups.setdefault(group, []).append(item)
    return groups


def _page_size(settings):
    return max(50, min(1000, safe_int(settings.get("page_size"), 300)))


class BaseBackend(object):
    kind = ""

    def __init__(self, source, store):
        self.source = source
        self.store = store
        self.settings = store.settings
        self.source_id = source.get("id") or ""
        self.error = ""
        self._epg_guide = None
        self._epg_urls = []

    # ------------------------------------------------------------------ api
    @property
    def name(self):
        return self.source.get("name") or self.source_id

    def is_ready(self):
        return False

    def refresh(self, force=False, progress=None):
        return False

    def prefetch(self, progress=None, force=False):
        """Prepare the complete catalogue in the background.

        M3U already downloads the whole playlist in :meth:`refresh`; MAG
        overrides this method to walk every VOD and series page.
        """
        return self.counts()

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

    def stream_options(self, item):
        """Return ``(user_agent, extra_options)`` for the player.

        M3U entries carry their own ``#EXTVLCOPT`` values; the source level UA
        is used as a fallback for providers that protect both the playlist and
        the streams with the same agent.
        """
        return (to_text(item.get("ua") or self.source.get("ua")),
                to_text(item.get("opts")))

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

    def favorite_keys(self):
        """Return the favorite keys as a set for list rendering."""
        return set(self.store.favorites(self.source_id))

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

    # ------------------------------------------------------------------ epg
    def epg_urls(self):
        """Return the configured XMLTV URLs for this source."""
        manual = clean_epg_urls(self.source.get("epg_url") or u"")
        if manual:
            return manual
        return list(self._epg_urls or [])

    def epg_channel_refs(self):
        return []

    def epg_guide(self):
        if self._epg_guide is None:
            self._epg_guide = EpgGuide(self.store, self.source_id)
        return self._epg_guide

    def epg_stale(self):
        if not self.epg_urls():
            return False
        return self.epg_guide().is_stale()

    def epg_has_data(self):
        return self.epg_guide().has_data()

    def refresh_epg(self, force=False, progress=None):
        """Download the guide when it is missing or older than its TTL."""
        urls = self.epg_urls()
        if not urls:
            return False
        guide = self.epg_guide()
        if not force and not guide.is_stale():
            return guide.has_data()
        refs = self.epg_channel_refs()
        if not refs:
            return False
        timeout = safe_int(self.settings.get("timeout"), 20)
        guide.refresh(urls, refs, user_agent=to_text(self.source.get("ua")),
                      timeout=timeout, progress=progress)
        return guide.has_data()

    def epg_programmes(self, item):
        try:
            return self.epg_guide().programmes_for(item)
        except Exception:
            return []

    def epg_now_next(self, item, at=None):
        current, upcoming = now_next(self.epg_programmes(item), at=at)
        return current, upcoming

    def _category(self, cat_id, name, count=0):
        return {"id": to_text(cat_id), "name": name, "count": safe_int(count)}

    def _page_slice(self, items, page):
        size = _page_size(self.settings)
        page = max(1, safe_int(page, 1))
        start = (page - 1) * size
        return items[start:start + size], len(items)


class M3UBackend(BaseBackend):
    kind = "m3u"

    def __init__(self, source, store):
        BaseBackend.__init__(self, source, store)
        self.live = []
        self.vod = []
        self.series = []
        self._series_index = {}
        self._live_groups = {}
        self._vod_groups = {}
        self._series_groups = {}
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
            if payload.get("epg_urls") is None:
                # Cache written before EPG support: re-read the playlist once
                # to discover its url-tvg header.  If the network is down, the
                # old catalogue still remains usable without EPG.
                try:
                    return self.refresh(force=True)
                except Exception:
                    self._apply(payload)
                    return True
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
        epg_urls = playlist_epg_urls(text, base_url=url)
        catalogue = build_catalogue(items, meta={
            "kind": "m3u",
            "url": url,
            "epg_urls": epg_urls,
        })
        self._apply(catalogue)
        if progress:
            progress(_("Saving playlist ..."))
        self.store.save_cache(self.source_id, catalogue)
        if force:
            # Channel ids may have changed, so an old mapping cannot be trusted.
            self.store.clear_epg_cache(self.source_id)
            self._epg_guide = None
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
        self.live = payload.get("live") or payload.get("channels") or []
        self.vod = payload.get("vod") or []
        self.series = payload.get("series") or []
        self._epg_urls = payload.get("epg_urls") or []
        for item in self.live:
            if not item.get("fav_key"):
                item["fav_key"] = favourite_key(item)
        for item in self.vod:
            if not item.get("fav_key"):
                item["fav_key"] = favourite_key(item)
        self._live_groups = _group_items(self.live, "Live TV")
        self._vod_groups = _group_items(self.vod, "Movies")
        self._series_groups = _group_items(self.series, "Series")
        self._series_index = {}
        for entry in self.series:
            self._series_index[entry.get("id")] = entry
        self.loaded = True

    def _ensure_live_groups(self):
        if not self._live_groups and self.live:
            self._live_groups = _group_items(self.live, "Live TV")

    def prefetch(self, progress=None, force=False):
        if force or not self.loaded:
            self.refresh(force=force, progress=progress)
        return self.counts()

    def counts(self):
        return {
            "live": len(self.live),
            "vod": len(self.vod),
            "series": len(self.series),
            "episodes": sum([len(entry.get("episodes") or []) for entry in self.series]),
        }

    # ---------------------------------------------------------------- live
    def live_categories(self):
        self._ensure_live_groups()
        groups = sorted(self._live_groups.keys(), key=_sort_key)
        categories = [
            self._category("all", _("All channels"), len(self.live)),
            self._category("fav", u"\u2605 " + _("Favorites"), self.favorites_count()),
        ]
        for group in groups:
            if self.hide_adult() and is_adult_category(group):
                continue
            count = len(self._live_groups.get(group) or [])
            categories.append(self._category("g:" + group, group, count))
        return categories

    def live_items(self, category_id, query=""):
        self._ensure_live_groups()
        try:
            if category_id == "fav":
                favorites = self.favorite_keys()
                items = [item for item in self.live if self.favorite_key(item) in favorites]
            elif category_id.startswith("g:"):
                items = self._live_groups.get(category_id[2:]) or []
                if not items and self.live:
                    group = category_id[2:]
                    items = [item for item in self.live if (item.get("group") or "Live TV") == group]
            else:
                items = list(self.live)
            if query:
                items = [item for item in items if _match(item.get("name"), query)]
            return items
        except Exception as error:
            _logger.exception("M3U live_items failed: %s", error)
            # Ultimate fallback: scan the full list.
            if category_id == "fav":
                try:
                    favorites = set(self.store.favorites(self.source_id))
                    return [item for item in self.live if self.favorite_key(item) in favorites]
                except Exception:
                    return []
            elif category_id.startswith("g:"):
                group = category_id[2:]
                return [item for item in self.live if (item.get("group") or "Live TV") == group]
            else:
                return list(self.live)

    def favorite_key(self, item):
        return item.get("fav_key") or favourite_key(item)

    # ------------------------------------------------------------------ epg
    def epg_urls(self):
        urls = BaseBackend.epg_urls(self)
        if urls:
            return urls
        derived = derive_epg_url(self.source.get("url"))
        return [derived] if derived else []

    def epg_channel_refs(self):
        refs = []
        for item in self.live:
            refs.append({
                "tvg_id": to_text(item.get("tvg_id")),
                "names": [item.get("tvg_name"), item.get("name")],
            })
        return refs

    # ----------------------------------------------------------------- vod
    def vod_categories(self):
        groups = sorted(self._vod_groups.keys(), key=_sort_key)
        categories = [self._category("all", _("All"), len(self.vod))]
        for group in groups:
            if self.hide_adult() and is_adult_category(group):
                continue
            count = len(self._vod_groups.get(group) or [])
            categories.append(self._category("g:" + group, group, count))
        return categories

    def vod_items(self, category_id, query="", page=1):
        if category_id.startswith("g:"):
            items = self._vod_groups.get(category_id[2:]) or []
        else:
            items = self.vod
        if query:
            items = [item for item in items if _match(item.get("name"), query)]
        return self._page_slice(items, page)

    # -------------------------------------------------------------- series
    def series_categories(self):
        groups = sorted(self._series_groups.keys(), key=_sort_key)
        categories = [self._category("all", _("All"), len(self.series))]
        for group in groups:
            if self.hide_adult() and is_adult_category(group):
                continue
            count = len(self._series_groups.get(group) or [])
            categories.append(self._category("g:" + group, group, count))
        return categories

    def series_items(self, category_id, query="", page=1):
        if category_id.startswith("g:"):
            items = self._series_groups.get(category_id[2:]) or []
        else:
            items = self.series
        if query:
            items = [item for item in items if _match(item.get("name"), query)]
        return self._page_slice(items, page)

    def seasons(self, series_id):
        entry = self._series_index.get(series_id)
        if not entry:
            return []
        counts = {}
        for episode in entry.get("episodes") or []:
            season = safe_int(episode.get("season"), 0)
            counts[season] = counts.get(season, 0) + 1
        seasons = []
        for season in sorted(counts.keys()):
            seasons.append({
                "id": str(season),
                "name": (_("Season {0}").format(season) if season else _("All episodes")),
                "count": counts[season],
            })
        return seasons

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
        self.vod = []
        self.series = []
        self.vod_ready = False
        self.series_ready = False
        self.loaded = False
        self._cache_ts = 0
        self._vod_cache = {}
        self._series_cache = {}
        self._live_groups = {}
        self._vod_groups = {}
        self._series_groups = {}

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
            if progress:
                progress(_("Saving portal data ..."))
            # Store the compact channel rows rather than the large raw portal
            # objects.  This keeps the cache smaller and makes list rendering
            # independent from the portal's field names.
            payload["channels"] = self.channels
            payload["channels_compact"] = True
            payload["vod"] = []
            payload["series"] = []
            payload["vod_ready"] = False
            payload["series_ready"] = False
            self.store.save_cache(self.source_id, payload)
            if force:
                self.store.clear_epg_cache(self.source_id)
                self._epg_guide = None
            info = client.account or {}
            expires = _expiry_of(info)
            status = "expired" if is_expired(expires) else ("active" if expires else "active")
            self.store.update_info(
                self.source_id,
                channels=len(self.channels),
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
        raw_channels = payload.get("channels") or payload.get("live") or []
        if payload.get("channels_compact"):
            self.channels = raw_channels
        else:
            self.channels = []
            for raw in raw_channels:
                group = to_text(raw.get("tv_genre_id") or raw.get("genre_id") or "")
                self.channels.append(self._channel(raw, group, "live"))
        self.vod = payload.get("vod") or []
        self.series = payload.get("series") or []
        self.vod_ready = bool(payload.get("vod_ready")) if "vod_ready" in payload else False
        self.series_ready = bool(payload.get("series_ready")) if "series_ready" in payload else False
        self._cache_ts = safe_int(payload.get("ts")) or now()
        self._rebuild_indexes()
        self.loaded = True

    def _ensure_live_groups(self):
        if not self._live_groups and self.channels:
            self._live_groups = _group_items(self.channels, "")

    def _rebuild_indexes(self):
        self._live_groups = _group_items(self.channels, "")
        self._vod_groups = _group_items(self.vod, "")
        self._series_groups = _group_items(self.series, "")

    def counts(self):
        info = self.source.get("info") or {}
        return {
            "live": len(self.channels) or safe_int(info.get("channels")),
            "vod": len(self.vod) if self.vod_ready else safe_int(info.get("vod")),
            "series": len(self.series) if self.series_ready else safe_int(info.get("series")),
        }

    def prefetch(self, progress=None, force=False):
        """Fetch every live/VOD/series category into the persistent cache.

        The live bouquet is already stored by :meth:`refresh`; this method
        walks the portal's VOD and series pages once so every category opens
        instantly afterwards, even when the box has no network at that moment.
        """
        if force or not self.loaded:
            self.refresh(force=force, progress=progress)
        if not self.loaded:
            return self.counts()
        try:
            if force or not self.vod_ready:
                self._prefetch_vod(progress)
            if force or not self.series_ready:
                self._prefetch_series(progress)
        finally:
            self._save_catalogue()
        return self.counts()

    def _prefetch_client(self, progress=None):
        client = self._make_client()
        if not client.token:
            if progress:
                progress(_("Connecting to the portal ..."))
            client.auth()
        return client

    def _all_pages(self, fetch, genre, label=u"", progress=None):
        rows = []
        page = 1
        total = 0
        while page <= 500:
            batch, reported = fetch(genre, page)
            if not batch:
                break
            rows.extend(batch)
            total = max(total, safe_int(reported))
            if total and len(rows) >= total:
                break
            if progress:
                progress(u"{0} {1}".format(label, len(rows)))
            page += 1
        return rows

    def _prefetch_catalogue(self, client, kind, genres, progress=None):
        if kind == "vod":
            label = _("Preparing movies ...")
            fetch = lambda genre, page: client.ordered_list("vod", genre, page)
            build = lambda raw, genre: self._vod(raw, genre, "vod")
            fallback_attr = ""
        else:
            label = _("Preparing series ...")
            fetch = lambda genre, page: client.series_page(genre, page)
            build = lambda raw, genre: self._vod(raw, genre, "series")
            fallback_attr = "series_flag"
        genre_list = []
        for genre in genres or []:
            if not isinstance(genre, dict) or not genre.get("id"):
                continue
            if (self.hide_adult() and
                    (genre.get("censored") or is_adult_category(genre.get("name")))):
                continue
            genre_list.append(genre)
        if not genre_list:
            if genres:
                # Every category was filtered as adult content.
                return [], 1
            genre_list = [{"id": "*", "name": _("All")}]
        catalog = {}
        ok_count = 0
        last_error = None
        for index, genre in enumerate(genre_list):
            genre_id = to_text(genre.get("id"))
            if progress:
                progress(u"{0} {1}/{2}".format(label, index + 1, len(genre_list)))
            try:
                raws = self._all_pages(fetch, genre_id, label, progress)
                ok_count += 1
            except PrefetchCancelled:
                raise
            except Exception as error:  # one bad category must not abort all
                last_error = error
                continue
            for raw in raws:
                if not isinstance(raw, dict):
                    continue
                ident = to_text(raw.get("id") or raw.get("movie_id") or
                                raw.get("series_id") or "")
                if not ident:
                    ident = short_hash(to_text(raw.get("name")) + "|" +
                                       to_text(raw.get("cmd")), 12)
                item = catalog.get(ident)
                if item is None:
                    item = build(raw, genre_id)
                    item["groups"] = [genre_id]
                    item["group"] = to_text(genre.get("name") or item.get("group"))
                    catalog[ident] = item
                elif genre_id not in item["groups"]:
                    item["groups"].append(genre_id)
        if not catalog and kind == "series" and fallback_attr:
            # Portals that only expose series through the VOD endpoint still
            # get a usable series list without another network pass.
            for item in self.vod:
                if not item.get(fallback_attr):
                    continue
                copy = dict(item)
                copy["kind"] = "series"
                copy["groups"] = list(item.get("groups") or [item.get("group") or ""])
                catalog[item.get("id") or item.get("fav_key")] = copy
        if not ok_count and not catalog:
            raise last_error or MagError(_("The portal did not return any items."))
        return list(catalog.values()), ok_count

    def _prefetch_vod(self, progress=None):
        client = self._prefetch_client(progress)
        genres = self.genres_vod
        if not genres:
            genres = client.vod_categories()
            self.genres_vod = genres
        items, _ok = self._prefetch_catalogue(client, "vod", genres, progress)
        self.vod = items
        self.vod_ready = True
        self._vod_groups = _group_items(self.vod, "")
        self._vod_cache = {}

    def _prefetch_series(self, progress=None):
        client = self._prefetch_client(progress)
        genres = self.genres_vod
        items, _ok = self._prefetch_catalogue(client, "series", genres, progress)
        if not items and not genres:
            # No VOD categories and no dedicated series endpoint: derive a
            # series catalogue from the prefetched VOD items flagged as such.
            for item in self.vod:
                if not item.get("series_flag"):
                    continue
                copy = dict(item)
                copy["kind"] = "series"
                copy["groups"] = list(item.get("groups") or [item.get("group") or ""])
                items.append(copy)
        self.series = items
        self.series_ready = True
        self._series_groups = _group_items(self.series, "")
        self._series_cache = {}

    def _save_catalogue(self):
        payload = {
            "kind": "mag",
            "ts": self._cache_ts or now(),
            "genres_itv": self.genres_itv,
            "genres_vod": self.genres_vod,
            "channels": self.channels,
            "channels_compact": True,
            "vod": self.vod,
            "series": self.series,
            "vod_ready": self.vod_ready,
            "series_ready": self.series_ready,
            "portal": self.source.get("url"),
            "mac": self.source.get("mac"),
        }
        self.store.save_cache(self.source_id, payload)

    # ---------------------------------------------------------------- live
    def live_categories(self):
        self._ensure_live_groups()
        categories = [
            self._category("all", _("All channels"), len(self.channels)),
            self._category("fav", u"\u2605 " + _("Favorites"), self.favorites_count()),
        ]
        for genre in self.genres_itv:
            if self.hide_adult() and (genre.get("censored") or is_adult_category(genre.get("name"))):
                continue
            count = len(self._live_groups.get(to_text(genre.get("id"))) or [])
            categories.append(self._category("g:" + to_text(genre.get("id")), genre["name"], count))
        return categories

    def live_items(self, category_id, query=""):
        self._ensure_live_groups()
        if self.channels:
            if category_id == "fav":
                favorites = self.favorite_keys()
                items = [item for item in self.channels
                         if self.favorite_key(item) in favorites]
            elif category_id.startswith("g:"):
                items = self._live_groups.get(category_id[2:]) or []
                if not items and self.channels:
                    group = category_id[2:]
                    items = [item for item in self.channels if to_text(item.get("group") or "") == group]
            else:
                items = self.channels
            if query:
                items = [item for item in items if _match(item.get("name"), query)]
            return items
        items = []
        if category_id not in ("all", "fav"):
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
                if page * _page_size(self.settings) >= total:
                    break
                page += 1
        return items

    def epg_channel_refs(self):
        refs = []
        for item in self.channels:
            refs.append({
                "tvg_id": to_text(item.get("tvg_id") or ""),
                "names": [item.get("tvg_name"), item.get("name")],
            })
        return refs

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
            "link": to_text(raw.get("link") or ""),
            "tvg_id": to_text(raw.get("tvg_id") or raw.get("xmltv_id") or ""),
            "tvg_name": to_text(raw.get("tvg_name") or ""),
            "fav_key": "mag:" + (ident or short_hash(name, 10)),
            "number": safe_int(raw.get("number")),
        }
        return item

    # ----------------------------------------------------------------- vod
    def vod_categories(self):
        info = self.source.get("info") or {}
        total = len(self.vod) if self.vod_ready else safe_int(info.get("vod"))
        categories = [self._category("all", _("All"), total)]
        for genre in self.genres_vod:
            if self.hide_adult() and (genre.get("censored") or is_adult_category(genre.get("name"))):
                continue
            genre_id = to_text(genre.get("id"))
            count = len(self._vod_groups.get(genre_id) or []) if self.vod_ready else 0
            categories.append(self._category("g:" + genre_id, genre["name"], count))
        return categories

    def vod_items(self, category_id, query="", page=1):
        if self.vod_ready:
            if category_id.startswith("g:"):
                items = self._vod_groups.get(category_id[2:]) or []
            else:
                items = self.vod
            if query:
                items = [item for item in items if _match(item.get("name"), query)]
            return self._page_slice(items, page)
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
        ident = to_text(raw.get("id") or raw.get("movie_id") or raw.get("series_id") or "")
        name = to_text(raw.get("name") or raw.get("title") or "?")
        screenshot = raw.get("screenshot_uri") or raw.get("cover") or raw.get("logo") or raw.get("poster") or ""
        item = {
            "id": ident,
            "name": name,
            "logo": portal_logo(self.source.get("url"), screenshot),
            "group": to_text(group),
            "kind": kind,
            "cmd": to_text(raw.get("cmd") or ""),
            "link": to_text(raw.get("link") or ""),
            "series_id": to_text(raw.get("movie_id") or raw.get("series_id") or ""),
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
        info = self.source.get("info") or {}
        total = len(self.series) if self.series_ready else safe_int(info.get("series"))
        categories = [self._category("all", _("All"), total)]
        for genre in self.genres_vod:
            if self.hide_adult() and (genre.get("censored") or is_adult_category(genre.get("name"))):
                continue
            genre_id = to_text(genre.get("id"))
            count = len(self._series_groups.get(genre_id) or []) if self.series_ready else 0
            categories.append(self._category("g:" + genre_id, genre["name"], count))
        return categories

    def series_items(self, category_id, query="", page=1):
        if self.series_ready:
            if category_id.startswith("g:"):
                items = self._series_groups.get(category_id[2:]) or []
            else:
                items = self.series
            if query:
                items = [item for item in items if _match(item.get("name"), query)]
            return self._page_slice(items, page)
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
    def _remember_stream_options(self, item, client):
        """Keep the portal headers needed by the stream URL.

        The media request is made by Enigma2, not by the HTTP client used for
        the API, so the User-Agent/Cookie/Referer must travel in the service
        reference.  They are attached to the selected item after create_link()
        and read by stream_options() when the player starts.
        """
        try:
            headers = client.stream_headers()
        except Exception:
            return
        agent = u""
        extra = []
        for key, value in headers.items():
            if key.lower() == "user-agent":
                agent = to_text(value)
            else:
                extra.append(u"{0}={1}".format(to_text(key), to_text(value)))
        item["stream_ua"] = agent
        item["stream_opts"] = u"&".join(extra)

    def stream_options(self, item):
        if item.get("stream_opts") or item.get("stream_ua"):
            return to_text(item.get("stream_ua")), to_text(item.get("stream_opts"))
        return BaseBackend.stream_options(self, item)

    def resolve(self, item):
        cmd = to_text(item.get("cmd") or item.get("link") or "").strip()
        if not cmd:
            raise MagError(_("This stream is not playable"))
        client = self._make_client()
        if not client.token:
            client.handshake()
        kind = item.get("kind") or "vod"
        series_id = 0
        if kind == "episode":
            series_id = safe_int(item.get("series_id"), 0)
        try:
            url = client.create_link(kind, cmd, series=series_id)
        except MagError:
            if not series_id:
                raise
            url = client.create_link(kind, cmd, series=0)
        self._remember_stream_options(item, client)
        return url

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
    if info.get("prefetch") == "running":
        return info.get("prefetch_text") or _("Preparing ...")
    if info.get("prefetch") == "error" and not safe_int(info.get("channels")):
        return _("Preparation failed")
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
