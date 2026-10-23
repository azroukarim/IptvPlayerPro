# -*- coding: utf-8 -*-
"""
Persistent server data cache on disk (HDD/USB).

Inspired by XPortal's data_cache.py.

The idea: first access to a server loads lists from network and saves them
as JSON files in the chosen data folder (Local or Media/HDD or Media/USB).
Any subsequent access reads from these files, opening instantly without wait.

Automatic refresh happens in two cases:
  1. Cache expiry (TTL_HOURS).
  2. Subscription expiry date change (renewal) — clears that server's cache entirely.
"""

from __future__ import absolute_import

import os
import json
import time
import hashlib
import threading

from .store import Store
from .util import now, safe_int, to_text

# Cache TTL in hours (0 = disabled)
TTL_HOURS = 12

_settings_ts = 0
_enabled = True
_lock = threading.RLock()


def enabled():
    """Read cache enable setting from global config (cached for 60s)."""
    global _settings_ts, _enabled
    with _lock:
        cur = time.time()
        if cur - _settings_ts > 60:
            try:
                store = Store()
                cfg = store.settings or {}
                _enabled = bool(cfg.get('cache_server_data', True))
            except Exception:
                _enabled = True
            _settings_ts = cur
    return _enabled


_root_ready = None


def root():
    """Return the cache root directory (created once)."""
    global _root_ready
    with _lock:
        if _root_ready:
            return _root_ready
        # Use the same data folder as config.json (persistent)
        try:
            store = Store()
            path = os.path.join(store.config_dir, 'datacache')
        except Exception:
            # Fallback: first writable candidate
            for base in ('/media/hdd/IPTVPlayerPro', '/media/usb/IPTVPlayerPro',
                         '/etc/enigma2/IPTVPlayerPro', '/tmp/iptvplayerpro'):
                try:
                    path = os.path.join(base, 'datacache')
                    if not os.path.isdir(path):
                        os.makedirs(path)
                    _root_ready = path
                    return _root_ready
                except Exception:
                    continue
            path = '/tmp/iptvplayerpro/datacache'
            os.makedirs(path)
        try:
            if not os.path.isdir(path):
                os.makedirs(path)
            _root_ready = path
        except Exception as e:
            print('[IPTVPlayerPro] data cache mkdir error: %s' % e)
        return _root_ready


def namespace(*parts):
    """Stable server identifier (e.g. host + user) to isolate each server's cache."""
    raw = '|'.join([str(p or '') for p in parts])
    return hashlib.md5(raw.encode('utf-8')).hexdigest()[:12]


def _path(ns, key):
    name = '%s_%s.json' % (ns, hashlib.md5(str(key).encode('utf-8')).hexdigest())
    return os.path.join(root(), name)


def load(ns, key, ttl_hours=None):
    """Return cached data if present and not expired, else None."""
    if not enabled():
        return None
    path = _path(ns, key)
    try:
        try:
            handle = open(path, 'r')
        except (IOError, OSError):
            return None  # missing -> cheapest check
        with handle as f:
            ttl = (TTL_HOURS if ttl_hours is None else ttl_hours) * 3600
            if ttl > 0:
                try:
                    mtime = os.fstat(f.fileno()).st_mtime
                except Exception:
                    mtime = os.path.getmtime(path)
                if (time.time() - mtime) > ttl:
                    return None
            blob = json.load(f)
        return blob.get('data')
    except Exception as e:
        print('[IPTVPlayerPro] data cache read error: %s' % e)
        try:
            os.remove(path)
        except Exception:
            pass
        return None


def save(ns, key, data):
    """Write data atomically to cache."""
    if not enabled() or data is None:
        return
    path = _path(ns, key)
    try:
        folder = os.path.dirname(path)
        if folder and not os.path.isdir(folder):
            os.makedirs(folder)
        tmp = '%s.%d.part' % (path, threading.current_thread().ident or os.getpid())
        with open(tmp, 'w') as f:
            json.dump({'ts': int(now()), 'data': data}, f)
        # On Windows, os.rename fails if target exists. Remove first.
        try:
            os.remove(path)
        except Exception:
            pass
        os.rename(tmp, path)
    except Exception as e:
        print('[IPTVPlayerPro] data cache write error: %s' % e)


def clear(ns=None):
    """Clear cache for a specific server namespace, or all if ns is None."""
    removed = 0
    try:
        base = root()
        for name in os.listdir(base):
            if not name.endswith('.json'):
                continue
            if ns and not name.startswith('%s_' % ns):
                continue
            try:
                os.remove(os.path.join(base, name))
                removed += 1
            except Exception:
                pass
    except Exception as e:
        print('[IPTVPlayerPro] data cache clear error: %s' % e)
    print('[IPTVPlayerPro] data cache cleared: %d file(s)' % removed)
    return removed


def check_expiry(ns, exp_date):
    """
    Compare subscription expiry date with stored one: if changed (renewal or
    switch), clear this server's cache so it reloads automatically.
    """
    if not exp_date:
        return False
    path = os.path.join(root(), 'exp_%s.txt' % ns)
    old = None
    try:
        if os.path.exists(path):
            with open(path, 'r') as f:
                old = f.read().strip()
    except Exception:
        old = None

    new = str(exp_date).strip()
    _UNKNOWN = ('unlimited / unknown', 'unknown', 'unlimited', 'n/a', '-', '')
    if new.lower() in _UNKNOWN:
        return False  # couldn't determine date: don't clear anything

    changed = bool(old) and old.lower() not in _UNKNOWN and old != new
    if changed:
        print('[IPTVPlayerPro] Subscription changed (%s -> %s), refreshing cache' % (old, exp_date))
        clear(ns)

    try:
        with open(path, 'w') as f:
            f.write(new)
    except Exception:
        pass
    return changed