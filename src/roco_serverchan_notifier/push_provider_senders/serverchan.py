from __future__ import annotations

from ..push_http import HttpSession, result_from_response
from ..push_models import NotificationMessage, ProviderConfig, PushResult


def send_serverchan(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    url = f"https://sctapi.ftqq.com/{provider.config['sendkey']}.send"
    response = session.post(url, data={"title": message.title, "desp": message.markdown}, timeout=timeout)
    return result_from_response(provider, response, success_codes={0, "0", None})
