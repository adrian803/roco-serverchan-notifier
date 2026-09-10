from __future__ import annotations

import json

import requests

from ..push_http import HttpSession, result_from_status
from ..push_models import NotificationMessage, ProviderConfig, PushResult


def send_discord(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    webhook = str(provider.config["webhook"])
    separator = "&" if "?" in webhook else "?"

    # If image data is available, send as file attachment
    if message.image_data:
        files = {
            "files[0]": ("merchant_card.png", message.image_data, "image/png"),
        }
        data = {
            "payload_json": json.dumps({
                "content": f"{message.title}\n\n{message.body}",
                "allowed_mentions": {"parse": []},
            }),
        }
        try:
            response = session.post(
                f"{webhook}{separator}wait=true",
                data=data,
                files=files,
                timeout=timeout,
            )
            result = result_from_status(provider, response)
            if result.success:
                return result
        except requests.RequestException:
            pass  # Image delivery is optional; still attempt the original text message.

    response = session.post(
        f"{webhook}{separator}wait=true",
        json={
            "content": f"{message.title}\n\n{message.markdown}",
            "allowed_mentions": {"parse": []},
        },
        timeout=timeout,
    )
    return result_from_status(provider, response)
