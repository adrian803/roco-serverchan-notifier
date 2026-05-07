from __future__ import annotations

from typing import Any

from ..push_http import HttpSession, JsonPostRequest, post_json
from ..push_models import NotificationMessage, ProviderConfig, PushResult
from .common import split_csv


def send_wxpusher(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    payload: dict[str, Any] = {
        "appToken": provider.config["app_token"],
        "content": message.markdown,
        "summary": message.title,
        "contentType": 3,
    }
    uids = split_csv(provider.config.get("uids"))
    topic_ids = split_csv(provider.config.get("topic_ids"))
    if uids:
        payload["uids"] = uids
    if topic_ids:
        payload["topicIds"] = [int(item) if item.isdigit() else item for item in topic_ids]
    return post_json(
        JsonPostRequest(
            provider,
            session,
            "https://wxpusher.zjiecode.com/api/send/message",
            payload,
            timeout,
            success_codes={1000, "1000", 0, "0"},
        )
    )
