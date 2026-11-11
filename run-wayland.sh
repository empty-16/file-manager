#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export QT_QPA_PLATFORM=wayland

exec docker compose run --rm dev python file-manager.py "$@"
