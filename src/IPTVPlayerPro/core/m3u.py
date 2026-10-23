# -*- coding: utf-8 -*-
"""M3U / M3U8 playlist parser and catalogue builder."""

from __future__ import absolute_import

import re
from collections import OrderedDict

try:
    from urllib.parse import urljoin
except ImportError:  # Python 2
    from urlparse import urljoin

from .util import md5, now, short_hash, strip_quality, to_text

ATTR_RE = re.compile(r'([A-Za-z0-9_-]+)\s*=\s*"([^"]*)"')
SERIES_RE = re.compile(r"(?i)\bS(\d{1,2})[\s._-]*E(\d{1,3})\b")
SERIES_ALT_RE = re.compile(r"(?i)\b(\d{1,2})x(\d{1,3})\b")
YEAR_RE = re.compile(r"(?:\(|\[|\s)((?:19|20)\d{2})(?:\)|\]|\s|$)")
QUALITY_RE = re.compile(r"(?i)\b(?:4k|uhd|fhd|hd|sd|hevc|h\.?264|h\.?265|multi|dubbed|subbed)\b")

VOD_WORDS = (
    "vod", "movie", "movies", "film", "films", "cinema", "films ", "افلام", u"أفلام",
    u"فيلم", u"سينما", "peliculas", "filmes",
)
SERIES_WORDS = (
    "series", "serie", "tv series", "tvshows", "tv shows", "shows", u"مسلسل",
    u"مسلسلات", u"دراما", "novelas", "telenovelas",
)
ADULT_WORDS = ("adult", "xxx", "porn", "erotic", "18+", u"للبالغين", u"اباحي", u"إباحي")
LIVE_WORDS = ("live", "tv", u"بث", u"مباشر", "channel", "channels")


def _normalise(value):
    return to_text(value).strip().lower()


def _contains_any(text, words):
    for word in words:
        if word and word in text:
            return True
    return False


def _entry_type(name, group, url, attrs):
    kind = _normalise(attrs.get("type") or attrs.get("tvg-type") or "")
    if "movie" in kind:
        return "vod"
    if "series" in kind:
        return "series"

    text = _normalise("{0} {1}".format(group, name))
    lower_url = _normalise(url)
    if _contains_any(text, SERIES_WORDS) or "/series/" in lower_url or "type=series" in lower_url:
        return "series"
    if _contains_any(text, VOD_WORDS) or "/movie/" in lower_url or "/movies/" in lower_url or "/vod/" in lower_url or "type=movie" in lower_url:
        return "vod"

    if SERIES_RE.search(name) or SERIES_ALT_RE.search(name):
        return "series"
    return "live"


def _series_parts(name):
    match = SERIES_RE.search(name)
    if match:
        season, episode = int(match.group(1)), int(match.group(2))
        title = name[:match.start()].strip(" -_.|")
        return title, season, episode
    match = SERIES_ALT_RE.search(name)
    if match:
        season, episode = int(match.group(1)), int(match.group(2))
        title = name[:match.start()].strip(" -_.|")
        return title, season, episode
    return strip_quality(name), 0, 0


def _split_extinf(line):
    body = line[len("#EXTINF:"):]
    in_quote = False
    for index, char in enumerate(body):
        if char == '"':
            in_quote = not in_quote
        elif char == "," and not in_quote:
            return body[:index], body[index + 1:].strip()
    return body, ""


def parse_playlist(text, base_url="", progress=None):
    """Return a list of normalized items from an M3U/M3U8 text."""
    text = to_text(text)
    text = text.lstrip(u"\ufeff")
    lines = text.splitlines()
    total_lines = len(lines)
    items = []
    current = None
    pending_group = ""
    pending_ua = ""
    pending_opts = []
    parsed_count = 0
    last_progress_update = 0
    
    for raw_line in lines:
        parsed_count += 1
        # Throttle progress updates
        if progress and total_lines > 1000:
            if parsed_count - last_progress_update >= max(100, total_lines // 100):
                progress(parsed_count, total_lines)
                last_progress_update = parsed_count
        
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#EXTINF"):
            header, title = _split_extinf(line)
            attrs = dict(ATTR_RE.findall(header))
            # duration is the first token of the header
            parts = header.strip().split()
            duration = parts[0] if parts else ""
            name = title or attrs.get("tvg-name") or attrs.get("title") or ""
            group = attrs.get("group-title") or attrs.get("group") or pending_group or ""
            logo = attrs.get("tvg-logo") or attrs.get("logo") or ""
            current = {
                "name": to_text(name).strip(),
                "attrs": attrs,
                "group": to_text(group).strip(),
                "logo": to_text(logo).strip(),
                "duration": duration,
                "ua": pending_ua,
                "opts": "&".join(pending_opts),
            }
            pending_ua = ""
            pending_opts = []
            continue
        if line.startswith("#EXTGRP:"):
            pending_group = line[len("#EXTGRP:"):].strip()
            if current is not None and not current.get("group"):
                current["group"] = pending_group
            continue
        if line.startswith("#EXTVLCOPT:"):
            option = line[len("#EXTVLCOPT:"):].strip()
            low = option.lower()
            if low.startswith("http-user-agent="):
                pending_ua = option.split("=", 1)[1].strip()
                if current is not None:
                    current["ua"] = pending_ua
            elif low.startswith(("http-referrer=", "http-referer=",
                                 "http-origin=", "http-cookie=")):
                pending_opts.append(option)
                if current is not None:
                    existing = to_text(current.get("opts"))
                    current["opts"] = "&".join(
                        [part for part in (existing, option) if part])
            continue
        if line.startswith("#"):
            continue
        if current is None:
            # URL without EXTINF: still show it, the provider knows why.
            current = {"name": line.split("/")[-1][:80], "attrs": {},
                       "group": pending_group, "logo": "", "duration": "",
                       "ua": pending_ua, "opts": "&".join(pending_opts)}
        url = line
        options = ""
        if "|" in url:
            url, options = url.split("|", 1)
        url = url.strip()
        option_text = "&".join(
            [part for part in (to_text(current.get("opts")), options.strip()) if part])
        if not url:
            current = None
            continue
        if base_url and not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
            try:
                url = urljoin(base_url, url)
            except Exception:
                pass
        name = to_text(current.get("name") or "").strip()
        group = to_text(current.get("group") or "").strip()
        logo = to_text(current.get("logo") or "").strip()
        kind = _entry_type(name, group, url, current.get("attrs") or {})
        item = {
            "name": name,
            "url": url,
            "logo": logo,
            "group": group or _default_group(kind),
            "kind": kind,
            "ua": current.get("ua") or "",
            "opts": option_text,
            "duration": current.get("duration") or "",
            "tvg_id": (current.get("attrs") or {}).get("tvg-id") or "",
            "tvg_name": (current.get("attrs") or {}).get("tvg-name") or "",
        }
        if kind == "series":
            title, season, episode = _series_parts(name)
            item["series"] = title or name
            item["season"] = season
            item["episode"] = episode
        item["id"] = short_hash(kind + "|" + (item.get("tvg_id") or "") + "|" + url, 14)
        item["fav_key"] = favourite_key(item)
        items.append(item)
        current = None
        pending_ua = ""
        pending_opts = []
    
    # Final progress update
    if progress:
        progress(total_lines, total_lines)
    
    return items


def _default_group(kind):
    if kind == "vod":
        return "Movies"
    if kind == "series":
        return "Series"
    return "Live TV"


def build_catalogue(items, meta=None):
    """Group parsed items into live / vod / series lists."""
    live = []
    vod = []
    series = OrderedDict()
    seen_live = set()
    seen_vod = set()

    for item in items:
        kind = item.get("kind")
        if kind == "series":
            key = "{0}|{1}".format(item.get("group") or "", item.get("series") or item.get("name"))
            entry = series.get(key)
            if entry is None:
                entry = {
                    "id": short_hash("series|" + key, 14),
                    "name": item.get("series") or item.get("name"),
                    "group": item.get("group") or "Series",
                    "logo": item.get("logo") or "",
                    "episodes": [],
                    "kind": "series",
                    "year": _year_of(item.get("name")),
                }
                series[key] = entry
            if not entry.get("logo") and item.get("logo"):
                entry["logo"] = item["logo"]
            entry["episodes"].append(item)
        elif kind == "vod":
            if item["url"] in seen_vod:
                continue
            seen_vod.add(item["url"])
            item["year"] = _year_of(item.get("name"))
            vod.append(item)
        else:
            if item["url"] in seen_live:
                continue
            seen_live.add(item["url"])
            live.append(item)

    series_list = []
    for entry in series.values():
        entry["episodes"].sort(key=lambda e: (e.get("season") or 0, e.get("episode") or 0, e.get("name") or ""))
        entry["count"] = len(entry["episodes"])
        entry["seasons"] = len(set([e.get("season") or 0 for e in entry["episodes"]]))
        series_list.append(entry)

    catalogue = {
        "ts": now(),
        "live": live,
        "vod": vod,
        "series": series_list,
        "counts": {
            "live": len(live),
            "vod": len(vod),
            "series": len(series_list),
            "episodes": sum([entry.get("count", 0) for entry in series_list]),
        },
    }
    if meta:
        catalogue.update(meta)
    return catalogue


def _year_of(name):
    match = YEAR_RE.search(to_text(name))
    if match:
        return match.group(1)
    return ""


def group_names(items):
    names = []
    seen = set()
    for item in items:
        group = item.get("group") or ""
        if group and group not in seen:
            seen.add(group)
            names.append(group)
    return names


def is_adult_category(name):
    return _contains_any(_normalise(name), ADULT_WORDS)


def favourite_key(item):
    return "m3u:" + md5("{0}|{1}".format(item.get("name", ""), item.get("url", "")))[:16]
