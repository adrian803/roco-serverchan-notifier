from __future__ import annotations

import base64
import hashlib

from ..push_http import HttpSession, JsonPostRequest, post_json
from ..push_models import NotificationMessage, ProviderConfig, PushResult


def send_wecom_bot(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    webhook = str(provider.config.get("webhook") or "").strip()
    if not webhook:
        key = str(provider.config.get("key") or "").strip()
        if not key:
            return PushResult(provider.id, provider.name, provider.type, False, "缺少 webhook 或 key")
        webhook = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={key}"

    # If image data is available, send as image message type
    if message.image_data:
        img_base64 = base64.b64encode(message.image_data).decode()
        img_md5 = hashlib.md5(message.image_data).hexdigest()
        payload = {
            "msgtype": "image",
            "image": {
                "base64": img_base64,
                "md5": img_md5,
            },
        }
        return post_json(JsonPostRequest(provider, session, webhook, payload, timeout))

    payload = {"msgtype": "markdown", "markdown": {"content": message.markdown}}
    return post_json(JsonPostRequest(provider, session, webhook, payload, timeout))
