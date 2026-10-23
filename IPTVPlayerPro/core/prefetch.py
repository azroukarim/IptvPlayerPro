# -*- coding: utf-8 -*-
"""Background preparation of a complete IPTV source catalogue.

Activating a source should make Live TV, Movies and Series immediately
available.  M3U playlists are already downloaded as one file; MAG portals need
one request per category and page.  This module runs that work in a daemon
thread and stores the result in the normal per-source cache.

The module is deliberately free of tabs and screen code.  The UI and the web
interface only read the small status helpers below.
"""

from __future__ import absolute_import

import threading
import time

from .backends import create_backend
from .i18n import _
from .util import (PrefetchCancelled, now, safe_int, to_text)

LOG_PATH = "/tmp/iptvplayerpro-prefetch.log"

_LOCK = threading.RLock()
_JOBS = {}


def _log(message):
    try:
        line = u"{0} {1}\n".format(time.strftime("%Y-%m-%d %H:%M:%S"),
                                   to_text(message))
        handle = open(LOG_PATH, "ab")
        try:
            handle.write(line.encode("utf-8"))
        finally:
            handle.close()
    except Exception:
        pass


def _fingerprint(source):
    return (to_text(source.get("type")), to_text(source.get("url")),
            to_text(source.get("mac")))


def enabled(store):
    try:
        return bool(store.settings.get("prefetch_enabled", True))
    except Exception:
        return True


def running(source_id):
    with _LOCK:
        job = _JOBS.get(to_text(source_id))
        return bool(job and not job["done"].is_set())


def status_text(source_id):
    with _LOCK:
        job = _JOBS.get(to_text(source_id))
        return to_text(job.get("text")) if job else u""


def wait(source_id, timeout=1800):
    """Wait until preparation ends, following a queued replacement job."""
    source_id = to_text(source_id)
    deadline = time.time() + max(1, safe_int(timeout, 1800))
    while True:
        with _LOCK:
            job = _JOBS.get(source_id)
        if job is None:
            return {"state": "idle", "error": u""}
        remaining = deadline - time.time()
        if remaining <= 0:
            return {"state": "timeout", "error": u""}
        job["done"].wait(remaining)
        with _LOCK:
            if _JOBS.get(source_id) is not job:
                continue
            return {"state": job.get("state") or "done",
                    "error": to_text(job.get("error"))}


def _report(job, text):
    if job["cancel"].is_set():
        raise PrefetchCancelled(u"cancelled")
    job["text"] = to_text(text)


def _run(store, source_id, force, job):
    state = "error"
    error = u""
    try:
        source = store.get_source(source_id)
        if source is None:
            state = "cancelled"
            return
        backend = create_backend(source, store)
        if backend is None:
            raise RuntimeError(u"Unsupported source")
        report = lambda text: _report(job, text)
        backend.refresh(force=force, progress=report)
        counts = backend.prefetch(progress=report, force=False) or {}
        if job["cancel"].is_set():
            raise PrefetchCancelled(u"cancelled")
        current = store.get_source(source_id)
        if current is None:
            store.clear_cache(source_id)
            state = "cancelled"
            return
        if _fingerprint(current) != job["fingerprint"]:
            # The URL/MAC changed while the worker was busy.  Do not leave a
            # cache belonging to the previous portal behind.
            store.clear_cache(source_id)
            state = "cancelled"
            return
        values = {
            "prefetch": "done",
            "prefetch_text": u"",
            "prefetch_error": u"",
            "prefetched": now(),
        }
        if "live" in counts:
            values["channels"] = safe_int(counts.get("live"))
        for key in ("vod", "series", "episodes"):
            if key in counts:
                values[key] = safe_int(counts.get(key))
        store.update_info(source_id, **values)
        state = "done"
    except PrefetchCancelled:
        state = "cancelled"
        current = store.get_source(source_id)
        if current is None or _fingerprint(current) != job["fingerprint"]:
            store.clear_cache(source_id)
    except Exception as exc:  # noqa: BLE001 - worker must never crash the UI
        if job["cancel"].is_set():
            state = "cancelled"
        else:
            state = "error"
            error = to_text(exc) or u"Preparation failed"
            _log(u"{0}: {1}".format(source_id, error))
            try:
                store.update_info(source_id, prefetch="error",
                                  prefetch_text=u"", prefetch_error=error)
            except Exception:
                pass
    finally:
        job["state"] = state
        job["error"] = error
        pending = None
        with _LOCK:
            if _JOBS.get(source_id) is job:
                _JOBS.pop(source_id, None)
                pending = job.get("pending")
        if pending is not None:
            # A refresh or a source edit arrived while this job was running.
            # Start the replacement before releasing waiters so they follow
            # the new job instead of briefly seeing an empty slot.
            try:
                start(store, source_id, force=bool(pending))
            except Exception as exc:
                _log(u"{0}: could not queue replacement: {1}".format(
                    source_id, to_text(exc)))
        job["done"].set()


def start(store, source_id, force=False):
    """Start preparing *source_id* in the background.

    Returns True when a job was started (or queued behind a running one).
    """
    source_id = to_text(source_id)
    if not source_id or not enabled(store):
        return False
    source = store.get_source(source_id)
    if not source or not source.get("url"):
        return False
    fingerprint = _fingerprint(source)
    with _LOCK:
        existing = _JOBS.get(source_id)
        if existing is not None and not existing["done"].is_set():
            if force or existing["fingerprint"] != fingerprint:
                existing["pending"] = True
                existing["cancel"].set()
                return True
            return False
        if existing is not None:
            _JOBS.pop(source_id, None)
        job = {
            "source_id": source_id,
            "fingerprint": fingerprint,
            "done": threading.Event(),
            "cancel": threading.Event(),
            "text": _("Preparing ..."),
            "state": "running",
            "error": u"",
            "pending": None,
            "started": now(),
            "thread": None,
        }
        _JOBS[source_id] = job
    try:
        store.update_info(source_id, prefetch="running",
                          prefetch_text=_("Preparing ..."),
                          prefetch_error=u"", prefetch_started=now())
    except Exception:
        pass
    thread = threading.Thread(target=_run, args=(store, source_id, bool(force), job))
    thread.setDaemon(True)
    job["thread"] = thread
    try:
        thread.start()
    except Exception as exc:
        _log(u"{0}: could not start worker: {1}".format(source_id, to_text(exc)))
        with _LOCK:
            if _JOBS.get(source_id) is job:
                _JOBS.pop(source_id, None)
        job["done"].set()
        try:
            store.update_info(source_id, prefetch="error",
                              prefetch_text=u"", prefetch_error=to_text(exc))
        except Exception:
            pass
        return False
    return True


def cancel(source_id):
    with _LOCK:
        job = _JOBS.get(to_text(source_id))
        if job:
            job["cancel"].set()


def reconcile(store):
    """Clear a stale ``running`` marker left by a previous plugin process."""
    with _LOCK:
        active = set(_JOBS.keys())
    try:
        sources = list(store.sources)
    except Exception:
        return
    for source in sources:
        source_id = to_text(source.get("id"))
        info = source.get("info") or {}
        if info.get("prefetch") == "running" and source_id not in active:
            try:
                store.update_info(source_id, prefetch="idle",
                                  prefetch_text=u"", prefetch_error=u"")
            except Exception:
                pass
