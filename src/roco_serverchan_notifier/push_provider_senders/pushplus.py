from __future__ import annotations

from ..push_http import HttpSession, JsonPostRequest, post_json
from ..push_models import NotificationMessage, ProviderConfig, PushResult


def send_pushplus(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    payload = {
        "token": provider.config["token"],
        "title": message.title,
        "content": message.markdown,
        "template": "markdown",
    }
    for key in ("topic", "channel"):
        value = str(provider.config.get(key, "")).strip()
        if value:
            payload[key] = value
    return post_json(
        JsonPostRequest(
            provider,
            session,
            "https://www.pushplus.plus/send",
            payload,
            timeout,
            success_codes={200, "200", 0, "0"},
        )
    )
