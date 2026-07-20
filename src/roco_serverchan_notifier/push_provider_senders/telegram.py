from __future__ import annotations

import io

from ..push_http import HttpSession, result_from_response, result_from_status
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
            "photo": ("merchant_card.png", io.BytesIO(message.image_data), "image/png"),
        }
        caption = f"{message.title}\n\n{message.body}"
        # Telegram caption limit is 1024 chars
        if len(caption) > 1024:
            caption = caption[:1021] + "..."
        data = {
            "chat_id": chat_id,
            "caption": caption,
            "parse_mode": "Markdown",
        }
        response = session.post(url, data=data, files=files, timeout=timeout)
        return result_from_response(provider, response, success_codes={200, "200", True, "ok"})

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": f"{message.title}\n\n{message.markdown}",
    }
    return result_from_response(provider, session.post(url, json=payload, timeout=timeout))
