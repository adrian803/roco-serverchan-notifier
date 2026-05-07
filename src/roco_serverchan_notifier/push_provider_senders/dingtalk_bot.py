from __future__ import annotations

from ..push_http import HttpSession, JsonPostRequest, post_json
from ..push_models import NotificationMessage, ProviderConfig, PushResult
from ..push_provider_auth import append_dingtalk_sign


def send_dingtalk_bot(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    webhook = append_dingtalk_sign(provider.config["webhook"], str(provider.config.get("secret") or ""))
    payload = {
        "msgtype": "markdown",
        "markdown": {"title": message.title, "text": message.markdown},
    }
    return post_json(JsonPostRequest(provider, session, webhook, payload, timeout))
