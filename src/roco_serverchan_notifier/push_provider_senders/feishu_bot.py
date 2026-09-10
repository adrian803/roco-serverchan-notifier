from __future__ import annotations

import os
import time

import requests

from ..push_http import HttpSession, JsonPostRequest, post_json
from ..push_models import NotificationMessage, ProviderConfig, PushResult
from ..push_provider_auth import feishu_sign

# --- tenant_access_token cache (module-level) ---
_token_cache: dict[tuple[str, str], tuple[str, float]] = {}


def _get_tenant_token(session: HttpSession, timeout: int) -> str | None:
    """Get Feishu tenant_access_token using app_id + app_secret."""
    app_id = os.environ.get("FEISHU_APP_ID", "").strip()
    app_secret = os.environ.get("FEISHU_APP_SECRET", "").strip()
    if not app_id or not app_secret:
        return None

    cache_key = (app_id, app_secret)
    cached = _token_cache.get(cache_key)
    now = time.time()
    if cached and cached[1] > now + 120:
        return cached[0]

    try:
        resp = session.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": app_id, "app_secret": app_secret},
            timeout=timeout,
        )
        data = resp.json()
        if resp.status_code >= 400 or not isinstance(data, dict) or data.get("code") != 0:
            return None
        token = data.get("tenant_access_token")
        if not isinstance(token, str) or not token:
            return None
        expire = int(data.get("expire", 7200))
        _token_cache[cache_key] = (token, now + expire)
        return token
    except Exception:
        return None


def _upload_image(session: HttpSession, image_data: bytes, timeout: int) -> str | None:
    """Upload image to Feishu and return image_key."""
    token = _get_tenant_token(session, timeout)
    if not token:
        return None

    try:
        files = {
            "image": ("image.png", image_data, "image/png"),
        }
        resp = session.post(
            "https://open.feishu.cn/open-apis/im/v1/images",
            headers={"Authorization": f"Bearer {token}"},
            data={"image_type": "message"},
            files=files,
            timeout=timeout,
        )
        data = resp.json()
        if resp.status_code >= 400 or not isinstance(data, dict) or data.get("code") != 0:
            return None
        image_key = data.get("data", {}).get("image_key")
        return image_key if isinstance(image_key, str) and image_key else None
    except Exception:
        return None


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

    # Upload image and send via webhook
    if message.image_data:
        image_key = _upload_image(session, message.image_data, timeout)
        if image_key:
            image_payload = {
                "msg_type": "image",
                "content": {"image_key": image_key},
            }
            _sign_payload(image_payload, provider)
            try:
                result = post_json(JsonPostRequest(provider, session, webhook, image_payload, timeout))
                if result.success:
                    return result
            except requests.RequestException:
                pass  # Image delivery is optional; still attempt the original text message.

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
    return post_json(JsonPostRequest(provider, session, webhook, payload, timeout))
