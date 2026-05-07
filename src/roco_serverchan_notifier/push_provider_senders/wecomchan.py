from __future__ import annotations

from ..push_http import HttpSession, JsonPostRequest, post_json
from ..push_models import NotificationMessage, ProviderConfig, PushResult
from ..push_provider_auth import get_wecom_token


def send_wecomchan(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    token = get_wecom_token(provider, session, timeout)
    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
    payload = {
        "touser": provider.config.get("touser") or "@all",
        "msgtype": "text",
        "agentid": int(provider.config["agentid"]),
        "text": {"content": f"{message.title}\n\n{message.body}\n\n{message.markdown}"},
        "safe": 0,
    }
    return post_json(JsonPostRequest(provider, session, url, payload, timeout))
