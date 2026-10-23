# -*- coding: utf-8 -*-
"""
Generate Enigma2 userbouquet files from server sections.

Inspired by XPortal's bouquets.py.

Layout:
- One parent bouquet per server (folder) appears in the main bouquet list.
- Inside it, one child bouquet per section (Live, VOD, Series).

Why two different prefixes:
Enigma2 auto-picks any file named ``userbouquet.*.tv`` in ``/etc/enigma2`` and
adds it to the top-level bouquet list on service reload — no matter what we
write in ``bouquets.tv``. If we named section bouquets with the same prefix
they would appear twice: once inside the parent folder and once outside.
Therefore section bouquets use prefix ``xportalsub.`` so the auto-loader
ignores them; they are only reachable through the parent folder which points
to them.

Service reference format:
    #SERVICE 4097:0:1:0:0:0:0:0:0:0:<url>:<name>

Colons inside the URL must be encoded as ``%3a`` otherwise enigma2 treats
them as field separators and the reference breaks. This is exactly what the
plugin does when playing from inside it, so bouquet entries work identically.

Stalker warning:
Stalker URLs are temporary (``play_token``) and expire. Their bouquets stop
working and need regeneration. Xtream and M3U URLs are permanent.
"""

from __future__ import absolute_import

import os
import io
import re
import struct
import hashlib

from .util import to_text, safe_int

BOUQUET_DIR = '/etc/enigma2'
INDEX_FILE = 'bouquets.tv'

# One parent bouquet per server; section bouquets live inside it.
NESTED_FOLDER = True

# Parent bouquet prefix: MUST stay userbouquet. so enigma2 sees it.
PARENT_PREFIX = 'userbouquet.iptvpro_'

# Child bouquet prefix inside the folder: MUST NOT be userbouquet.
CHILD_PREFIX_NESTED = 'iptvsub.iptvpro_'

# Flat mode fallback (if NESTED_FOLDER = False).
CHILD_PREFIX_FLAT = PARENT_PREFIX

# Old prefix kept for compatibility with external callers.
PREFIX = PARENT_PREFIX

# All prefixes we may have written in any version — for cleanup/recognition.
ALL_PREFIXES = (PARENT_PREFIX, CHILD_PREFIX_NESTED)

# Folder label prefix as shown in channel list: IPTV_
FOLDER_PREFIX = 'IPTV_'

# Section type tags shown in bouquet names: LIVE_FR SPORT
MODE_TAGS = {'live': 'LIVE', 'catchup': 'LIVE', 'vod': 'VOD', 'series': 'SERIES'}

# Section order inside folder, also used in filename.
MODE_ORDER = ('live', 'vod', 'series')

_OUR_LINE_RE = re.compile(
    r'"((?:%s)[^"]*)"' % '|'.join(re.escape(p) for p in ALL_PREFIXES))

_SLUG_RE = re.compile(r'[^a-z0-9]+')


def child_prefix():
    return CHILD_PREFIX_NESTED if NESTED_FOLDER else CHILD_PREFIX_FLAT


def slug(text):
    """Safe filename: lowercase alnum and underscores only."""
    value = _SLUG_RE.sub('_', str(text or '').strip().lower())
    return value.strip('_')[:40] or 'x'


def _index_path():
    return os.path.join(BOUQUET_DIR, INDEX_FILE)


def _fingerprint(text):
    """Short fingerprint of the original name.

    Necessary because slug drops everything non-latin alnum: two different
    Arabic names yield the same slug, likewise "FR| SPORT" and "FR SPORT".
    Fingerprint guarantees a unique file per section, stable across
    regenerations so the same file is overwritten instead of accumulating.
    """
    return hashlib.md5(to_text(text).encode('utf-8')).hexdigest()[:8]


def _service_ref(url, name, service_type=4097):
    """Build an enigma2 service reference line."""
    # Escape colons in URL
    safe_url = to_text(url).replace(':', '%3a')
    safe_name = to_text(name).replace(':', ';')
    return '#SERVICE %d:0:1:0:0:0:0:0:0:0:%s:%s\n' % (service_type, safe_url, safe_name)


def _write_bouquet(path, lines):
    """Atomically write a bouquet file."""
    try:
        folder = os.path.dirname(path)
        if folder and not os.path.isdir(folder):
            os.makedirs(folder)
        tmp = path + '.tmp'
        with io.open(tmp, 'w', encoding='utf-8') as f:
            f.write('#NAME %s\n' % os.path.basename(path))
            f.writelines(lines)
        os.rename(tmp, path)
        return True
    except Exception as e:
        print('[IPTVPlayerPro] bouquet write error: %s' % e)
        return False


def _read_bouquet(path):
    """Read bouquet lines (skip header)."""
    try:
        with io.open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        # Skip #NAME line
        return [l for l in lines if not l.startswith('#NAME')]
    except Exception:
        return []


def generate_for_source(store, source_id, service_type=4097):
    """
    Generate parent + child bouquets for a given source.
    Returns (parent_path, [child_paths]) or (None, []) on failure.
    """
    source = store.get_source(source_id)
    if not source:
        return None, []

    source_type = to_text(source.get('type'))
    source_name = to_text(source.get('name')) or source_id
    url = to_text(source.get('url'))
    mac = to_text(source.get('mac'))

    # Namespace for backend
    from .backends import create_backend
    backend = create_backend(source, store)
    if backend is None:
        return None, []

    # Build parent bouquet name
    parent_slug = slug(source_name)
    parent_fname = '%s%s.tv' % (PARENT_PREFIX, parent_slug)
    parent_path = os.path.join(BOUQUET_DIR, parent_fname)

    parent_lines = []
    child_paths = []

    try:
        # Ensure backend has categories loaded
        if hasattr(backend, 'prepare_section'):
            backend.prepare_section('live')
            backend.prepare_section('movies')
            backend.prepare_section('series')
    except Exception:
        pass

    # Iterate sections in order
    for mode in MODE_ORDER:
        if mode == 'live':
            categories = backend.live_categories() if hasattr(backend, 'live_categories') else []
            mode_tag = MODE_TAGS.get('live', 'LIVE')
        elif mode == 'vod':
            categories = backend.vod_categories() if hasattr(backend, 'vod_categories') else []
            mode_tag = MODE_TAGS.get('vod', 'VOD')
        else:
            categories = backend.series_categories() if hasattr(backend, 'series_categories') else []
            mode_tag = MODE_TAGS.get('series', 'SERIES')

        if not categories:
            continue

        # Child bouquet for this mode
        child_fname = '%s%s_%s.tv' % (child_prefix(), parent_slug, mode)
        child_path = os.path.join(BOUQUET_DIR, child_fname)
        child_paths.append(child_path)

        child_lines = []
        for cat in categories:
            cat_id = to_text(cat.get('id'))
            cat_name = to_text(cat.get('name'))
            if not cat_id or not cat_name:
                continue
            # Build URL to open this category in the plugin
            # We use a special scheme that the plugin can handle
            cat_url = 'iptvpro://%s/category/%s/%s' % (source_id, mode, cat_id)
            child_lines.append(_service_ref(cat_url, '%s %s' % (mode_tag, cat_name), service_type))

        if child_lines:
            _write_bouquet(child_path, child_lines)
            # Parent points to child bouquet
            parent_lines.append('#SERVICE 1:7:1:0:0:0:0:0:0:0: %s\n' % child_path)

    if parent_lines:
        _write_bouquet(parent_path, parent_lines)
        return parent_path, child_paths

    return None, []


def regenerate_all(store, service_type=4097):
    """Regenerate bouquets for all configured sources."""
    results = []
    for source in store.sources:
        sid = to_text(source.get('id'))
        if sid:
            p, c = generate_for_source(store, sid, service_type)
            results.append((sid, p, c))
    return results


def cleanup_obsolete():
    """Remove bouquet files created by old versions of this plugin."""
    try:
        for name in os.listdir(BOUQUET_DIR):
            if not name.endswith('.tv'):
                continue
            for pref in ALL_PREFIXES:
                if name.startswith(pref):
                    try:
                        os.remove(os.path.join(BOUQUET_DIR, name))
                    except Exception:
                        pass
    except Exception:
        pass


def update_bouquets_index(parent_paths):
    """
    Ensure bouquets.tv contains entries for all parent bouquets.
    Adds missing ones, preserves others.
    """
    index_path = _index_path()
    existing = []
    try:
        with io.open(index_path, 'r', encoding='utf-8') as f:
            existing = f.readlines()
    except Exception:
        pass

    # Keep non-iptvpro lines
    kept = [l for l in existing if 'iptvpro_' not in l and 'iptvsub.iptvpro_' not in l]

    # Add our parent bouquets
    for p in parent_paths:
        fname = os.path.basename(p)
        line = '#SERVICE 1:7:1:0:0:0:0:0:0:0: %s\n' % fname
        if line not in kept:
            kept.append(line)

    # Write back
    try:
        tmp = index_path + '.tmp'
        with io.open(tmp, 'w', encoding='utf-8') as f:
            f.writelines(kept)
        os.rename(tmp, index_path)
    except Exception as e:
        print('[IPTVPlayerPro] bouquets.tv update error: %s' % e)