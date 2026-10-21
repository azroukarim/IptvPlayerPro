#!/bin/sh
# ============================================================
#  IPTV Player Pro - Enigma2 installer
#  https://github.com/azroukarim/IptvPlayerPro
# ------------------------------------------------------------
#  Usage on the receiver:
#    wget -q --no-check-certificate -O /tmp/iptvpro.sh \
#      https://raw.githubusercontent.com/azroukarim/IptvPlayerPro/main/install.sh
#    sh /tmp/iptvpro.sh
#
#  Or copy install.sh together with the .ipk to /tmp then:
#    sh /tmp/install.sh
#
#  Options:
#    --no-restart     install without restarting Enigma2
#    --ipk FILE       install a local .ipk file
# ============================================================

VERSION="1.1.3"
PKG_NAME="enigma2-plugin-extensions-iptvplayerpro"
PKG="${PKG_NAME}_${VERSION}_all.ipk"
BASE_RAW="https://raw.githubusercontent.com/azroukarim/IptvPlayerPro/main/dist"
BASE_GH="https://github.com/azroukarim/IptvPlayerPro/raw/main/dist"
TMP="/tmp/${PKG}"

NO_RESTART=0
LOCAL_IPK=""

say() {
    printf '%s\n' "[IPTV Player Pro] $*"
}

die() {
    printf '%s\n' "[IPTV Player Pro] ERROR: $*" >&2
    exit 1
}

usage() {
    printf '%s\n' "IPTV Player Pro installer"
    printf '%s\n' "  --no-restart    install without restarting Enigma2"
    printf '%s\n' "  --ipk FILE      install a local .ipk file"
    printf '%s\n' "  --help          show this help"
}

download() {
    if command -v wget >/dev/null 2>&1; then
        wget -q -O "$TMP" "$1" >/dev/null 2>&1 && return 0
        wget -q --no-check-certificate -O "$TMP" "$1" >/dev/null 2>&1 && return 0
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
        --ipk)
            shift
            [ $# -gt 0 ] || die "--ipk needs a file path"
            LOCAL_IPK="$1"
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

# If the script was copied next to the .ipk, use that local file.
SELF_DIR="."
case "$0" in
    */*) SELF_DIR="${0%/*}" ;;
esac
if [ -z "$LOCAL_IPK" ] && [ -f "$SELF_DIR/$PKG" ]; then
    LOCAL_IPK="$SELF_DIR/$PKG"
fi

if [ -n "$LOCAL_IPK" ]; then
    [ -f "$LOCAL_IPK" ] || die "file not found: $LOCAL_IPK"
    TMP="$LOCAL_IPK"
    say "Using local package: $TMP"
else
    say "Downloading ${PKG} ..."
    URL="${IPTVPRO_URL:-$BASE_RAW/$PKG}"
    download "$URL" || download "$BASE_GH/$PKG" || die "download failed, check the network on the receiver"
    [ -s "$TMP" ] || die "the downloaded file is empty"
fi

# Locate opkg even when /usr/bin is not in PATH.
OPKG=""
for candidate in opkg /usr/bin/opkg /usr/sbin/opkg /bin/opkg; do
    if command -v "$candidate" >/dev/null 2>&1; then
        OPKG="$candidate"
        break
    fi
done
[ -n "$OPKG" ] || die "opkg was not found on this image"

say "Installing ${PKG} ..."
"$OPKG" install "$TMP" || \
    "$OPKG" install --force-reinstall "$TMP" || \
    "$OPKG" install --force-depends --force-overwrite --force-reinstall "$TMP" || \
    die "installation failed"

[ "$TMP" = "$LOCAL_IPK" ] || rm -f "$TMP"
say "Installed successfully: /usr/lib/enigma2/python/Plugins/Extensions/IPTVPlayerPro"

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
