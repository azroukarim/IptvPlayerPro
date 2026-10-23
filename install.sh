#!/bin/sh
# ============================================================
#  IPTV Player Pro - Enigma2 installer
#  https://github.com/azroukarim/IptvPlayerPro
# ------------------------------------------------------------
#  Usage on the receiver (Telnet/SSH):
#    wget -q --no-check-certificate -O /tmp/iptvpro.sh \
#      https://raw.githubusercontent.com/azroukarim/IptvPlayerPro/main/install.sh
#    sh /tmp/iptvpro.sh
#
#  Options:
#    --no-restart     install without restarting Enigma2
#    --tar FILE       install a local IPTVPlayerPro.tar.gz
#    --help           show this help
# ============================================================

VERSION="1.5.5"
TAR_NAME="IPTVPlayerPro.tar.gz"
BASE_RAW="https://raw.githubusercontent.com/azroukarim/IptvPlayerPro/main/dist"
BASE_GH="https://github.com/azroukarim/IptvPlayerPro/raw/main/dist"
TMP="/tmp/${TAR_NAME}"
TARGET_DIR="/usr/lib/enigma2/python/Plugins/Extensions/IPTVPlayerPro"

NO_RESTART=0
LOCAL_TAR=""

say() {
    printf '%s\n' "[IPTV Player Pro] $*"
}

die() {
    printf '%s\n' "[IPTV Player Pro] ERROR: $*" >&2
    exit 1
}

usage() {
    printf '%s\n' "IPTV Player Pro installer ${VERSION}"
    printf '%s\n' "  --no-restart    install without restarting Enigma2"
    printf '%s\n' "  --tar FILE      install a local ${TAR_NAME}"
    printf '%s\n' "  --help          show this help"
}

download() {
    if command -v wget >/dev/null 2>&1; then
        wget -q --no-check-certificate -O "$TMP" "$1" >/dev/null 2>&1 && return 0
        wget -q -O "$TMP" "$1" >/dev/null 2>&1 && return 0
    fi
    if command -v curl >/dev/null 2>&1; then
        curl -k -L -s -o "$TMP" "$1" >/dev/null 2>&1 && return 0
    fi
    return 1
}

while [ $# -gt 0 ]; do
    case "$1" in
        --no-restart)
            NO_RESTART=1
            ;;
        --tar|--ipk)
            shift
            [ $# -gt 0 ] || die "--tar needs a file path"
            LOCAL_TAR="$1"
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "unknown option: $1 (try --help)"
            ;;
    esac
    shift
done

# The installer must run on the receiver, not on a Windows/Linux PC.
[ -d /usr/lib/enigma2 ] || die "this script must run on the Enigma2 receiver (Telnet/SSH), not on your PC"

# If the script was copied next to the package, use that local file.
SELF_DIR="."
case "$0" in
    */*) SELF_DIR="${0%/*}" ;;
esac
if [ -z "$LOCAL_TAR" ] && [ -f "$SELF_DIR/$TAR_NAME" ]; then
    LOCAL_TAR="$SELF_DIR/$TAR_NAME"
fi

if [ -n "$LOCAL_TAR" ]; then
    [ -f "$LOCAL_TAR" ] || die "file not found: $LOCAL_TAR"
    TMP="$LOCAL_TAR"
    say "Using local package: $TMP"
else
    say "Downloading ${TAR_NAME} ..."
    URL="${IPTVPRO_URL:-$BASE_RAW/$TAR_NAME}"
    download "$URL" || download "$BASE_GH/$TAR_NAME" || die "download failed, check the network on the receiver"
    [ -s "$TMP" ] || die "the downloaded file is empty"
fi

# Verify the archive before deleting the installed version.
tar -tzf "$TMP" >/dev/null 2>&1 || die "invalid archive: $TMP"

say "Extracting and installing to $TARGET_DIR ..."
# Remove old version if present to avoid stale/orphaned files
rm -rf "$TARGET_DIR"

tar -xzf "$TMP" -C / || die "tar extraction failed"

[ "$TMP" = "$LOCAL_TAR" ] || rm -f "$TMP"
say "Installed successfully: $TARGET_DIR"

if [ "$NO_RESTART" = "1" ]; then
    say "Restart Enigma2 manually: Menu > Standby & Restart > Restart GUI"
    exit 0
fi

say "Restarting Enigma2 ..."
if command -v init >/dev/null 2>&1; then
    init 4
    sleep 2
    init 3
elif command -v killall >/dev/null 2>&1; then
    killall -9 enigma2
else
    say "Restart Enigma2 manually: Menu > Standby & Restart > Restart GUI"
fi

say "Done. Open: Menu > Plugins > IPTV Player Pro"
