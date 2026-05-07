from __future__ import annotations

from ..push_http import HttpSession, result_from_status
from ..push_models import NotificationMessage, ProviderConfig, PushResult


def send_discord(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    webhook = str(provider.config["webhook"])
    separator = "&" if "?" in webhook else "?"
    response = session.post(
        f"{webhook}{separator}wait=true",
        json={
            "content": f"{message.title}\n\n{message.markdown}",
            "allowed_mentions": {"parse": []},
        },
        timeout=timeout,
    )
    return result_from_status(provider, response)
