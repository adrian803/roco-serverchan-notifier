from __future__ import annotations

from ..push_http import HttpSession, JsonPostRequest, post_json
from ..push_models import NotificationMessage, ProviderConfig, PushResult
from .common import provider_config_text


def send_bark(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    server_url = provider_config_text(provider, "server_url").rstrip("/")
    url = f"{server_url}/{provider.config['device_key']}"
    payload = {
        "title": message.title,
        "body": f"{message.body}\n\n{message.markdown}",
    }
    group = provider_config_text(provider, "group")
    if group:
        payload["group"] = group
    return post_json(
        JsonPostRequest(
            provider,
            session,
            url,
            payload,
            timeout,
            success_codes={200, "200", 0, "0"},
        )
    )
