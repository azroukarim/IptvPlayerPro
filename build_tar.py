# -*- coding: utf-8 -*-
"""Build the installable Enigma2 .tar.gz package for IPTV Player Pro.

Usage:
    python build_tar.py
"""

from __future__ import print_function

import io
import os
import re
import sys
import tarfile
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src", "IPTVPlayerPro")
DIST = os.path.join(ROOT, "dist")
INSTALL_PATH = "usr/lib/enigma2/python/Plugins/Extensions/IPTVPlayerPro"


def plugin_version():
    path = os.path.join(SRC, "core", "store.py")
    with io.open(path, encoding="utf-8") as handle:
        text = handle.read()
    match = re.search(r'^VERSION\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit("VERSION not found in core/store.py")
    return match.group(1)


def iter_files():
    for base, dirs, files in os.walk(SRC):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for name in sorted(files):
            if name.endswith((".pyc", ".pyo", ".tmp")):
                continue
            absolute = os.path.join(base, name)
            relative = os.path.relpath(absolute, SRC).replace(os.sep, "/")
            yield relative, absolute


def build_tar(target_path, version, prefix="usr/lib/enigma2/python/Plugins/Extensions/IPTVPlayerPro"):
    mtime = int(time.time())
    with tarfile.open(target_path, mode="w:gz", compresslevel=9) as archive:
        # Create directory hierarchy
        parts = prefix.split("/")
        curr = ""
        for p in parts:
            curr = curr + "/" + p if curr else p
            info = tarfile.TarInfo(curr)
            info.type = tarfile.DIRTYPE
            info.mode = 0o755
            info.uid = 0
            info.gid = 0
            info.uname = "root"
            info.gname = "root"
            info.mtime = mtime
            archive.addfile(info)

        # Add files
        for relative, absolute in iter_files():
            archive_name = "{0}/{1}".format(prefix, relative)
            with io.open(absolute, "rb") as handle:
                data = handle.read()
            info = tarfile.TarInfo(archive_name)
            info.size = len(data)
            info.mode = 0o644
            info.uid = 0
            info.gid = 0
            info.uname = "root"
            info.gname = "root"
            info.mtime = mtime
            archive.addfile(info, io.BytesIO(data))


def main():
    if not os.path.isdir(SRC):
        raise SystemExit("Missing source directory: " + SRC)
    if not os.path.isdir(DIST):
        os.makedirs(DIST)

    version = plugin_version()

    # 1. Main Enigma2 distribution archive: extracts directly to /usr/lib/enigma2/python/Plugins/Extensions/IPTVPlayerPro
    target_main = os.path.join(DIST, "IPTVPlayerPro.tar.gz")
    target_versioned = os.path.join(DIST, "IPTVPlayerPro_{0}.tar.gz".format(version))

    build_tar(target_main, version, prefix=INSTALL_PATH)
    build_tar(target_versioned, version, prefix=INSTALL_PATH)

    size = os.path.getsize(target_main)
    print("Built: {0} ({1:.1f} KiB)".format(target_main, size / 1024.0))
    print("Built: {0}".format(target_versioned))
    return 0


if __name__ == "__main__":
    sys.exit(main())
