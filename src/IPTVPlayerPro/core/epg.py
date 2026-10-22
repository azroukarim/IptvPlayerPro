# -*- coding: utf-8 -*-
"""XMLTV EPG support shared by the M3U and MAG backends.

The parser is deliberately limited to what the plugin displays: the current
and next programme for a channel.  It reads XMLTV as a stream, keeps only a
short window of programmes, and stores a compact JSON cache.  Only the Python
standard library is used so the module works on Python 2.7 and Python 3.
"""

from __future__ import absolute_import

import calendar
import io
import os
import re
import threading
import time

try:
    import xml.etree.ElementTree as ET
except ImportError:  # pragma: no cover - Python 2 ships ElementTree
    import xml.etree.ElementTree as ET

try:
    from urllib.parse import parse_qs, urljoin, urlsplit, urlunsplit
except ImportError:  # Python 2
    from urlparse import parse_qs, urljoin, urlsplit, urlunsplit

from .i18n import _
from .net import Http, NetError, build_url
from .util import (clean_html, now, py2, read_json, safe_int, strip_quality,
                   to_bytes, to_text, write_json)


EPG_CACHE_HOURS = 6
EPG_KEEP_SECONDS = 3600
# Only now/next is displayed.  Keeping a little more than the cache TTL is
# enough and avoids large JSON files on receivers with thousands of channels.
EPG_WINDOW_SECONDS = 8 * 3600
EPG_TITLE_LIMIT = 180

_XMLTV_TIME_RE = re.compile(
    r"^\s*(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})?(?:\.\d+)?"
    r"(?:\s*([+-])(\d{2}):?(\d{2}))?"
)
_EPG_URL_RE = re.compile(
    r"(?i)(?:url-tvg|x-tvg-url|tvg-url)\s*=\s*[\"']?([^\"'\s>]+)"
)
_BIDI_RE = re.compile(u"[\u200e\u200f\u202a-\u202e]")
_LEADING_CODE_RE = re.compile(u"^[a-z]{2,3}\\s*[:\\-|]\\s*")


class EpgError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)

    def __unicode__(self):
        return to_text(self.args[0]) if self.args else u"EPG error"

    def __str__(self):
        value = self.__unicode__()
        return to_bytes(value) if py2() else value


def normalize_name(value):
    """Return a stable channel-name key for XMLTV name fallback matching."""
    text = to_text(value)
    if not text:
        return u""
    text = _BIDI_RE.sub(u" ", text)
    text = strip_quality(text).lower()
    text = _LEADING_CODE_RE.sub(u"", text)
    text = re.sub(u"(?i)\\b(?:hd|sd|fhd|uhd|4k|hevc|multi|arabic|subbed|dubbed)\\b", u" ", text)
    # Keep Arabic letters, Latin letters and digits.  Punctuation, provider
    # separators and quality suffixes vary far too much between playlists.
    text = re.sub(u"[^0-9a-z\u0600-\u06ff\ufb50-\ufdff\ufe70-\ufeff]+", u"", text)
    return text


def item_keys(item):
    """Return lookup keys for an M3U/MAG channel in priority order."""
    item = item or {}
    keys = []
    tvg_id = to_text(item.get("tvg_id") or item.get("xmltv_id")).strip()
    if tvg_id:
        keys.append(u"tvg:" + tvg_id.lower())
    for value in (item.get("tvg_name"), item.get("name")):
        normalized = normalize_name(value)
        if normalized:
            key = u"name:" + normalized
            if key not in keys:
                keys.append(key)
    return keys


def _valid_epg_url(value):
    text = to_text(value).strip()
    low = text.lower()
    return low.startswith("http://") or low.startswith("https://")


def clean_epg_urls(value, base_url=u""):
    """Split, resolve and de-duplicate a list of XMLTV URLs."""
    text = to_text(value).replace(u"&amp;", u"&").strip()
    if not text:
        return []
    result = []
    for part in re.split(r"\s*[,|]\s*", text):
        part = part.strip()
        if not part:
            continue
        if base_url and not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", part):
            try:
                part = urljoin(base_url, part)
            except Exception:
                pass
        if _valid_epg_url(part) and part not in result:
            result.append(part)
    return result


def playlist_epg_urls(text, base_url=u""):
    """Read url-tvg / x-tvg-url / tvg-url from an M3U header."""
    header = to_text(text)
    if not header:
        return []
    # Limit the scan to the header area.  Some playlists contain thousands of
    # channel lines before the first URL, so 32 KiB is a safe boundary.
    match = _EPG_URL_RE.search(header[:32768])
    if not match:
        return []
    return clean_epg_urls(match.group(1), base_url=base_url)


def derive_epg_url(url):
    """Derive an Xtream Codes xmltv.php URL from a get.php/player_api URL."""
    text = to_text(url).strip()
    if not text:
        return u""
    try:
        parts = urlsplit(text)
    except Exception:
        return u""
    query = parse_qs(parts.query)
    username = to_text((query.get("username") or [u""])[0]).strip()
    password = to_text((query.get("password") or [u""])[0]).strip()
    if not username or not password:
        return u""
    path = parts.path or u"/"
    lower = path.lower()
    if lower.endswith("/get.php") or lower.endswith("/player_api.php"):
        base_path = path.rsplit("/", 1)[0] + u"/xmltv.php"
    else:
        base_path = u"/xmltv.php"
    base = urlunsplit((parts.scheme, parts.netloc, base_path, u"", u""))
    return build_url(base, [("username", username), ("password", password)])


def parse_xmltv_time(value):
    """Convert an XMLTV timestamp to a Unix timestamp (local when no offset)."""
    match = _XMLTV_TIME_RE.match(to_text(value))
    if not match:
        return 0
    year, month, day, hour, minute = [int(match.group(index)) for index in range(1, 6)]
    second = int(match.group(6) or 0)
    if not (1 <= month <= 12 and 1 <= day <= 31 and 0 <= hour <= 23
            and 0 <= minute <= 59 and 0 <= second <= 59):
        return 0
    try:
        if match.group(7):
            offset = int(match.group(8)) * 3600 + int(match.group(9)) * 60
            stamp = calendar.timegm((year, month, day, hour, minute, second, 0, 0, 0))
            if match.group(7) == u"+":
                stamp -= offset
            else:
                stamp += offset
            return int(stamp)
        return int(time.mktime((year, month, day, hour, minute, second, 0, 0, -1)))
    except Exception:
        return 0


def clock_text(timestamp):
    try:
        return to_text(time.strftime("%H:%M", time.localtime(int(timestamp))))
    except Exception:
        return u""


def now_next(programmes, at=None):
    """Return ``(current, next)`` programme lists for a Unix timestamp."""
    current = None
    upcoming = None
    moment = safe_int(at if at is not None else now())
    ordered = sorted(programmes or [], key=lambda programme: safe_int(programme[0]))
    for programme in ordered:
        start = safe_int(programme[0])
        stop = safe_int(programme[1])
        if start <= moment < stop:
            current = programme
        elif start > moment:
            upcoming = programme
            break
    if current is not None and upcoming is not None:
        # An overlapping programme that already started is not "next".
        if safe_int(upcoming[0]) < safe_int(current[1]) and safe_int(upcoming[0]) <= moment:
            upcoming = None
    if upcoming is None:
        threshold = safe_int(current[1]) if current is not None else moment
        for programme in ordered:
            start = safe_int(programme[0])
            if start >= threshold and start > moment:
                upcoming = programme
                break
    return current, upcoming


def _programme_title(element):
    fallback = u""
    for child in element:
        tag = to_text(child.tag).split(u"}")[-1].lower()
        if tag != u"title":
            continue
        value = clean_html(child.text or u"").replace(u"\n", u" ").strip()
        if not value:
            continue
        if not fallback:
            fallback = value
        language = to_text(child.get("lang") or u"").lower()
        if language.startswith("ar"):
            return value
    return fallback


def _channel_names(data):
    """First pass: collect XMLTV channel ids and their display names."""
    channels = {}
    try:
        source = io.BytesIO(data)
        context = ET.iterparse(source, events=("start", "end"))
        try:
            _event, root = next(context)
        except StopIteration:
            return channels
        for event, element in context:
            if event != "end":
                continue
            tag = to_text(element.tag).split(u"}")[-1].lower()
            if tag == "channel":
                channel_id = to_text(element.get("id") or u"").strip()
                if channel_id:
                    names = set()
                    for child in element:
                        child_tag = to_text(child.tag).split(u"}")[-1].lower()
                        if child_tag == "display-name":
                            normalized = normalize_name(child.text)
                            if normalized:
                                names.add(normalized)
                    if names:
                        channels[channel_id] = names
                element.clear()
                try:
                    root.clear()
                except Exception:
                    pass
        return channels
    except Exception as error:
        raise EpgError(_("The EPG file is not valid XML.") + u" " + to_text(error))


def _build_mapping(channels, refs):
    """Map playlist lookup keys to XMLTV channel ids."""
    exact_ids = dict((channel_id.lower(), channel_id) for channel_id in channels)
    wanted_ids = set()
    mapping = {}
    for ref in refs:
        tvg_id = to_text(ref.get("tvg_id") or ref.get("xmltv_id")).strip()
        if tvg_id:
            actual = exact_ids.get(tvg_id.lower(), tvg_id)
            wanted_ids.add(actual)
            mapping.setdefault(u"tvg:" + tvg_id.lower(), [])
            if actual not in mapping[u"tvg:" + tvg_id.lower()]:
                mapping[u"tvg:" + tvg_id.lower()].append(actual)

    names_to_ids = {}
    for channel_id, names in channels.items():
        for name in names:
            names_to_ids.setdefault(name, []).append(channel_id)
    for ref in refs:
        for value in ref.get("names") or []:
            normalized = normalize_name(value)
            if not normalized:
                continue
            key = u"name:" + normalized
            matches = names_to_ids.get(normalized) or []
            if len(matches) != 1:
                continue
            mapping.setdefault(key, [])
            if matches[0] not in mapping[key]:
                mapping[key].append(matches[0])
            wanted_ids.add(matches[0])
    return mapping, wanted_ids


def _parse_programmes(data, wanted_ids):
    """Second pass: keep only programmes whose channel is relevant."""
    programmes = {}
    moment = now()
    lower_bound = moment - EPG_KEEP_SECONDS
    upper_bound = moment + EPG_WINDOW_SECONDS
    try:
        source = io.BytesIO(data)
        context = ET.iterparse(source, events=("start", "end"))
        try:
            _event, root = next(context)
        except StopIteration:
            return programmes
        for event, element in context:
            if event != "end":
                continue
            tag = to_text(element.tag).split(u"}")[-1].lower()
            if tag == "programme":
                channel_id = to_text(element.get("channel") or u"").strip()
                if channel_id in wanted_ids:
                    start = parse_xmltv_time(element.get("start"))
                    stop = parse_xmltv_time(element.get("stop"))
                    title = _programme_title(element)
                    if start > 0 and stop > start and title:
                        if stop > lower_bound and start < upper_bound:
                            programmes.setdefault(channel_id, []).append(
                                [start, stop, title[:EPG_TITLE_LIMIT]])
                element.clear()
                try:
                    root.clear()
                except Exception:
                    pass
        return programmes
    except Exception as error:
        raise EpgError(_("The EPG file is not valid XML.") + u" " + to_text(error))


def _normalise_programmes(programmes):
    clean = {}
    for channel_id, entries in (programmes or {}).items():
        merged = {}
        for entry in entries or []:
            try:
                start = safe_int(entry[0])
                stop = safe_int(entry[1])
                title = to_text(entry[2]).replace(u"\n", u" ").strip()
            except Exception:
                continue
            if start <= 0 or stop <= start or not title:
                continue
            key = (start, stop, title)
            merged[key] = [start, stop, title]
        ordered = sorted(merged.values(), key=lambda programme: programme[0])
        for index, programme in enumerate(ordered):
            if programme[1] <= programme[0]:
                if index + 1 < len(ordered) and ordered[index + 1][0] > programme[0]:
                    programme[1] = ordered[index + 1][0]
                else:
                    programme[1] = programme[0] + 3600
        if ordered:
            clean[channel_id] = ordered
    return clean


def _merge_mapping(target, extra):
    for key, ids in (extra or {}).items():
        values = target.setdefault(key, [])
        for channel_id in ids or []:
            if channel_id not in values:
                values.append(channel_id)
    return target


def _merge_programmes(target, extra):
    for channel_id, entries in (extra or {}).items():
        values = target.setdefault(channel_id, [])
        values.extend(entries or [])
    return target


class EpgGuide(object):
    """Cached EPG for one source."""

    def __init__(self, store, source_id):
        self.store = store
        self.source_id = source_id
        self.path = store.epg_file(source_id)
        self._lock = threading.RLock()
        self._loaded = False
        self._mapping = {}
        self._programmes = {}
        self._ts = 0
        self._urls = []

    # --------------------------------------------------------------- cache
    def load(self):
        with self._lock:
            if self._loaded:
                return
            self._loaded = True
            payload = read_json(self.path, None)
            if not isinstance(payload, dict):
                return
            mapping = payload.get("mapping") or {}
            if isinstance(mapping, dict):
                for key, value in mapping.items():
                    if isinstance(value, list):
                        ids = [to_text(item) for item in value if to_text(item)]
                    else:
                        ids = [to_text(value)] if to_text(value) else []
                    if ids:
                        self._mapping[to_text(key)] = ids
            programmes = payload.get("programmes") or {}
            if isinstance(programmes, dict):
                for channel_id, entries in programmes.items():
                    if isinstance(entries, list):
                        self._programmes[to_text(channel_id)] = entries
            self._ts = safe_int(payload.get("ts"))
            self._urls = [to_text(url) for url in payload.get("urls") or []]

    def save(self):
        with self._lock:
            payload = {
                "ts": self._ts,
                "urls": self._urls,
                "mapping": self._mapping,
                "programmes": self._programmes,
            }
            return write_json(self.path, payload)

    def is_stale(self):
        self.load()
        with self._lock:
            if self._ts <= 0:
                return True
            return (now() - self._ts) > EPG_CACHE_HOURS * 3600

    def has_data(self):
        self.load()
        with self._lock:
            return bool(self._programmes)

    def clear(self):
        with self._lock:
            self._mapping = {}
            self._programmes = {}
            self._ts = 0
            self._urls = []
            self._loaded = True
        try:
            os.remove(self.path)
        except Exception:
            pass

    # --------------------------------------------------------------- lookup
    def programmes_for(self, item):
        self.load()
        with self._lock:
            for key in item_keys(item):
                ids = self._mapping.get(key)
                if not ids and key.startswith(u"tvg:"):
                    channel_id = key[4:]
                    if channel_id in self._programmes:
                        ids = [channel_id]
                if not ids:
                    continue
                merged = []
                for channel_id in ids:
                    merged.extend(self._programmes.get(channel_id) or [])
                if merged:
                    merged.sort(key=lambda programme: safe_int(programme[0]))
                    return [list(programme) for programme in merged]
        return []

    def now_next(self, item, at=None):
        current, upcoming = now_next(self.programmes_for(item), at=at)
        return current, upcoming

    # -------------------------------------------------------------- refresh
    def refresh(self, urls, refs, user_agent=u"", timeout=20, progress=None):
        """Download and parse XMLTV documents, replacing the cached guide."""
        urls = clean_epg_urls(u",".join(to_text(url) for url in (urls or [])))
        if not urls:
            raise EpgError(_("No EPG URL configured."))
        refs = [ref for ref in (refs or []) if ref]
        if not refs:
            raise EpgError(_("No channels to match the EPG with."))
        mapping = {}
        programmes = {}
        errors = []
        for index, url in enumerate(urls):
            if progress:
                try:
                    progress(_("Downloading EPG ..."))
                except Exception:
                    pass
            try:
                http = Http(timeout=timeout, user_agent=user_agent or None,
                            retries=0)
                data, _handle = http.get(url)
                if not data:
                    raise EpgError(_("The EPG file is empty."))
                channels = _channel_names(data)
                part_mapping, wanted_ids = _build_mapping(channels, refs)
                part_programmes = _parse_programmes(data, wanted_ids)
                _merge_mapping(mapping, part_mapping)
                _merge_programmes(programmes, part_programmes)
            except (NetError, EpgError) as error:
                errors.append(to_text(error))
            except Exception as error:  # noqa: BLE001
                errors.append(to_text(error))
        clean_programmes = _normalise_programmes(programmes)
        if not mapping and not clean_programmes:
            detail = errors[0] if errors else _("No matching channels found.")
            raise EpgError(detail)
        with self._lock:
            self._mapping = mapping
            self._programmes = clean_programmes
            self._urls = list(urls)
            # Do not suppress a retry for six hours when the guide had no
            # usable programmes for the configured channels.
            self._ts = now() if clean_programmes else 0
            self._loaded = True
        self.save()
        return bool(clean_programmes)
