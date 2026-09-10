from __future__ import annotations

import requests

from ..push_http import HttpSession, JsonPostRequest, post_json, result_from_response
from ..push_models import NotificationMessage, ProviderConfig, PushResult


def send_telegram(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    bot_token = str(provider.config["bot_token"])
    chat_id = str(provider.config["chat_id"])

    # If image data is available, send as photo
    if message.image_data:
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        files = {
            "photo": ("merchant_card.png", message.image_data, "image/png"),
        }
        caption = f"{message.title}\n\n{message.body}"
        # Telegram caption limit is 1024 chars
        if len(caption) > 1024:
            caption = caption[:1021] + "..."
        data = {
            "chat_id": chat_id,
            "caption": caption,
        }
        try:
            response = session.post(url, data=data, files=files, timeout=timeout)
            result = result_from_response(provider, response, success_codes={0, "0"})
            if result.success:
                return result
        except requests.RequestException:
            pass  # Image delivery is optional; still attempt the original text message.

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": f"{message.title}\n\n{message.markdown}",
    }
    return post_json(JsonPostRequest(provider, session, url, payload, timeout))
