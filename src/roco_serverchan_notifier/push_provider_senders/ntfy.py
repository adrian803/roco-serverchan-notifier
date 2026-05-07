from __future__ import annotations

from ..push_http import HttpSession, result_from_status
from ..push_models import NotificationMessage, ProviderConfig, PushResult
from .common import provider_config_text


def send_ntfy(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    base_url = provider_config_text(provider, "base_url").rstrip("/")
    url = f"{base_url}/{provider.config['topic']}"
    headers = {
        "Title": message.title,
        "Markdown": "yes",
    }
    for name, header in (("priority", "Priority"), ("tags", "Tags")):
        value = provider_config_text(provider, name)
        if value:
            headers[header] = value
    token = provider_config_text(provider, "token")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = session.post(
        url,
        data=message.markdown.encode("utf-8"),
        headers=headers,
        timeout=timeout,
    )
    return result_from_status(provider, response)
