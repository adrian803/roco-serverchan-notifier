from __future__ import annotations

from ..push_http import HttpSession, JsonPostRequest, post_json
from ..push_models import NotificationMessage, ProviderConfig, PushResult


def send_telegram(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    url = f"https://api.telegram.org/bot{provider.config['bot_token']}/sendMessage"
    payload = {
        "chat_id": str(provider.config["chat_id"]),
        "text": f"{message.title}\n\n{message.markdown}",
    }
    return post_json(JsonPostRequest(provider, session, url, payload, timeout))
