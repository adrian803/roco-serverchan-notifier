#!/bin/sh
set -eu

CONFIG_FILE="${CONFIG_PATH:-/data/config.json}"
CONFIG_DIR="$(dirname "$CONFIG_FILE")"

if [ "$(id -u)" = "0" ]; then
  mkdir -p "$CONFIG_DIR"
  chown -R app:app "$CONFIG_DIR" 2>/dev/null || {
    echo "warning: unable to chown $CONFIG_DIR; continuing with current permissions" >&2
  }

  APP_UID="$(id -u app)"
  APP_GID="$(id -g app)"
  exec setpriv --reuid "$APP_UID" --regid "$APP_GID" --init-groups "$@"
fi

exec "$@"
