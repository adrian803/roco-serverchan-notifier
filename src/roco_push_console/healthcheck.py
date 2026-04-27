from __future__ import annotations

import os
import socket

from .launcher import normalize_app_mode


def main() -> int:
    mode = normalize_app_mode(os.environ.get("APP_MODE", "web"))
    if mode != "web":
        return 0

    host = os.environ.get("WEB_HEALTH_HOST", "127.0.0.1")
    port = int(os.environ.get("WEB_PORT", "19892"))
    with socket.create_connection((host, port), 3):
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
