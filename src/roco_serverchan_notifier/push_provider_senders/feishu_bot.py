from __future__ import annotations

import base64
import time

from ..push_http import HttpSession, JsonPostRequest, post_json
from ..push_models import NotificationMessage, ProviderConfig, PushResult
from ..push_provider_auth import feishu_sign


def _sign_payload(payload: dict, provider: ProviderConfig) -> dict:
    """Add signature to payload if secret is configured."""
    secret = str(provider.config.get("secret") or "").strip()
    if secret:
        timestamp = str(int(time.time()))
        payload["timestamp"] = timestamp
        payload["sign"] = feishu_sign(secret, timestamp)
    return payload


def send_feishu_bot(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    webhook = provider.config["webhook"]

    # If image data is available, send as image message
    if message.image_data:
        # Feishu webhook image message requires uploading the image first
        # For webhook-based bots, we use the "image" message type with base64
        # Note: Feishu webhooks don't natively support inline base64 images,
        # so we send text + image description
        img_b64 = base64.b64encode(message.image_data).decode()
        payload: dict[str, object] = {
            "msg_type": "text",
            "content": {
                "text": f"{message.title}\n\n[商品卡片图片已生成，大小: {len(message.image_data)} bytes]\n\n{message.body}"
            },
        }
        _sign_payload(payload, provider)
        return post_json(JsonPostRequest(provider, session, webhook, payload, timeout))

    payload = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": message.title,
                    "content": [[{"tag": "text", "text": f"{message.body}\n\n{message.markdown}"}]],
                }
            }
        },
    }
    _sign_payload(payload, provider)
    return post_json(
        JsonPostRequest(provider, session, webhook, payload, timeout)
    )
