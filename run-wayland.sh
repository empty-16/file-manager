#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export QT_QPA_PLATFORM=wayland
export QT_IM_MODULE=simple
export QT_LOGGING_RULES="qt.qpa.wayland.textinput=false"

exec docker compose run --rm \
  -e QT_QPA_PLATFORM="$QT_QPA_PLATFORM" \
  -e QT_IM_MODULE="$QT_IM_MODULE" \
  -e QT_LOGGING_RULES="$QT_LOGGING_RULES" \
  -e FILE_MANAGER_NATIVE_TITLEBAR="${FILE_MANAGER_NATIVE_TITLEBAR:-0}" \
  dev python file-manager.py "$@"
