# -*- coding: utf-8 -*-
"""Small helpers shared by the IPTV Player Pro modules.

The module is deliberately free of any enigma2 import so it can be
executed (and unit tested) on a normal desktop Python installation.
"""

from __future__ import absolute_import

import hashlib
import json
import os
import re
import time

from .i18n import _

try:
    from html import unescape as html_unescape
except ImportError:  # Python 2
    try:
        from HTMLParser import HTMLParser
        _HTML = HTMLParser()

        def html_unescape(text):
            return _HTML.unescape(text)
    except Exception:
        def html_unescape(text):
            return text

try:
    text_type = unicode  # noqa: F821 (Python 2)
    bytes_type = str
except NameError:
    text_type = str
    bytes_type = bytes


ENCODING = "utf-8"


def py2():
    import sys
    return sys.version_info[0] < 3


def to_text(value, encoding=ENCODING):
    if value is None:
        return u""
    if isinstance(value, bytes_type):
        try:
            return value.decode(encoding, "replace")
        except Exception:
            return value.decode("latin-1", "replace")
    if not isinstance(value, text_type):
        return text_type(value)
    return value


def to_bytes(value, encoding=ENCODING):
    if isinstance(value, bytes_type):
        return value
    return to_text(value).encode(encoding, "replace")


def md5(value):
    return hashlib.md5(to_bytes(value)).hexdigest()


def short_hash(value, size=8):
    return md5(value)[:size]


def now():
    return int(time.time())


def safe_int(value, default=0):
    try:
        return int(float(value))
    except Exception:
        return default


def human_count(value):
    try:
        return "{0:,}".format(int(value))
    except Exception:
        return str(value)


# Stream URLs from M3U files and MAG portals often need an HTTP user agent,
# referrer or cookie.  Enigma2's service reference accepts those values after
# a ``#`` and separates them with ``&`` (for example
# ``http://host/live.ts#User-Agent=VLC/3.0&Referer=http://host/``).
_HEADER_ALIASES = {
    "http-user-agent": "User-Agent",
    "user-agent": "User-Agent",
    "useragent": "User-Agent",
    "http-referrer": "Referer",
    "http-referer": "Referer",
    "referer": "Referer",
    "referrer": "Referer",
    "http-origin": "Origin",
    "origin": "Origin",
    "cookie": "Cookie",
    "http-cookie": "Cookie",
}


def _stream_header_parts(value):
    """Split ``Key=Value&Key=Value`` (or VLC ``|`` options) into pairs."""
    text = to_text(value).strip()
    if text.startswith("|"):
        text = text[1:]
    pairs = []
    for chunk in re.split(r"[&|]", text):
        chunk = chunk.strip()
        if not chunk or "=" not in chunk:
            continue
        key, val = chunk.split("=", 1)
        key = to_text(key).strip()
        val = to_text(val).replace("\r", " ").replace("\n", " ").strip()
        if not key or not val:
            continue
        low = key.lower()
        if low in _HEADER_ALIASES:
            key = _HEADER_ALIASES[low]
        elif low.startswith("http-"):
            # Unknown VLC-specific options are not valid HTTP headers.
            continue
        pairs.append((key, val))
    return pairs


def stream_url_with_headers(url, user_agent=u"", options=u""):
    """Return *url* with Enigma2 stream headers appended when needed.

    The service reference parser only understands headers for HTTP/HTTPS/RTSP
    URLs; other protocols are returned unchanged.  Existing headers are kept
    and a playlist value never replaces an explicitly supplied user agent.
    """
    url = to_text(url).strip()
    if not url or not re.match(r"(?i)^(?:https?|rtsp)://", url):
        return url
    base, separator, fragment = url.partition("#")
    headers = _stream_header_parts(fragment)
    seen = set([key.lower() for key, _value in headers])
    for key, value in _stream_header_parts(options):
        if key.lower() not in seen:
            headers.append((key, value))
            seen.add(key.lower())
    agent = to_text(user_agent).replace("\r", " ").replace("\n", " ").strip()
    if agent and "user-agent" not in seen:
        headers.append(("User-Agent", agent))
    if not headers:
        return url
    encoded = "&".join([u"{0}={1}".format(key, value) for key, value in headers])
    return u"{0}#{1}".format(base, encoded)


def human_age(timestamp):
    timestamp = safe_int(timestamp)
    if timestamp <= 0:
        return u""
    delta = now() - timestamp
    if delta < 0:
        delta = 0
    if delta < 60:
        return _("just now")
    if delta < 3600:
        return u"{0} {1}".format(delta // 60, _("min ago"))
    if delta < 86400:
        return u"{0} {1}".format(delta // 3600, _("h ago"))
    return u"{0} {1}".format(delta // 86400, _("d ago"))


def human_expiry(value):
    if value is None:
        return u""
    if isinstance(value, (int, float)):
        value = int(value)
        if value <= 0:
            return u""
        try:
            return time.strftime("%Y-%m-%d", time.localtime(value))
        except Exception:
            return u""
    text = to_text(value).strip()
    if not text or text.lower() in ("null", "none", "0", "0000-00-00", "0000-00-00 00:00:00"):
        return u""
    # The portals use "2026-12-31 23:59:59"; keep the readable part only.
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        return u"{0}-{1}-{2}".format(match.group(1), match.group(2), match.group(3))
    return text


def is_expired(value):
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return 0 < value < now()
    text = to_text(value).strip()
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if not match:
        return False
    try:
        import calendar
        expires = calendar.timegm((int(match.group(1)), int(match.group(2)), int(match.group(3)), 23, 59, 59, 0, 0, 0))
        return expires < now()
    except Exception:
        return False


def clean_html(value):
    text = to_text(value)
    if not text:
        return u""
    text = text.replace("<br />", "\n").replace("<br/>", "\n").replace("<br>", "\n")
    text = re.sub(r"<[^>]+>", " ", text)
    try:
        text = html_unescape(text)
    except Exception:
        text = text.replace("&amp;", "&").replace("&quot;", "\"").replace("&#39;", "'")
    text = text.replace("\r", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def strip_quality(name):
    text = to_text(name)
    text = re.sub(r"(?i)\[\s*(?:4k|fhd|uhd|hd|sd|hevc|h\.?264|h\.?265|multi|arabic|subbed|dubbed)\s*\]", " ", text)
    text = re.sub(r"(?i)\b(?:4k|fhd|uhd|hevc|h\.?264|h\.?265)\b", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip(" -_|")


def key_for(prefix, value):
    return "{0}:{1}".format(prefix, short_hash(value, 12))


def ensure_dir(path):
    if not path:
        return False
    try:
        if not os.path.isdir(path):
            os.makedirs(path)
        return True
    except Exception:
        return False


def atomic_write(path, data):
    """Write *data* (bytes/str) to *path* atomically."""
    folder = os.path.dirname(path)
    if not ensure_dir(folder):
        return False
    tmp = path + ".tmp"
    try:
        handle = open(tmp, "wb")
        try:
            handle.write(to_bytes(data))
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except Exception:
                pass
        finally:
            handle.close()
        try:
            os.replace(tmp, path)
        except AttributeError:
            if os.path.exists(path):
                os.remove(path)
            os.rename(tmp, path)
        return True
    except Exception:
        try:
            os.remove(tmp)
        except Exception:
            pass
        return False


def read_json(path, default=None):
    try:
        handle = open(path, "rb")
        try:
            raw = handle.read()
        finally:
            handle.close()
        if not raw:
            return default
        return json.loads(raw.decode("utf-8-sig"))
    except Exception:
        return default


def write_json(path, payload):
    try:
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        raw = json.dumps(payload, separators=(",", ":"))
    return atomic_write(path, raw)


def json_loads_tolerant(text):
    """Parse JSON that may be wrapped in HTML, prefixed with junk or BOM."""
    if not text:
        raise ValueError("empty response")
    text = to_text(text).strip().lstrip(u"\ufeff")
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        return json.loads(text[start:end + 1])
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end > start:
        return json.loads(text[start:end + 1])
    raise ValueError("invalid JSON response")


def host_of(url):
    text = to_text(url)
    match = re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://([^/]+)", text)
    if match:
        return match.group(1)
    return text[:60]


def ellipsis(text, limit):
    text = to_text(text)
    if limit and len(text) > limit:
        return text[:max(0, limit - 1)] + u"\u2026"
    return text
