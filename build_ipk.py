# -*- coding: utf-8 -*-
"""Build the installable Enigma2 .ipk package.

Usage:
    python build_ipk.py

The archive layout is the one understood by opkg on every Enigma2 image:

    debian-binary
    control.tar.gz
    data.tar.gz

Only the plugin sources and the pre-generated PNG assets are packaged.
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

PACKAGE = "enigma2-plugin-extensions-iptvplayerpro"
PLUGIN_DIR = "IPTVPlayerPro"
INSTALL_ROOT = "usr/lib/enigma2/python/Plugins/Extensions"
MAINTAINER = "azroukarim"
HOMEPAGE = "https://github.com/azroukarim/IptvPlayerPro"


def plugin_version():
    path = os.path.join(SRC, "core", "store.py")
    handle = io.open(path, encoding="utf-8")
    try:
        text = handle.read()
    finally:
        handle.close()
    match = re.search(r'^VERSION\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit("VERSION not found in core/store.py")
    return match.group(1)


def iter_files():
    """Yield (relative posix path, absolute path) for the plugin payload."""
    for base, dirs, files in os.walk(SRC):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for name in sorted(files):
            if name.endswith((".pyc", ".pyo", ".tmp")):
                continue
            absolute = os.path.join(base, name)
            relative = os.path.relpath(absolute, SRC).replace(os.sep, "/")
            yield relative, absolute


def add_bytes(archive, name, data, mode=0o644, mtime=None):
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = mode
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    info.mtime = mtime or int(time.time())
    archive.addfile(info, io.BytesIO(data))


def add_dir(archive, name, mtime):
    info = tarfile.TarInfo(name)
    info.type = tarfile.DIRTYPE
    info.mode = 0o755
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    info.mtime = mtime
    archive.addfile(info)


def make_control_tar(version, mtime):
    control = u"""Package: {package}
Version: {version}
Description: IPTV Player Pro - M3U and MAG/Stalker player for Enigma2
Section: extra
Priority: optional
Maintainer: {maintainer}
Architecture: all
Depends: enigma2
Homepage: {homepage}
""".format(package=PACKAGE, version=version, maintainer=MAINTAINER, homepage=HOMEPAGE)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz", compresslevel=9) as archive:
        add_bytes(archive, "control", control.encode("utf-8"), 0o644, mtime)
    return buffer.getvalue()


def make_data_tar(mtime):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz", compresslevel=9) as archive:
        current = "./" + INSTALL_ROOT
        add_dir(archive, current, mtime)
        for part in PLUGIN_DIR.split("/"):
            current += "/" + part
            add_dir(archive, current, mtime)
        for folder in ("core", "ui", "web", "images"):
            add_dir(archive, current + "/" + folder, mtime)
        for relative, absolute in iter_files():
            handle = io.open(absolute, "rb")
            try:
                data = handle.read()
            finally:
                handle.close()
            add_bytes(archive, current + "/" + relative, data, 0o644, mtime)
    return buffer.getvalue()


def write_ar(path, members):
    """Write a deterministic ar archive the way dpkg/opkg expects it."""
    with io.open(path, "wb") as handle:
        handle.write(b"!<arch>\n")
        for name, data in members:
            header = u"{0:<16}{1:<12}{2:<6}{3:<6}{4:<8}{5:<10}`\n".format(
                name, int(time.time()), 0, 0, "100644", len(data),
            )
            handle.write(header.encode("ascii"))
            handle.write(data)
            if len(data) % 2:
                handle.write(b"\n")


def main():
    version = plugin_version()
    if not os.path.isdir(SRC):
        raise SystemExit("Missing source directory: " + SRC)
    if not os.path.isdir(DIST):
        os.makedirs(DIST)

    mtime = int(time.time())
    control_tar = make_control_tar(version, mtime)
    data_tar = make_data_tar(mtime)

    filename = "{0}_{1}_all.ipk".format(PACKAGE, version)
    target = os.path.join(DIST, filename)
    write_ar(target, [
        ("debian-binary", b"2.0\n"),
        ("control.tar.gz", control_tar),
        ("data.tar.gz", data_tar),
    ])

    size = os.path.getsize(target)
    print("Built:", target)
    print("Size : {0:.1f} KiB".format(size / 1024.0))
    print("Files: {0}".format(sum(1 for _ in iter_files())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
