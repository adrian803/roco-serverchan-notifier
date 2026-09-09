from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from ..push_http import HttpSession, JsonPostRequest, post_json
from ..push_models import NotificationMessage, ProviderConfig, PushResult
from ..push_provider_auth import feishu_sign

IMAGE_DIR = Path("/data/images")

# --- tenant_access_token cache (module-level) ---
_token_cache: dict[str, tuple[str, float]] = {}


def _get_tenant_token(session: HttpSession, timeout: int) -> str | None:
    """Get Feishu tenant_access_token using app_id + app_secret."""
    cache_key = "tenant_token"
    cached = _token_cache.get(cache_key)
    now = time.time()
    if cached and cached[1] > now + 120:
        return cached[0]

    app_id = os.environ.get("FEISHU_APP_ID", "").strip()
    app_secret = os.environ.get("FEISHU_APP_SECRET", "").strip()
    if not app_id or not app_secret:
        return None

    try:
        resp = session.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": app_id, "app_secret": app_secret},
            timeout=timeout,
        )
        data = resp.json()
        if data.get("code") != 0:
            return None
        token = data["tenant_access_token"]
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
        import io
        files = {
            "image_type": (None, "message"),
            "image": ("image.png", io.BytesIO(image_data), "image/png"),
        }
        resp = session.post(
            "https://open.feishu.cn/open-apis/im/v1/images",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
            timeout=timeout,
        )
        data = resp.json()
        if data.get("code") != 0:
            return None
        return data.get("data", {}).get("image_key")
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


def _save_image(image_data: bytes) -> Path | None:
    """Save image to disk for host-side pickup."""
    try:
        IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        path = IMAGE_DIR / "merchant_card_latest.png"
        path.write_bytes(image_data)
        return path
    except Exception:
        return None


def _build_card_message(message: NotificationMessage, image_sent: bool) -> dict:
    """Build an interactive card message for Feishu."""
    elements: list[dict[str, Any]] = []

    if message.markdown:
        elements.append({"tag": "markdown", "content": message.markdown})

    if image_sent:
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "markdown",
            "content": "🖼️ 商品卡片图片已随消息发送",
        })

    elements.append({
        "tag": "note",
        "elements": [{"tag": "plain_text", "content": "洛克王国远行商人监控"}],
    })

    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": message.title},
                "template": "turquoise",
            },
            "elements": elements,
        },
    }


def send_feishu_bot(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    webhook = provider.config["webhook"]

    # Save image for host-side script to upload and send
    image_saved = False
    if message.image_data:
        image_saved = _save_image(message.image_data) is not None

    # Upload image and send via webhook
    if image_saved and message.image_data:
        image_key = _upload_image(session, message.image_data, timeout)
        if image_key:
            image_payload = {
                "msg_type": "image",
                "content": {"image_key": image_key},
            }
            _sign_payload(image_payload, provider)
            result = post_json(JsonPostRequest(provider, session, webhook, image_payload, timeout))
            if result.success:
                return result

    # Fallback: send card if no image
    payload = _build_card_message(message, False)
    _sign_payload(payload, provider)
    return post_json(JsonPostRequest(provider, session, webhook, payload, timeout))
