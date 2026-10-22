#!/usr/bin/env bash
# ------------------------------------------------------------
# make_tar_package.sh
#   - حزم الإضافة بصيغة tar.gz المتوافقة مع Enigma2
# ------------------------------------------------------------

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

python build_tar.py
