# -*- coding: utf-8 -*-
"""Desktop tests for the local web interface (no Enigma2 imports)."""

from __future__ import absolute_import, print_function

import base64
import json
import os
import shutil
import sys
import tempfile

try:
    from urllib.error import HTTPError
    from urllib.request import (ProxyHandler, Request, build_opener)
except ImportError:  # Python 2
    from urllib2 import HTTPError, ProxyHandler, Request, build_opener

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from IPTVPlayerPro.core.store import Store  # noqa: E402
from IPTVPlayerPro.web.server import manager  # noqa: E402


def main():
    work = tempfile.mkdtemp(prefix="iptvpro-web-")
    store = Store(config_dir=work, cache_dir=work)
    store.set_setting("m3u_file", os.path.join(work, "m3u.txt"))
    store.set_setting("mac_file", os.path.join(work, "mac.txt"))
    opener = build_opener(ProxyHandler({}))
    base = ""
    try:
        assert manager.start(store, port=0, host="127.0.0.1"), manager.last_error
        base = "http://127.0.0.1:{0}/".format(manager.port())

        def request(path, payload=None, headers=None):
            data = None
            request_headers = dict(headers or {})
            if payload is not None:
                data = json.dumps(payload).encode("utf-8")
                request_headers.setdefault("Content-Type", "application/json")
            req = Request(base + path, data=data, headers=request_headers)
            try:
                response = opener.open(req, timeout=15)
                body = response.read()
                return response.getcode(), body
            except HTTPError as error:
                return error.code, error.read()

        def get_json(path, headers=None):
            status, body = request(path, headers=headers)
            return status, json.loads(body.decode("utf-8"))

        def post_json(path, payload, headers=None):
            merged = {"X-IPTVPro": "1"}
            merged.update(headers or {})
            status, body = request(path, payload, merged)
            return status, json.loads(body.decode("utf-8"))

        # Page is served with both forms.
        status, page = request("")
        assert status == 200
        assert b'id="m3uForm"' in page
        assert b'id="magForm"' in page
        assert b'name="epg_url"' in page
        assert b"api/source" in page

        status, data = get_json("api/state")
        assert status == 200 and data["ok"]
        assert data["sources"] == []

        # Add an M3U source; it should become active.
        status, data = post_json("api/source", {
            "type": "m3u",
            "name": "Test playlist",
            "url": "http://example.com/list.m3u",
            "ua": "VLC/3.0",
            "epg_url": "http://example.com/epg.xml",
            "activate": 1,
        })
        assert status == 200 and data["ok"]
        assert data["updated"] is False
        assert data["source"]["epg_url"] == "http://example.com/epg.xml"
        m3u_id = data["source"]["id"]
        assert data["state"]["active"] == m3u_id
        assert len(data["state"]["sources"]) == 1

        fresh = Store(config_dir=work, cache_dir=work)
        assert len(fresh.sources) == 1
        assert fresh.active_id() == m3u_id
        assert fresh.sources[0]["url"] == "http://example.com/list.m3u"

        # Posting the same URL updates instead of duplicating.
        status, data = post_json("api/source", {
            "type": "m3u",
            "name": "Updated name",
            "url": "http://example.com/list.m3u",
            "activate": 1,
        })
        assert status == 200 and data["updated"] is True
        assert len(data["state"]["sources"]) == 1
        assert data["source"]["name"] == "Updated name"
        assert data["source"]["epg_url"] == "http://example.com/epg.xml"

        # An invalid EPG URL is rejected.
        status, data = post_json("api/source", {
            "type": "m3u",
            "url": "http://example.com/other.m3u",
            "epg_url": "ftp://example.com/epg.xml",
        })
        assert status == 400 and not data["ok"]

        # Invalid MAG MAC is rejected.
        status, data = post_json("api/source", {
            "type": "mag",
            "url": "http://portal.example.com:8080/c/",
            "mac": "00:11:22",
        })
        assert status == 400 and not data["ok"]

        # Valid MAG source is normalized and stored.
        status, data = post_json("api/source", {
            "type": "mag",
            "name": "Test portal",
            "url": "http://portal.example.com:8080/c/",
            "mac": "00-1a-79-12-34-56",
            "activate": 1,
        })
        assert status == 200 and data["ok"]
        mag_id = data["source"]["id"]
        assert data["source"]["mac"] == "00:1A:79:12:34:56"
        assert data["source"]["url"] == "http://portal.example.com:8080"
        assert data["state"]["active"] == mag_id
        assert len(data["state"]["sources"]) == 2

        # Activating another source works.
        status, data = post_json("api/activate", {"id": m3u_id})
        assert status == 200 and data["state"]["active"] == m3u_id

        # Requests without the CSRF header are rejected.
        status, body = request("api/activate", {"id": mag_id}, {"Content-Type": "application/json"})
        assert status == 403

        # Optional PIN protection.
        fresh.set_setting("web_pin", "1234")
        status, body = request("api/state")
        assert status == 401
        token = base64.b64encode(b"admin:1234").decode("ascii")
        status, data = get_json("api/state", {"Authorization": "Basic " + token})
        assert status == 200 and data["ok"]
        fresh.set_setting("web_pin", "")

        # Delete a source.
        status, data = post_json("api/delete", {"id": mag_id})
        assert status == 200 and data["ok"]
        assert len(data["state"]["sources"]) == 1
        assert Store(config_dir=work, cache_dir=work).get_source(mag_id) is None

        status, data = get_json("api/health")
        assert status == 200 and data["ok"]

        print("Web interface tests passed.")
    finally:
        manager.stop()
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
