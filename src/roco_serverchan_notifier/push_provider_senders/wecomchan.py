from __future__ import annotations

import requests

from ..push_http import HttpSession, JsonPostRequest, post_json
from ..push_models import NotificationMessage, ProviderConfig, PushResult
from ..push_provider_auth import get_wecom_token


def _upload_image(session: HttpSession, token: str, image_data: bytes, timeout: int) -> str | None:
    """Application messages reference temporary media uploaded with the same token."""
    try:
        response = session.post(
            f"https://qyapi.weixin.qq.com/cgi-bin/media/upload?access_token={token}&type=image",
            files={"media": ("merchant_card.png", image_data, "image/png")},
            timeout=timeout,
        )
        payload = response.json()
        if response.status_code >= 400 or not isinstance(payload, dict):
            return None
        if payload.get("errcode") not in (0, "0"):
            return None
        media_id = payload.get("media_id")
        return media_id if isinstance(media_id, str) and media_id else None
    except (requests.RequestException, ValueError):
        return None


def send_wecomchan(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    token = get_wecom_token(provider, session, timeout)
    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
    agentid = int(provider.config["agentid"])
    touser = provider.config.get("touser") or "@all"

    # If image data is available, send as image message
    if message.image_data:
        media_id = _upload_image(session, token, message.image_data, timeout)
        if media_id:
            payload = {
                "touser": touser,
                "msgtype": "image",
                "agentid": agentid,
                "image": {"media_id": media_id},
                "safe": 0,
            }
            try:
                result = post_json(JsonPostRequest(provider, session, url, payload, timeout))
                if result.success:
                    return result
            except requests.RequestException:
                pass  # Image delivery is optional; still attempt the original text message.

    payload = {
        "touser": touser,
        "msgtype": "text",
        "agentid": agentid,
        "text": {"content": f"{message.title}\n\n{message.body}\n\n{message.markdown}"},
        "safe": 0,
    }
    return post_json(JsonPostRequest(provider, session, url, payload, timeout))
