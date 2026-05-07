from __future__ import annotations

import urllib.parse

from ..push_http import HttpSession, result_from_status
from ..push_models import NotificationMessage, ProviderConfig, PushResult
from .common import provider_config_text


def send_gotify(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    base_url = str(provider.config["base_url"]).rstrip("/")
    app_token = urllib.parse.quote_plus(str(provider.config["app_token"]))
    url = f"{base_url}/message?token={app_token}"
    try:
        priority = int(provider_config_text(provider, "priority") or 0)
    except (TypeError, ValueError):
        priority = 5
    if priority <= 0:
        priority = 5
    payload = {"title": message.title, "message": message.markdown, "priority": priority}
    response = session.post(url, json=payload, timeout=timeout)
    return result_from_status(provider, response)
