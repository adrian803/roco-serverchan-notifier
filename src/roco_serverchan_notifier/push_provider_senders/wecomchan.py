from __future__ import annotations

import base64
import hashlib

from ..push_http import HttpSession, JsonPostRequest, post_json
from ..push_models import NotificationMessage, ProviderConfig, PushResult
from ..push_provider_auth import get_wecom_token


def send_wecomchan(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    token = get_wecom_token(provider, session, timeout)
    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
    agentid = int(provider.config["agentid"])
    touser = provider.config.get("touser") or "@all"

    # If image data is available, send as image message
    if message.image_data:
        img_base64 = base64.b64encode(message.image_data).decode()
        img_md5 = hashlib.md5(message.image_data).hexdigest()
        payload = {
            "touser": touser,
            "msgtype": "image",
            "agentid": agentid,
            "image": {
                "base64": img_base64,
                "md5": img_md5,
            },
            "safe": 0,
        }
        return post_json(JsonPostRequest(provider, session, url, payload, timeout))

    payload = {
        "touser": touser,
        "msgtype": "text",
        "agentid": agentid,
        "text": {"content": f"{message.title}\n\n{message.body}\n\n{message.markdown}"},
        "safe": 0,
    }
    return post_json(JsonPostRequest(provider, session, url, payload, timeout))
