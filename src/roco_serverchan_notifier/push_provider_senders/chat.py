from __future__ import annotations

from ..push_http import HttpSession, JsonPostRequest, post_json
from ..push_models import NotificationMessage, ProviderConfig, PushResult


def _chat_text(message: NotificationMessage) -> str:
    return f"{message.title}\n\n{message.markdown}"


def send_telegram(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    url = f"https://api.telegram.org/bot{provider.config['bot_token']}/sendMessage"
    payload = {
        "chat_id": str(provider.config["chat_id"]),
        "text": _chat_text(message),
    }
    return post_json(JsonPostRequest(provider, session, url, payload, timeout))


def send_discord(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    webhook = str(provider.config["webhook"])
    separator = "&" if "?" in webhook else "?"
    response = session.post(
        f"{webhook}{separator}wait=true",
        json={
            "content": _chat_text(message),
            "allowed_mentions": {"parse": []},
        },
        timeout=timeout,
    )
    success = 200 <= response.status_code < 300
    message_text = response.text[:200] or response.reason
    return PushResult(
        provider.id,
        provider.name,
        provider.type,
        success,
        message_text,
        response.status_code,
    )
