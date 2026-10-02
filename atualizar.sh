#!/usr/bin/env bash
set -Eeuo pipefail
BASE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
command -v python3 >/dev/null || { echo 'Python 3 é necessário.' >&2; exit 1; }
exec python3 "$BASE/scripts/maintenance.py" update "$@"
