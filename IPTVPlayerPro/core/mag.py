# -*- coding: utf-8 -*-
"""MAG / Stalker portal client (handshake, profile, genres, VOD, series)."""

from __future__ import absolute_import

import hashlib
import json
import re

try:
    from urllib.parse import urlsplit, urlunsplit
except ImportError:  # Python 2
    from urlparse import urlsplit, urlunsplit

from .i18n import _
from .net import Http, NetError, build_url
from .util import (json_loads_tolerant, now, py2, safe_int, to_bytes, to_text)

MAG_UA = (
    "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 "
    "(KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3"
)
MAG_XUA = "Model: MAG254; Link: WiFi"
MAG_IMAGE_VERSION = "218"
MAG_VER = (
    "ImageDescription: 0.2.18-r23-250; ImageDate: Thu Sep 13 11:31:19 EEST 2018; "
    "PORTAL version: 5.6.2; API Version: JS API version: 343; "
    "STB API version: 146; Player Engine version: 0x58c"
)
TIMEZONE = "Europe/London"

MAC_RE = re.compile(r"^([0-9A-F]{2}):([0-9A-F]{2}):([0-9A-F]{2}):([0-9A-F]{2}):([0-9A-F]{2}):([0-9A-F]{2})$")
STREAM_PREFIX_RE = re.compile(r"^(?:ffmpeg|ffrt|auto|mpegts|rtp|ffmpegts|live)\s+", re.I)


class MagError(Exception):
    def __init__(self, message, details=None):
        Exception.__init__(self, message)
        self.details = details

    def __unicode__(self):
        message = to_text(self.args[0]) if self.args else u"portal error"
        if self.details:
            return u"{0} ({1})".format(message, to_text(self.details))
        return message

    def __str__(self):
        value = self.__unicode__()
        return to_bytes(value) if py2() else value


def normalize_mac(value):
    text = to_text(value).upper().replace("-", ":").replace(".", ":").replace(" ", "")
    text = re.sub(r"[^0-9A-F]", "", text)
    if len(text) != 12:
        return ""
    return ":".join([text[i:i + 2] for i in range(0, 12, 2)])


def is_valid_mac(value):
    return bool(MAC_RE.match(normalize_mac(value)))


def normalize_portal(value):
    text = to_text(value).strip()
    if not text:
        return ""
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", text):
        text = "http://" + text
    parts = urlsplit(text)
    path = parts.path.rstrip("/")
    for suffix in ("/server/load.php", "/portal.php", "/load.php", "/c"):
        if path.endswith(suffix):
            path = path[:-len(suffix)]
            break
    path = path.rstrip("/")
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def api_endpoints(portal):
    root = normalize_portal(portal)
    if not root:
        return []
    if root.endswith("/stalker_portal"):
        candidates = [root + "/server/load.php", root + "/portal.php", root + "/c/portal.php"]
    else:
        candidates = [
            root + "/server/load.php",
            root + "/portal.php",
            root + "/stalker_portal/server/load.php",
            root + "/c/portal.php",
        ]
    result = []
    for candidate in candidates:
        if candidate not in result:
            result.append(candidate)
    return result


def _stream_url(value):
    text = to_text(value).strip()
    if not text:
        return ""
    text = STREAM_PREFIX_RE.sub("", text, count=1).strip()
    if text.startswith("//"):
        text = "http:" + text
    if text.lower().startswith(("http://", "https://", "rtmp://", "rtsp://", "udp://", "rtp://")):
        return text
    # Some portals hand back a quoted string or a JSON fragment.
    match = re.search(r"(https?://[^\s\"']+)", text)
    if match:
        return match.group(1)
    return text


class MagClient(object):
    def __init__(self, portal, mac, serial=None, device_id=None, timeout=20):
        self.portal = normalize_portal(portal)
        self.mac = normalize_mac(mac)
        if not self.portal:
            raise MagError(_("Invalid portal URL"))
        if not is_valid_mac(self.mac):
            raise MagError(_("Invalid MAC address"))
        self.serial = to_text(serial).strip() or hashlib.md5(self.mac.encode("utf-8")).hexdigest()[:13]
        if device_id:
            self.device_id = to_text(device_id).strip()
        else:
            self.device_id = hashlib.sha1(self.serial.encode("utf-8")).hexdigest().upper()
        self.device_id2 = self.device_id
        self.signature = hashlib.sha256(self.serial.encode("utf-8")).hexdigest().upper()
        self.http = Http(timeout=timeout, user_agent=MAG_UA)
        self.endpoints = api_endpoints(self.portal)
        self.endpoint = self.endpoints[0] if self.endpoints else ""
        self.token = ""
        self.profile = {}
        self.account = {}
        self.genres_itv = []
        self.genres_vod = []

    # ------------------------------------------------------------- headers
    def _cookie(self):
        parts = [
            "mac={0}".format(self.mac),
            "stb_lang=en",
            "timezone={0}".format(TIMEZONE),
        ]
        if self.token:
            parts.append("token={0}".format(self.token))
        return "; ".join(parts)

    def _headers(self):
        root = self.portal or ""
        return {
            "User-Agent": MAG_UA,
            "X-User-Agent": MAG_XUA,
            "Referer": root + "/c/",
            "Cookie": self._cookie(),
            "Accept": "*/*",
            "Connection": "Keep-Alive",
        }

    def stream_headers(self):
        """Headers some portals require for the media URL itself."""
        root = self.portal or ""
        return {
            "User-Agent": MAG_UA,
            "Referer": root + "/c/",
            "Cookie": self._cookie(),
        }

    # ------------------------------------------------------------- request
    def _request(self, params, endpoint=None):
        params = dict(params)
        params["JsHttpRequest"] = "1-xml"
        url = build_url(endpoint or self.endpoint, params)
        try:
            raw = self.http.get_text(url, headers=self._headers())
        except NetError as error:
            raise MagError(str(error))
        try:
            return json_loads_tolerant(raw)
        except Exception:
            raise MagError(_("The portal returned an invalid response"), to_text(raw[:120]))

    @staticmethod
    def _js(data):
        if isinstance(data, dict):
            if "js" in data:
                return data.get("js")
            return data
        return data

    @staticmethod
    def _as_list(js):
        if isinstance(js, list):
            return js
        if isinstance(js, dict):
            for key in ("data", "results", "items", "genres", "channels"):
                value = js.get(key)
                if isinstance(value, list):
                    return value
            for value in js.values():
                if isinstance(value, list):
                    return value
        return []

    def _check_error(self, js):
        if isinstance(js, dict):
            error = js.get("error") or js.get("msg")
            if error and not js.get("data"):
                raise MagError(to_text(error))
        return js

    # ---------------------------------------------------------------- auth
    def handshake(self, force=False):
        if self.token and not force:
            return self.token
        errors = []
        for endpoint in self.endpoints:
            try:
                data = self._request({
                    "type": "stb",
                    "action": "handshake",
                    "token": "",
                    "prehash": "0",
                }, endpoint=endpoint)
            except MagError as error:
                errors.append(to_text(error))
                continue
            js = self._js(data)
            token = ""
            if isinstance(js, dict):
                token = to_text(js.get("token") or "")
            elif isinstance(js, list) and js and isinstance(js[0], dict):
                token = to_text(js[0].get("token") or "")
            if token:
                self.endpoint = endpoint
                self.token = token
                return token
            if isinstance(js, dict):
                message = js.get("error") or js.get("msg")
                if message:
                    errors.append(to_text(message))
        raise MagError(_("The portal did not return a token. Check the URL and the MAC."), u" | ".join(errors[:2]))

    def profile_info(self):
        self.handshake()
        metrics = json.dumps({
            "mac": self.mac,
            "sn": self.serial,
            "model": "MAG254",
            "type": "STB",
            "uid": "",
            "random": "",
        }, separators=(",", ":"))
        data = self._request({
            "type": "stb",
            "action": "get_profile",
            "hd": "1",
            "ver": MAG_VER,
            "num_banks": "2",
            "sn": self.serial,
            "stb_type": "MAG254",
            "client_type": "STB",
            "image_version": MAG_IMAGE_VERSION,
            "video_out": "hdmi",
            "device_id": self.device_id,
            "device_id2": self.device_id2,
            "signature": self.signature,
            "auth_second_step": "1",
            "hw_version": "1.7-BD-00",
            "not_valid_token": "0",
            "metrics": metrics,
            "api_signature": "",
            "prehash": "0",
        })
        js = self._js(data)
        self._check_error(js)
        if isinstance(js, list):
            js = js[0] if js else {}
        if not isinstance(js, dict) or not js:
            raise MagError(_("The portal did not accept the MAC address."))
        self.profile = js
        return js

    def account_info(self):
        if not self.token:
            self.handshake()
        info = {}
        try:
            data = self._request({"type": "account_info", "action": "get_main_info"})
            js = self._js(data)
            if isinstance(js, dict):
                info.update(js)
            elif isinstance(js, list) and js and isinstance(js[0], dict):
                info.update(js[0])
        except MagError:
            pass
        if self.profile:
            for key in ("mac", "name", "phone", "end_date", "expire_billing_date", "tariff_expired_date", "login", "status"):
                if key in self.profile and key not in info:
                    info[key] = self.profile[key]
        self.account = info
        return info

    def auth(self):
        self.handshake(force=True)
        self.profile_info()
        self.account_info()
        return self.account

    # ------------------------------------------------------------- genres
    def itv_genres(self):
        data = self._request({"type": "itv", "action": "get_genres"})
        items = self._as_list(self._check_error(self._js(data)))
        self.genres_itv = [self._genre(item) for item in items if isinstance(item, dict)]
        return self.genres_itv

    def vod_categories(self):
        data = None
        try:
            data = self._request({"type": "vod", "action": "get_categories"})
        except MagError:
            data = self._request({"type": "vod", "action": "get_genres"})
        items = self._as_list(self._check_error(self._js(data)))
        self.genres_vod = [self._genre(item) for item in items if isinstance(item, dict)]
        return self.genres_vod

    @staticmethod
    def _genre(item):
        return {
            "id": to_text(item.get("id") or item.get("genre_id") or item.get("category_id") or ""),
            "name": to_text(item.get("title") or item.get("name") or item.get("alias") or "?"),
            "alias": to_text(item.get("alias") or ""),
            "censored": safe_int(item.get("censored") or 0),
        }

    # ----------------------------------------------------------- listings
    def all_channels(self):
        data = self._request({"type": "itv", "action": "get_all_channels"})
        js = self._check_error(self._js(data))
        items = self._as_list(js)
        return [item for item in items if isinstance(item, dict)]

    def ordered_list(self, kind, category, page=1):
        params = {
            "type": kind,
            "action": "get_ordered_list",
            "p": safe_int(page, 1),
            "sortby": "number" if kind == "itv" else "added",
            "hd": "0",
        }
        if kind == "itv":
            params["genre"] = category
            params["fav"] = "0"
        else:
            params["category"] = category
            params["genre"] = "0"
            params["not_ended"] = "0"
        data = self._request(params)
        js = self._check_error(self._js(data))
        items = self._as_list(js)
        total = 0
        if isinstance(js, dict):
            total = safe_int(js.get("total_items") or js.get("total") or 0)
        if not items and page == 1:
            # Some portals only understand the other key.
            params.pop("genre" if kind == "itv" else "category", None)
            params["category" if kind == "itv" else "genre"] = category
            data = self._request(params)
            js = self._check_error(self._js(data))
            items = self._as_list(js)
            if not total and isinstance(js, dict):
                total = safe_int(js.get("total_items") or 0)
        if not total:
            total = len(items)
        return [item for item in items if isinstance(item, dict)], total

    def series_page(self, category, page=1, movie_id=None, season_id=None):
        params = {
            "type": "vod",
            "action": "get_ordered_list",
            "p": safe_int(page, 1),
            "sortby": "added",
            "is_series": "1",
        }
        if movie_id:
            params["movie_id"] = movie_id
            params["season_id"] = season_id if season_id is not None else 0
            params["episode_id"] = 0
        else:
            params["category"] = category
            params["genre"] = "0"
        data = self._request(params)
        js = self._check_error(self._js(data))
        items = self._as_list(js)
        total = 0
        if isinstance(js, dict):
            total = safe_int(js.get("total_items") or 0)
        if not total:
            total = len(items)
        return [item for item in items if isinstance(item, dict)], total

    # ------------------------------------------------------------ playback
    def create_link(self, kind, cmd, series=0):
        cmd = to_text(cmd).strip()
        if not cmd:
            raise MagError(_("This item has no stream command."))
        params = {
            "type": "vod" if kind in ("vod", "series", "episode") else "itv",
            "action": "create_link",
            "cmd": cmd,
            "series": series or 0,
            "forced_storage": "undefined",
            "disable_ad": "0",
            "download": "0",
        }
        if params["type"] == "itv":
            params["force_ch_link_check"] = "0"
        data = self._request(params)
        js = self._js(data)
        if isinstance(js, list):
            js = js[0] if js else {}
        if isinstance(js, dict):
            self._check_error(js)
            url = js.get("cmd") or js.get("url") or js.get("link") or ""
        else:
            url = js
        url = _stream_url(url)
        if not url or not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
            raise MagError(_("The portal did not return a playable link."), to_text(url)[:120])
        return url


def portal_logo(portal, value):
    """Make relative portal artwork absolute."""
    text = to_text(value).strip()
    if not text:
        return ""
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", text):
        return text
    if text.startswith("//"):
        return "http:" + text
    root = normalize_portal(portal)
    if text.startswith("/"):
        return root + text
    return root + "/" + text
