# -*- coding: utf-8 -*-
"""Small WebIF-style HTTP server for adding M3U and MAG sources.

The server uses only the Python standard library and can therefore run on
every Enigma2 image (Python 2.7 and Python 3).  It writes directly to the
plugin configuration, so an added source is available the next time the
plugin menu is opened.
"""

from __future__ import absolute_import

import base64
import json
import os
import socket
import threading

try:
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from socketserver import ThreadingMixIn
    from urllib.parse import parse_qs, urlsplit
except ImportError:  # Python 2
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
    from SocketServer import ThreadingMixIn
    from urlparse import parse_qs, urlsplit

from ..core.backends import create_backend
from ..core.epg import clean_epg_urls
from ..core.mag import is_valid_mac, normalize_mac, normalize_portal
from ..core.store import Store, VERSION
from ..core.util import safe_int, to_bytes, to_text
from .page import PAGE

DEFAULT_PORT = 8099
MAX_BODY = 1024 * 1024

LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "images", "logo.png")

try:
    _LOGO_DATA = open(LOGO_PATH, "rb").read()
except Exception:
    _LOGO_DATA = None


class ApiError(Exception):
    def __init__(self, message, status=400):
        Exception.__init__(self, message)
        self.status = status


def _error_text(error):
    if isinstance(error, ApiError) and error.args:
        return to_text(error.args[0])
    return to_text(error) or u"request failed"


def _local_addresses():
    """Return the receiver LAN addresses (best effort)."""
    result = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = info[4][0]
            if address and not address.startswith("127.") and address not in result:
                result.append(address)
    except Exception:
        pass
    if not result:
        try:
            probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                probe.connect(("8.8.8.8", 80))
                address = probe.getsockname()[0]
            finally:
                probe.close()
            if address and not address.startswith("127."):
                result.append(address)
        except Exception:
            pass
    if not result:
        result.append("127.0.0.1")
    return result


def _valid_url(value):
    try:
        parts = urlsplit(to_text(value).strip())
    except Exception:
        return False
    return parts.scheme.lower() in ("http", "https") and bool(parts.netloc)


def _truthy(value):
    return to_text(value).strip().lower() in ("1", "true", "yes", "on", "y")


def _default_name(kind, url, mac):
    try:
        host = urlsplit(url).netloc or url
    except Exception:
        host = url
    if kind == "mag":
        return u"MAG - {0}".format(host)
    return u"M3U - {0}".format(host)


def _find_source(store, kind, url, mac):
    for source in store.sources:
        if to_text(source.get("type")) != kind:
            continue
        if to_text(source.get("url")).strip() != url:
            continue
        if kind == "mag" and normalize_mac(source.get("mac")) != mac:
            continue
        return source
    return None


def _source_view(source, active_id):
    info = source.get("info") or {}
    return {
        "id": to_text(source.get("id")),
        "type": to_text(source.get("type")) or "m3u",
        "name": to_text(source.get("name")),
        "url": to_text(source.get("url")),
        "mac": to_text(source.get("mac")),
        "ua": to_text(source.get("ua")),
        "epg_url": to_text(source.get("epg_url")),
        "active": source.get("id") == active_id,
        "status": to_text(info.get("status")),
        "expires": to_text(info.get("expires")),
        "channels": safe_int(info.get("channels")),
        "vod": safe_int(info.get("vod")),
        "series": safe_int(info.get("series")),
        "episodes": safe_int(info.get("episodes")),
        "updated": safe_int(info.get("updated") or source.get("updated")),
    }


def _state_payload(store, context):
    return {
        "ok": True,
        "version": VERSION,
        "port": context.port,
        "urls": context.urls(),
        "pin_required": bool(to_text(store.settings.get("web_pin")).strip()),
        "active": store.active_id(),
        "sources": [_source_view(source, store.active_id()) for source in store.sources],
    }


class WebContext(object):
    def __init__(self, port, config_dir=None, cache_dir=None):
        self.port = port
        self.config_dir = config_dir
        self.cache_dir = cache_dir
        self.lock = threading.Lock()

    def store(self):
        return Store(config_dir=self.config_dir, cache_dir=self.cache_dir)

    def pin(self):
        try:
            return to_text(self.store().settings.get("web_pin")).strip()
        except Exception:
            return u""

    def urls(self):
        return ["http://{0}:{1}/".format(address, self.port) for address in _local_addresses()]


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class Handler(BaseHTTPRequestHandler):
    server_version = "IPTVPlayerPro/" + VERSION
    protocol_version = "HTTP/1.0"

    def log_message(self, fmt, *args):
        # Keep Enigma2's console clean; useful errors are returned to the page.
        pass

    # ------------------------------------------------------------- responses
    def _send(self, body, content_type="text/html; charset=utf-8", status=200):
        data = to_bytes(body)
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        try:
            self.wfile.write(data)
        except Exception:
            pass

    def _json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        self._send(body, "application/json; charset=utf-8", status)

    def _unauthorized(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="IPTV Player Pro"')
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _authorized(self):
        pin = self.server.context.pin()
        if not pin:
            return True
        header = self.headers.get("Authorization") or ""
        if not header.lower().startswith("basic "):
            self._unauthorized()
            return False
        try:
            encoded = header.split(None, 1)[1].strip()
            decoded = to_text(base64.b64decode(encoded.encode("ascii")))
            user, separator, supplied = decoded.partition(":")
        except Exception:
            self._unauthorized()
            return False
        if separator and supplied == pin:
            return True
        self._unauthorized()
        return False

    def _read_payload(self):
        length = safe_int(self.headers.get("Content-Length"), 0)
        if length <= 0:
            return {}
        if length > MAX_BODY:
            raise ApiError(u"Request is too large", 413)
        raw = self.rfile.read(length)
        content_type = (self.headers.get("Content-Type") or "").lower()
        if "application/json" in content_type:
            try:
                data = json.loads(to_text(raw) or "{}")
            except Exception:
                raise ApiError(u"Invalid JSON data", 400)
            if not isinstance(data, dict):
                raise ApiError(u"Invalid request data", 400)
            return data
        try:
            values = parse_qs(to_text(raw), keep_blank_values=True)
        except Exception:
            raise ApiError(u"Invalid request data", 400)
        result = {}
        for key, value in values.items():
            result[key] = value[0] if isinstance(value, list) and value else value
        return result

    def _require_post_header(self):
        if (self.headers.get("X-IPTVPro") or "") != "1":
            raise ApiError(u"Unauthorized request", 403)

    # ------------------------------------------------------------------ GET
    def do_GET(self):
        try:
            if not self._authorized():
                return
            path = urlsplit(self.path).path
            if path in ("/", "/index.html"):
                self._send(PAGE)
            elif path == "/logo.png":
                if _LOGO_DATA:
                    self._send(_LOGO_DATA, "image/png")
                else:
                    self._json({"ok": False, "error": u"Logo not found"}, 404)
            elif path == "/api/state":
                store = self.server.context.store()
                self._json(_state_payload(store, self.server.context))
            elif path == "/api/health":
                self._json({"ok": True, "version": VERSION})
            elif path in ("/favicon.ico",):
                self.send_response(204)
                self.send_header("Content-Length", "0")
                self.end_headers()
            else:
                self._json({"ok": False, "error": u"Page not found"}, 404)
        except Exception as error:
            self._json({"ok": False, "error": _error_text(error)}, 500)

    # ----------------------------------------------------------------- POST
    def do_POST(self):
        try:
            if not self._authorized():
                return
            self._require_post_header()
            path = urlsplit(self.path).path
            context = self.server.context
            payload = self._read_payload()

            if path == "/api/source":
                store, source, updated = self._save_source(context, payload)
                self._json({
                    "ok": True,
                    "updated": updated,
                    "source": _source_view(source, store.active_id()),
                    "state": _state_payload(store, context),
                })
                return

            if path == "/api/activate":
                source_id = to_text(payload.get("id")).strip()
                with context.lock:
                    store = context.store()
                    if not source_id or store.get_source(source_id) is None:
                        raise ApiError(u"Source not found", 404)
                    store.set_active(source_id)
                self._json({"ok": True, "state": _state_payload(store, context)})
                return

            if path == "/api/delete":
                source_id = to_text(payload.get("id")).strip()
                with context.lock:
                    store = context.store()
                    if not source_id or store.get_source(source_id) is None:
                        raise ApiError(u"Source not found", 404)
                    store.delete_source(source_id)
                self._json({"ok": True, "state": _state_payload(store, context)})
                return

            if path == "/api/refresh":
                source_id = to_text(payload.get("id")).strip()
                store = context.store()
                source = store.get_source(source_id)
                if source is None:
                    raise ApiError(u"Source not found", 404)
                backend = create_backend(source, store)
                if backend is None:
                    raise ApiError(u"Source type is not supported", 400)
                try:
                    backend.refresh(force=True)
                except Exception as error:
                    raise ApiError(_error_text(error), 502)
                store = context.store()
                self._json({"ok": True, "state": _state_payload(store, context)})
                return

            self._json({"ok": False, "error": u"Page not found"}, 404)
        except ApiError as error:
            self._json({"ok": False, "error": _error_text(error)}, error.status)
        except Exception as error:
            self._json({"ok": False, "error": _error_text(error)}, 500)

    # --------------------------------------------------------------- source
    def _save_source(self, context, payload):
        kind = to_text(payload.get("type") or payload.get("kind") or "m3u").strip().lower()
        if kind in ("portal", "stalker", "magbox"):
            kind = "mag"
        if kind not in ("m3u", "mag"):
            raise ApiError(u"Source type is not supported", 400)

        url = to_text(payload.get("url")).strip()
        mac = u""
        if kind == "mag":
            url = normalize_portal(url)
            mac = normalize_mac(payload.get("mac"))
            if not _valid_url(url):
                raise ApiError(u"Enter a valid portal URL", 400)
            if not is_valid_mac(mac):
                raise ApiError(u"Invalid MAC address", 400)
        elif not _valid_url(url):
            raise ApiError(u"Enter a valid M3U URL", 400)

        name = to_text(payload.get("name")).strip()
        ua = to_text(payload.get("ua")).strip()
        epg_url = to_text(payload.get("epg_url")).strip()
        if epg_url and not clean_epg_urls(epg_url):
            raise ApiError(u"Enter a valid EPG URL", 400)
        activate = _truthy(payload.get("activate", 1))

        with context.lock:
            store = context.store()
            existing = _find_source(store, kind, url, mac)
            if existing is not None:
                values = {"name": name or existing.get("name") or _default_name(kind, url, mac), "ua": ua}
                if epg_url:
                    values["epg_url"] = epg_url
                store.update_source(existing.get("id"), **values)
                store.clear_cache(existing.get("id"))
                if activate:
                    store.set_active(existing.get("id"))
                source = store.get_source(existing.get("id"))
                updated = True
            else:
                if not name:
                    name = _default_name(kind, url, mac)
                source = store.new_source(kind, name, url, mac, ua)
                if epg_url:
                    store.update_source(source.get("id"), epg_url=epg_url)
                    source = store.get_source(source.get("id"))
                if activate:
                    store.set_active(source.get("id"))
                updated = False
            return store, source, updated


class WebManager(object):
    def __init__(self):
        self._lock = threading.RLock()
        self._server = None
        self._thread = None
        self._port = 0
        self._host = ""
        self.last_error = u""

    def start(self, store=None, port=None, host="0.0.0.0"):
        store = store or Store()
        port = safe_int(port if port is not None else store.settings.get("web_port"), DEFAULT_PORT)
        with self._lock:
            if self._server is not None and self._port == port and self._host == host:
                return True
            self._stop_locked()
            context = WebContext(port, store.config_dir, store.cache_dir)
            try:
                server = ThreadedHTTPServer((host, port), Handler)
            except Exception as error:
                self.last_error = to_text(error)
                self._server = None
                self._thread = None
                return False
            self._port = server.server_address[1]
            context.port = self._port
            server.context = context
            thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.4})
            thread.setDaemon(True)
            thread.start()
            self._server = server
            self._thread = thread
            self._host = host
            self.last_error = u""
            return True

    def _stop_locked(self):
        server = self._server
        thread = self._thread
        self._server = None
        self._thread = None
        self._port = 0
        self._host = ""
        if server is not None:
            try:
                server.shutdown()
            except Exception:
                pass
            try:
                server.server_close()
            except Exception:
                pass
        if thread is not None and thread.is_alive():
            thread.join(2.0)

    def stop(self):
        with self._lock:
            self._stop_locked()

    def running(self):
        with self._lock:
            return self._server is not None

    def port(self):
        with self._lock:
            return self._port

    def urls(self):
        with self._lock:
            port = self._port
        if not port:
            return []
        return ["http://{0}:{1}/".format(address, port) for address in _local_addresses()]

    def ensure(self, store):
        if not bool(store.settings.get("web_enabled", True)):
            self.stop()
            return False
        port = safe_int(store.settings.get("web_port"), DEFAULT_PORT)
        return self.start(store, port=port)


manager = WebManager()
