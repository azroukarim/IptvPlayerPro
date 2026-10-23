# -*- coding: utf-8 -*-
"""
Daily background server data refresh.

Inspired by XPortal's refresher.py.

The idea: at a user-chosen hour the last-used server's sections are re-fetched
and their snapshot saved anew, in a separate thread with no impact on the UI.
The plugin always opens on fresh data without waiting.

How the timer works:
A single timer ticks every minute and asks: has the appointed moment for today
passed and not yet executed? We chose this over computing the time until the
appointment because the receiver's clock is synced from the network after boot
and may jump hours at once, so a pre-computed delay would be lost.
The tick is cheap: comparing two numbers.

Last run timestamp is stored in settings, so the refresh doesn't repeat on the
same day if the device is rebooted, and doesn't get lost if the device was off
at the appointed time — it runs on the first tick after startup.
"""

from __future__ import absolute_import

import time
import threading

from .store import Store
from .util import now, to_text
from . import data_cache

CHECK_INTERVAL_MS = 60 * 1000       # Tick every minute
DEFAULT_TIME = '04:00'
STEP_MINUTES = 30                   # Step when changing time in settings

_timer = None
_owner = None                       # Live reference prevents timer GC
_running = False                    # Prevents overlapping refreshes


# -------------------------------------------------------------------- settings
def _config():
    try:
        store = Store()
        return store.settings or {}
    except Exception:
        return {}


def is_enabled(cfg=None):
    cfg = _config() if cfg is None else cfg
    return bool(cfg.get('auto_refresh', False))


def parse_time(text):
    """'HH:MM' -> (hour, minute). Any bad text returns default."""
    try:
        hour, minute = str(text or '').split(':')
        hour, minute = int(hour), int(minute)
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute
    except Exception:
        pass
    return parse_time(DEFAULT_TIME) if text != DEFAULT_TIME else (4, 0)


def normalize(text):
    """Return time as HH:MM normalised; bad text returns default."""
    hour, minute = parse_time(text)
    return '%02d:%02d' % (hour, minute)


def refresh_time(cfg=None):
    cfg = _config() if cfg is None else cfg
    return parse_time(cfg.get('refresh_time', DEFAULT_TIME))


def shift_time(text, direction):
    """Advance or delay time by fixed step, wrapping at midnight."""
    hour, minute = parse_time(text)
    total = (hour * 60 + minute + direction * STEP_MINUTES) % (24 * 60)
    return '%02d:%02d' % (total // 60, total % 60)


def _last_run(cfg):
    try:
        return int(cfg.get('last_refresh_ts', 0) or 0)
    except Exception:
        return 0


def _mark_run(when=None):
    try:
        store = Store()
        cfg = store.settings or {}
        cfg['last_refresh_ts'] = int(when or now())
        store.set_settings(cfg)
    except Exception as exc:
        print('[IPTVPlayerPro] refresh stamp error: %s' % exc)


# ------------------------------------------------------------------ appointment
def due_at(now_ts, last_ts, hour, minute):
    """Has the appointment arrived and not yet run?

    Pure function, separated for testability: takes numbers, returns decision.
    """
    if now_ts < 0:
        return False
    # Build today's appointment timestamp
    lt = time.localtime(now_ts)
    target = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, hour, minute, 0,
                          lt.tm_wday, lt.tm_yday, lt.tm_isdst))
    return target <= now_ts and last_ts < target


# ---------------------------------------------------------------- worker logic
def _refresh_worker(source_id, progress=None):
    """Background worker: refreshes server data and updates caches."""
    try:
        store = Store()
        source = store.get_source(source_id)
        if not source:
            return
        from .backends import create_backend
        backend = create_backend(source, store)
        if backend is None:
            return

        # Use section-aware refresh (only categories for VOD/Series)
        # This is fast and updates the cache files
        def report(text, percent=None):
            if progress:
                progress(text, percent)

        # Refresh all sections (live + categories)
        backend.refresh(force=True, progress=report)

        # Mark refresh as done
        _mark_run()
        print('[IPTVPlayerPro] Background refresh completed for %s' % source_id)

    except Exception as exc:  # noqa: BLE001
        print('[IPTVPlayerPro] background refresh error: %s' % exc)


# --------------------------------------------------------------- timer control
def _tick():
    """Timer callback: check if refresh is due, start worker if so."""
    global _running
    if _running:
        return
    if not is_enabled():
        return
    try:
        store = Store()
        source = store.active_source()
        if not source:
            return
        source_id = to_text(source.get('id'))
        if not source_id:
            return
        cfg = store.settings or {}
        last_ts = _last_run(cfg)
        hour, minute = refresh_time(cfg)
        if due_at(now(), last_ts, hour, minute):
            _running = True
            print('[IPTVPlayerPro] Starting background refresh for %s' % source_id)

            def report(text, percent=None):
                pass  # Silent background

            thread = threading.Thread(target=_refresh_worker, args=(source_id, report))
            thread.setDaemon(True)
            thread.start()
    except Exception as exc:
        print('[IPTVPlayerPro] refresh tick error: %s' % exc)
    finally:
        _running = False


def start_timer():
    """Start the minute timer (called once at plugin init)."""
    global _timer, _owner
    if _timer is not None:
        return
    try:
        from enigma import eTimer
        _timer = eTimer()
        _timer.callback.append(_tick)
        _timer.start(CHECK_INTERVAL_MS, True)
        _owner = _timer  # keep alive
        print('[IPTVPlayerPro] Refresher timer started (interval %d ms)' % CHECK_INTERVAL_MS)
    except Exception as exc:
        print('[IPTVPlayerPro] failed to start refresher timer: %s' % exc)


def stop_timer():
    """Stop the timer (called on plugin shutdown)."""
    global _timer, _owner
    if _timer is not None:
        try:
            _timer.stop()
        except Exception:
            pass
        _timer = None
        _owner = None
        print('[IPTVPlayerPro] Refresher timer stopped')