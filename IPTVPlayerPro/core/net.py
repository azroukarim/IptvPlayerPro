# -*- coding: utf-8 -*-
"""HTTP client used by the playlist and portal backends.

Only the standard library is used so the plugin works on every image
(Python 2.7 and Python 3.x) without extra dependencies.
"""

from __future__ import absolute_import

import gzip
import json
import socket
import time
import zlib

from .util import json_loads_tolerant, py2, to_bytes, to_text

try:
    from urllib.request import Request, urlopen
    from urllib.parse import urlencode
except ImportError:  # Python 2
    from urllib2 import Request, urlopen
    from urllib import urlencode

try:
    import ssl
except ImportError:
    ssl = None


DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class NetError(Exception):
    def __init__(self, message, status=None):
        Exception.__init__(self, message)
        self.status = status

    def __unicode__(self):
        return to_text(self.args[0]) if self.args else u"network error"

    def __str__(self):
        value = self.__unicode__()
        return to_bytes(value) if py2() else value


_SSL_CTX = None

def _ssl_context():
    global _SSL_CTX
    if _SSL_CTX is not None:
        return _SSL_CTX
    if not ssl:
        return None
    try:
        _SSL_CTX = ssl._create_unverified_context()
        return _SSL_CTX
    except Exception:
        pass
    try:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT if hasattr(ssl, "PROTOCOL_TLS_CLIENT") else ssl.PROTOCOL_SSLv23)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        _SSL_CTX = ctx
        return _SSL_CTX
    except Exception:
        pass
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        _SSL_CTX = ctx
        return _SSL_CTX
    except Exception:
        return None


class Http(object):
    def __init__(self, timeout=60, user_agent=None, retries=4):
        self.timeout = timeout or 60
        self.user_agent = user_agent or DEFAULT_UA
        self.retries = retries
        self.context = _ssl_context()

    # -------------------------------------------------------------- public
    def get(self, url, headers=None, timeout=None, retries=None):
        return self.request(url, headers=headers, timeout=timeout, retries=retries)

    def get_text(self, url, headers=None, timeout=None, retries=None, progress=None):
        """Download text with optional progress callback.
        
        progress callback signature: progress(downloaded_bytes, total_bytes)
        """
        data, _ = self.request(url, headers=headers, timeout=timeout, retries=retries, progress=progress)
        return data

    def get_json(self, url, headers=None, timeout=None, retries=None):
        text = self.get_text(url, headers=headers, timeout=timeout, retries=retries)
        return json_loads_tolerant(text)

    # ------------------------------------------------------------- request
    def request(self, url, headers=None, timeout=None, retries=None, progress=None):
        timeout = timeout or self.timeout
        attempts = self.retries if retries is None else retries
        attempts = max(1, attempts + 1)
        last_error = None
        for attempt in range(attempts):
            try:
                return self._once(url, headers, timeout, progress)
            except NetError as error:
                last_error = error
                if error.status and 400 <= error.status < 500 and error.status not in (408, 429):
                    break
            except Exception as error:
                last_error = NetError(to_text(error))
            if attempt + 1 < attempts:
                time.sleep(0.6)
        raise last_error or NetError("network error")

    def _once(self, url, headers, timeout, progress=None):
        request_headers = {
            "User-Agent": self.user_agent,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "close",
        }
        if headers:
            for key, value in headers.items():
                if value is not None:
                    request_headers[key] = to_text(value)
        request = Request(to_text(url), headers=request_headers)
        handle = None
        try:
            if self.context is not None:
                try:
                    handle = urlopen(request, timeout=timeout, context=self.context)
                except TypeError:
                    handle = urlopen(request, timeout=timeout)
            else:
                handle = urlopen(request, timeout=timeout)
            
            # Get content length for progress
            total_size = 0
            try:
                cl = handle.headers.get("Content-Length")
                if cl:
                    total_size = int(cl)
            except Exception:
                pass
            
            # Stream download with progress
            chunk_size = 8192
            chunks = []
            downloaded = 0
            last_progress_time = 0
            progress_interval = 0.5  # Update progress every 0.5 seconds
            
            while True:
                chunk = handle.read(chunk_size)
                if not chunk:
                    break
                chunks.append(chunk)
                downloaded += len(chunk)
                
                # Throttle progress updates
                if progress and total_size > 0:
                    import time as _time
                    now = _time.time()
                    if now - last_progress_time >= progress_interval:
                        progress(downloaded, total_size)
                        last_progress_time = now
            
            data = b''.join(chunks)
            encoding = ""
            try:
                encoding = (handle.headers.get("Content-Encoding") or "").lower()
            except Exception:
                pass
            data = self._decode_body(data, encoding)
            
            # Final progress update
            if progress and total_size > 0:
                progress(total_size, total_size)
            
            return data, handle
        except Exception as error:
            status = None
            if hasattr(error, "code"):
                status = error.code
                try:
                    body = error.read()
                    snippet = to_text(body[:200]).strip()
                except Exception:
                    snippet = ""
                raise NetError("HTTP {0} {1}".format(status, snippet).strip(), status=status)
            if isinstance(error, socket.timeout):
                raise NetError("Timeout", status=None)
            raise NetError(to_text(error))
        finally:
            try:
                if handle is not None:
                    handle.close()
            except Exception:
                pass

    @staticmethod
    def _decode_body(data, encoding):
        if not data:
            return data
        try:
            if encoding == "gzip" or data[:2] == b"\x1f\x8b":
                decompress = getattr(gzip, "decompress", None)
                if decompress is not None:
                    return decompress(data)
                # Python 2.7 has no gzip.decompress().
                import io
                return gzip.GzipFile(fileobj=io.BytesIO(data)).read()
            if encoding == "deflate":
                try:
                    return zlib.decompress(data)
                except Exception:
                    return zlib.decompress(data, -zlib.MAX_WBITS)
        except Exception:
            pass
        return data


def build_url(base, params):
    """Append urlencoded params to a base URL (keeping existing ones)."""
    if not params:
        return base
    query = urlencode(params)
    if "?" in base:
        if base.endswith("?") or base.endswith("&"):
            return base + query
        return base + "&" + query
    return base + "?" + query


def post_json(url, payload, timeout=20, user_agent=None):
    body = to_bytes(json.dumps(payload))
    request = Request(url, data=body, headers={
        "User-Agent": user_agent or DEFAULT_UA,
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    try:
        handle = urlopen(request, timeout=timeout, context=_ssl_context())
    except TypeError:
        handle = urlopen(request, timeout=timeout)
    try:
        return json_loads_tolerant(handle.read())
    finally:
        try:
            handle.close()
        except Exception:
            pass
