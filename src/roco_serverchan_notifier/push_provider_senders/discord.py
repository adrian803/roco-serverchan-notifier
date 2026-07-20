from __future__ import annotations

import io

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
            "file": ("merchant_card.png", io.BytesIO(message.image_data), "image/png"),
        }
        data = {
            "content": f"{message.title}\n\n{message.body}",
            "allowed_mentions": '{"parse": []}',
        }
        response = session.post(
            f"{webhook}{separator}wait=true",
            data=data,
            files=files,
            timeout=timeout,
        )
        return result_from_status(provider, response)

    response = session.post(
        f"{webhook}{separator}wait=true",
        json={
            "content": f"{message.title}\n\n{message.markdown}",
            "allowed_mentions": {"parse": []},
        },
        timeout=timeout,
    )
    return result_from_status(provider, response)
