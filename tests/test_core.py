# -*- coding: utf-8 -*-
"""Desktop tests for the core modules (no enigma2 imports)."""

from __future__ import absolute_import, print_function

import calendar
import json
import os
import shutil
import sys
import tempfile
import threading
import time

try:
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from urllib.parse import parse_qs, urlparse
except ImportError:  # Python 2
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
    from urlparse import parse_qs, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from IPTVPlayerPro.core.m3u import build_catalogue, parse_playlist  # noqa: E402
from IPTVPlayerPro.core.epg import (derive_epg_url, parse_xmltv_time,  # noqa: E402
                                    playlist_epg_urls)
from IPTVPlayerPro.core.i18n import set_language  # noqa: E402
from IPTVPlayerPro.core.mag import MagClient, normalize_mac, normalize_portal  # noqa: E402
from IPTVPlayerPro.core.store import Store  # noqa: E402
from IPTVPlayerPro.core.backends import M3UBackend, MagBackend, source_summary  # noqa: E402
from IPTVPlayerPro.core.util import stream_url_with_headers  # noqa: E402

PLAYLIST = u"""#EXTM3U
#EXTINF:-1 tvg-id="news1" tvg-logo="http://img/logos/news.png" group-title="News",News One HD
http://stream.example.com/live/news1.m3u8
#EXTGRP:Sports
#EXTINF:-1,Football 1
http://stream.example.com/live/football.m3u8
#EXTINF:-1 tvg-logo="http://img/movies/inception.jpg" group-title="Movies",Inception (2010)
http://stream.example.com/movie/inception.mp4
#EXTINF:-1 group-title="Movies",The Matrix 1999
#EXTVLCOPT:http-user-agent=SpecialAgent
http://stream.example.com/movie/matrix.mp4
#EXTINF:-1 group-title="Series",Breaking Bad S01E01
http://stream.example.com/series/bb/s01e01.mkv
#EXTINF:-1 group-title="Series",Breaking Bad S01E02
http://stream.example.com/series/bb/s01e02.mkv
#EXTINF:-1 group-title="Series",Dark 1x01
http://stream.example.com/series/dark/101.mkv
#EXTINF:-1,Relative Channel
sub/relative.m3u8
"""


class MockPortal(object):
    def __init__(self):
        self.requests = []

    def response(self, path):
        parsed = urlparse(path)
        query = parse_qs(parsed.query)
        flat = dict((key, value[0]) for key, value in query.items())
        self.requests.append(flat)
        action = flat.get("action", "")
        kind = flat.get("type", "")
        if action == "handshake":
            return {"js": {"token": "TOKEN-123"}}
        if action == "get_profile":
            if "TOKEN-123" not in self.last_cookie:
                return {"js": {}}
            return {"js": {"id": "1", "name": "Tester", "mac": "00:1A:79:11:22:33", "end_date": "2027-01-01 00:00:00"}}
        if action == "get_main_info":
            return {"js": {"mac": "00:1A:79:11:22:33", "end_date": "2027-01-01 00:00:00"}}
        if action == "get_genres" and kind == "itv":
            return {"js": [{"id": "1", "title": "News"}, {"id": "2", "title": "Sports"}]}
        if action == "get_all_channels":
            return {"js": {"data": [
                {"id": "11", "name": "News One", "cmd": "ffmpeg http://portal/live/11.m3u8", "logo": "/logos/11.png", "tv_genre_id": "1", "number": "1"},
                {"id": "12", "name": "Sport One", "cmd": "ffmpeg http://portal/live/12.m3u8", "logo": "/logos/12.png", "tv_genre_id": "2", "number": "2"},
            ], "total_items": 2}}
        if action == "get_categories":
            return {"js": [{"id": "10", "title": "Action"}]}
        if action == "get_ordered_list" and kind == "vod":
            if flat.get("movie_id"):
                if flat.get("season_id") in (None, "0"):
                    return {"js": {"data": [
                        {"id": "1", "name": "Season 1", "series": [1, 2]},
                        {"id": "2", "name": "Season 2", "series": [3]},
                    ], "total_items": 2}}
                return {"js": {"data": [
                    {"id": "1001", "name": "Pilot", "cmd": "ffmpeg http://portal/series/e1.mp4", "season_id": "1", "episode": "1"},
                    {"id": "1002", "name": "Second", "cmd": "ffmpeg http://portal/series/e2.mp4", "season_id": "1", "episode": "2"},
                ], "total_items": 2}}
            if flat.get("is_series") == "1":
                return {"js": {"data": [
                    {"id": "200", "name": "Portal Series", "screenshot_uri": "/p/200.jpg", "is_series": 1},
                ], "total_items": 1}}
            return {"js": {"data": [
                {"id": "101", "name": "Movie A", "screenshot_uri": "/p/101.jpg", "year": "2020",
                 "genres_str": "Action", "rating_imdb": "7.5", "description": "<b>Great</b> movie",
                 "cmd": "ffmpeg http://portal/vod/101.mp4", "time": "01:50:00"},
            ], "total_items": 1}}
        if action == "create_link":
            return {"js": {"cmd": "ffmpeg http://portal/stream/play.m3u8"}}
        return {"js": {}}


def make_handler(portal):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            portal.last_cookie = self.headers.get("Cookie", "")
            payload = portal.response(self.path)
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    return Handler


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print("  ok:", message)


def test_playlist():
    print("[m3u]")
    items = parse_playlist(PLAYLIST, base_url="http://stream.example.com/list.m3u")
    check(len(items) == 8, "parsed 8 entries")
    catalogue = build_catalogue(items)
    check(catalogue["counts"]["live"] == 3, "3 live channels")
    check(catalogue["counts"]["vod"] == 2, "2 movies")
    check(catalogue["counts"]["series"] == 2, "2 series")
    check(catalogue["series"][0]["count"] == 2, "Breaking Bad has 2 episodes")
    check(items[7]["url"].startswith("http://stream.example.com/sub/"), "relative URL resolved")
    check(items[0]["logo"].endswith("news.png"), "tvg-logo kept")
    check(items[3]["ua"] == "SpecialAgent", "EXTVLCOPT user-agent kept")
    movie = [item for item in catalogue["vod"] if "Inception" in item["name"]][0]
    check(movie["year"] == "2010", "movie year detected")

    option_items = parse_playlist(u"""#EXTM3U
#EXTINF:-1 group-title="News",Header Channel
#EXTVLCOPT:http-user-agent=LineAgent
#EXTVLCOPT:http-referrer=http://portal.example/c/
http://stream.example.com/live/header.ts|User-Agent=UrlAgent&Origin=http://portal.example
""")
    option_item = option_items[0]
    check(option_item["ua"] == "LineAgent", "EXTVLCOPT agent on entry")
    check("http-referrer=" in option_item["opts"] and "User-Agent=UrlAgent" in option_item["opts"],
          "EXTVLCOPT and URL options combined")

    headed = stream_url_with_headers(
        option_item["url"], option_item["ua"], option_item["opts"])
    check(headed.count("User-Agent=") == 1, "user agent is not duplicated")
    check("#Referer=http://portal.example/c/" in headed, "referrer header added")
    check("#" in headed and "Origin=http://portal.example" in headed, "origin header kept")
    check(stream_url_with_headers("udp://239.0.0.1:1234", "Agent"),
          "non-HTTP URL is not corrupted")
    check(not stream_url_with_headers("udp://239.0.0.1:1234", "Agent").endswith("#User-Agent=Agent"),
          "headers are only applied to HTTP/RTSP URLs")


def test_store(tmp):
    print("[store]")
    set_language("en")
    conf = os.path.join(tmp, "conf")
    store = Store(config_dir=conf, cache_dir=os.path.join(tmp, "cache"))
    store.set_setting("m3u_file", os.path.join(conf, "m3u.txt"))
    store.set_setting("mac_file", os.path.join(conf, "mac.txt"))
    source = store.new_source("m3u", "My List", "http://example.com/list.m3u")
    check(store.active_id() == source["id"], "first source becomes active")
    check(store.set_active(source["id"]), "set active works")
    store.update_info(source["id"], channels=10, vod=2, series=1)
    store.save()
    reloaded = Store(config_dir=os.path.join(tmp, "conf"), cache_dir=os.path.join(tmp, "cache"))
    check(len(reloaded.sources) == 1, "source persisted")
    check(reloaded.sources[0]["info"]["channels"] == 10, "info persisted")
    m3u_path = os.path.join(conf, "m3u.txt")
    check(os.path.exists(m3u_path), "m3u text file written")
    handle = open(m3u_path, "rb")
    try:
        m3u_text = handle.read().decode("utf-8")
    finally:
        handle.close()
    check("My List|http://example.com/list.m3u" in m3u_text, "m3u text content")
    backend = M3UBackend(reloaded.active_source(), reloaded)
    summary = source_summary(reloaded.active_source(), reloaded)
    check("10" in summary and "channels" in summary, "summary shows counts")
    key = backend.favorite_key({"name": "x", "url": "http://x"})
    check(reloaded.toggle_favorite(source["id"], key) is True, "favorite added")
    check(reloaded.toggle_favorite(source["id"], key) is False, "favorite removed")
    handle = open(m3u_path, "ab")
    try:
        handle.write(b"Second|http://example.com/second.m3u|\n")
    finally:
        handle.close()
    result = reloaded.import_server_files()
    check(result["added"] == 1 and len(reloaded.sources) == 2, "servers imported from text file")


def test_mag(tmp):
    print("[mag]")
    portal = MockPortal()
    portal.last_cookie = ""
    server = HTTPServer(("127.0.0.1", 0), make_handler(portal))
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    port = server.server_address[1]
    url = "http://127.0.0.1:{0}/c/".format(port)
    check(normalize_portal(url) == "http://127.0.0.1:{0}".format(port), "portal root normalized")
    check(normalize_mac("00-1a-79-11-22-33") == "00:1A:79:11:22:33", "MAC normalized")

    client = MagClient(url, "00:1A:79:11:22:33", timeout=5)
    token = client.handshake()
    check(token == "TOKEN-123", "handshake token")
    profile = client.profile_info()
    check(profile.get("name") == "Tester", "profile parsed")
    account = client.account_info()
    check(account.get("end_date") == "2027-01-01 00:00:00", "expiry parsed")
    genres = client.itv_genres()
    check(len(genres) == 2 and genres[0]["name"] == "News", "itv genres")
    channels = client.all_channels()
    check(len(channels) == 2, "all channels")
    vod_cats = client.vod_categories()
    check(vod_cats[0]["name"] == "Action", "vod categories")
    movies, total = client.ordered_list("vod", "10", 1)
    check(total == 1 and movies[0]["name"] == "Movie A", "vod page")
    seasons, _t = client.series_page("*", 1, movie_id="200", season_id=0)
    check(len(seasons) == 2 and seasons[0]["name"] == "Season 1", "seasons")
    episodes, _t = client.series_page("*", 1, movie_id="200", season_id="1")
    check(len(episodes) == 2 and episodes[0]["name"] == "Pilot", "episodes")
    link = client.create_link("itv", "ffmpeg http://portal/live/11.m3u8")
    check(link == "http://portal/stream/play.m3u8", "create_link strips prefix")

    magconf = os.path.join(tmp, "magconf")
    store = Store(config_dir=magconf, cache_dir=os.path.join(tmp, "magcache"))
    store.set_setting("m3u_file", os.path.join(magconf, "m3u.txt"))
    store.set_setting("mac_file", os.path.join(magconf, "mac.txt"))
    source = store.new_source("mag", "Portal", url, "00:1A:79:11:22:33")
    backend = MagBackend(source, store)
    check(backend.refresh(force=True) is True, "backend refresh")
    check(backend.is_ready(), "backend ready")
    cats = backend.live_categories()
    check(len(cats) == 4, "live categories: all, favorites, 2 genres")
    check(len(backend.live_items("g:1")) == 1, "genre filter")
    check(backend.live_items("g:1")[0]["logo"].startswith("http://127.0.0.1"), "logo made absolute")
    vod_items, total = backend.vod_items("all", page=1)
    check(total == 1 and vod_items[0]["description"] == "Great movie", "vod items and html cleaned")
    series_items, _total = backend.series_items("all", page=1)
    check(len(series_items) == 1 and series_items[0]["name"] == "Portal Series", "series items")
    seasons = backend.seasons("200")
    check(len(seasons) == 2, "backend seasons")
    episodes, _t = backend.episodes("200", "1")
    check(len(episodes) == 2, "backend episodes")
    check(backend.resolve(episodes[0]) == "http://portal/stream/play.m3u8", "resolve episode")
    mag_ua, mag_opts = backend.stream_options(episodes[0])
    check("MAG" in mag_ua, "MAG stream user agent")
    check("Cookie=" in mag_opts and "Referer=" in mag_opts, "MAG stream headers kept")
    check(store.get_source(source["id"])["info"]["expires"] == "2027-01-01 00:00:00", "expiry stored")
    mac_path = os.path.join(magconf, "mac.txt")
    check(os.path.exists(mac_path), "mac text file written")
    handle = open(mac_path, "rb")
    try:
        mac_text = handle.read().decode("utf-8")
    finally:
        handle.close()
    check("00:1A:79:11:22:33" in mac_text and "Portal|http" in mac_text, "mac text content")
    server.shutdown()


def test_epg(tmp):
    print("[epg]")
    check(parse_xmltv_time("20261022120000 +0200") ==
          calendar.timegm((2026, 10, 22, 10, 0, 0, 0, 0, 0)), "XMLTV timezone")
    check(parse_xmltv_time("20261022120000 +02:00") ==
          calendar.timegm((2026, 10, 22, 10, 0, 0, 0, 0, 0)), "XMLTV timezone colon")
    check(derive_epg_url("http://portal.test/get.php?username=u&password=p&type=m3u_plus") ==
          "http://portal.test/xmltv.php?username=u&password=p", "Xtream EPG URL derived")

    moment = int(time.time())
    start = moment - 600
    stop = moment + 3000
    next_stop = stop + 3600

    def xmltv_time(value):
        return time.strftime("%Y%m%d%H%M%S +0000", time.gmtime(value))

    served = {}

    class EpgHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/playlist.m3u":
                body = served["playlist"].encode("utf-8")
            elif path == "/epg.xml":
                body = served["epg"].encode("utf-8")
            else:
                body = b"not found"
                self.send_response(404)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(200)
            self.send_header("Content-Type", "audio/x-mpegurl" if path.endswith(".m3u") else "application/xml")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), EpgHandler)
    port = server.server_address[1]
    base = "http://127.0.0.1:{0}".format(port)
    epg_url = base + "/epg.xml"
    served["playlist"] = u"""#EXTM3U url-tvg="{0}"
#EXTINF:-1 tvg-id="news1" tvg-name="News One" group-title="News",News One HD
http://stream.example.com/live/news1.m3u8
#EXTINF:-1 group-title="News",Name Match HD
http://stream.example.com/live/match.m3u8
""".format(epg_url)
    served["epg"] = u"""<?xml version="1.0" encoding="utf-8"?>
<tv>
  <channel id="news1"><display-name>News One</display-name></channel>
  <channel id="sports9"><display-name>Name Match</display-name></channel>
  <programme start="{0}" stop="{1}" channel="news1">
    <title lang="ar">نشرة الأخبار</title>
  </programme>
  <programme start="{1}" stop="{2}" channel="news1">
    <title>News Next</title>
  </programme>
  <programme start="{0}" stop="{1}" channel="sports9">
    <title>Match Live</title>
  </programme>
</tv>
""".format(xmltv_time(start), xmltv_time(stop), xmltv_time(next_stop))

    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    work = tempfile.mkdtemp(prefix="iptvpro-epg-")
    try:
        store = Store(config_dir=work, cache_dir=work)
        store.set_setting("timeout", 5)
        source = store.new_source("m3u", "EPG Test", base + "/playlist.m3u", "", "")
        backend = M3UBackend(source, store)
        backend.refresh(force=True)
        check(backend.epg_urls() == [epg_url], "EPG URL from M3U header")
        check(backend.refresh_epg(force=True), "EPG downloaded")
        items = backend.live_items("all")
        news = [item for item in items if item.get("tvg_id") == "news1"][0]
        match = [item for item in items if "Match" in item.get("name", "")][0]
        current, upcoming = backend.epg_now_next(news, at=moment)
        check(current is not None and current[2] == u"نشرة الأخبار", "current programme")
        check(upcoming is not None and upcoming[2] == "News Next", "next programme")
        current, upcoming = backend.epg_now_next(match, at=moment)
        check(current is not None and current[2] == "Match Live", "EPG name fallback")
        guide = backend.epg_guide()
        check(guide.programmes_for(news), "programmes returned")
        check(os.path.exists(store.epg_file(source.get("id"))), "EPG cache written")

        reloaded = M3UBackend(store.get_source(source.get("id")), store)
        reloaded.refresh()
        current, upcoming = reloaded.epg_now_next(
            [item for item in reloaded.live_items("all") if item.get("tvg_id") == "news1"][0],
            at=moment)
        check(current is not None and current[2] == u"نشرة الأخبار", "EPG cache reloaded")
    finally:
        server.shutdown()
        shutil.rmtree(work, ignore_errors=True)


def main():
    tmp = tempfile.mkdtemp(prefix="iptvpro-test-")
    try:
        test_playlist()
        test_store(tmp)
        test_mag(tmp)
        test_epg(tmp)
        print("\nAll core tests passed.")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
