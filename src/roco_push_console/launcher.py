from __future__ import annotations

import os

from . import app, scheduler, web


MODE_ALIASES = {
    "": "web",
    "web": "web",
    "console": "web",
    "ui": "web",
    "scheduler": "scheduler",
    "schedule": "scheduler",
    "headless": "scheduler",
    "cron": "scheduler",
    "once": "once",
    "run-once": "once",
}


def normalize_app_mode(value: str | None) -> str:
    mode = str(value or "").strip().lower()
    if mode in MODE_ALIASES:
        return MODE_ALIASES[mode]
    valid = ", ".join(sorted({item for item in MODE_ALIASES.values()}))
    raise SystemExit(f"未知 APP_MODE: {value!r}，可用模式: {valid}")


def main() -> None:
    mode = normalize_app_mode(os.environ.get("APP_MODE", "web"))
    if mode == "scheduler":
        return scheduler.cli()
    if mode == "once":
        return app.cli()
    return web.cli()


if __name__ == "__main__":
    main()
