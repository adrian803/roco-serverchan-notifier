from __future__ import annotations

import time
import urllib.parse
from typing import Any

import requests

from .provider_specs import provider_required_fields
from .push_http import HttpSession, JsonPostRequest, post_json, result_from_response
from .push_models import NotificationMessage, ProviderConfig, PushResult
from .push_provider_auth import append_dingtalk_sign, feishu_sign, get_wecom_token
from .push_redaction import redact_sensitive_text


def split_csv(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def missing_required(provider: ProviderConfig) -> list[str]:
    return [
        field_name
        for field_name in provider_required_fields(provider.type)
        if not str(provider.config.get(field_name, "")).strip()
    ]


def send_serverchan(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    url = f"https://sctapi.ftqq.com/{provider.config['sendkey']}.send"
    response = session.post(url, data={"title": message.title, "desp": message.markdown}, timeout=timeout)
    return result_from_response(provider, response, success_codes={0, "0", None})


def send_pushplus(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    payload = {
        "token": provider.config["token"],
        "title": message.title,
        "content": message.markdown,
        "template": "markdown",
    }
    for key in ("topic", "channel"):
        value = str(provider.config.get(key, "")).strip()
        if value:
            payload[key] = value
    return post_json(
        JsonPostRequest(
            provider,
            session,
            "https://www.pushplus.plus/send",
            payload,
            timeout,
            success_codes={200, "200", 0, "0"},
        )
    )


def send_wecomchan(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    token = get_wecom_token(provider, session, timeout)
    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
    payload = {
        "touser": provider.config.get("touser") or "@all",
        "msgtype": "text",
        "agentid": int(provider.config["agentid"]),
        "text": {"content": f"{message.title}\n\n{message.body}\n\n{message.markdown}"},
        "safe": 0,
    }
    return post_json(JsonPostRequest(provider, session, url, payload, timeout))


def send_wecom_bot(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    webhook = str(provider.config.get("webhook") or "").strip()
    if not webhook:
        key = str(provider.config.get("key") or "").strip()
        if not key:
            return PushResult(provider.id, provider.name, provider.type, False, "缺少 webhook 或 key")
        webhook = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={key}"
    payload = {"msgtype": "markdown", "markdown": {"content": message.markdown}}
    return post_json(JsonPostRequest(provider, session, webhook, payload, timeout))


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


def send_bark(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    server_url = str(provider.config.get("server_url") or "https://api.day.app").rstrip("/")
    url = f"{server_url}/{provider.config['device_key']}"
    payload = {
        "title": message.title,
        "body": f"{message.body}\n\n{message.markdown}",
    }
    group = str(provider.config.get("group") or "").strip()
    if group:
        payload["group"] = group
    return post_json(
        JsonPostRequest(
            provider,
            session,
            url,
            payload,
            timeout,
            success_codes={200, "200", 0, "0"},
        )
    )


def send_dingtalk_bot(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    webhook = append_dingtalk_sign(provider.config["webhook"], str(provider.config.get("secret") or ""))
    payload = {
        "msgtype": "markdown",
        "markdown": {"title": message.title, "text": message.markdown},
    }
    return post_json(JsonPostRequest(provider, session, webhook, payload, timeout))


def send_feishu_bot(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    payload: dict[str, Any] = {
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
    secret = str(provider.config.get("secret") or "").strip()
    if secret:
        timestamp = str(int(time.time()))
        payload["timestamp"] = timestamp
        payload["sign"] = feishu_sign(secret, timestamp)
    return post_json(
        JsonPostRequest(provider, session, provider.config["webhook"], payload, timeout)
    )


def send_ntfy(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    base_url = str(provider.config.get("base_url") or "https://ntfy.sh").rstrip("/")
    url = f"{base_url}/{provider.config['topic']}"
    headers = {
        "Title": message.title,
        "Markdown": "yes",
    }
    for name, header in (("priority", "Priority"), ("tags", "Tags")):
        value = str(provider.config.get(name) or "").strip()
        if value:
            headers[header] = value
    token = str(provider.config.get("token") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = session.post(
        url,
        data=message.markdown.encode("utf-8"),
        headers=headers,
        timeout=timeout,
    )
    success = 200 <= response.status_code < 300
    return PushResult(
        provider.id,
        provider.name,
        provider.type,
        success,
        response.text[:200] or response.reason,
        response.status_code,
    )


def send_gotify(
    provider: ProviderConfig, message: NotificationMessage, session: HttpSession, timeout: int
) -> PushResult:
    base_url = str(provider.config["base_url"]).rstrip("/")
    app_token = urllib.parse.quote_plus(str(provider.config["app_token"]))
    url = f"{base_url}/message?token={app_token}"
    try:
        priority = int(provider.config.get("priority") or 5)
    except (TypeError, ValueError):
        priority = 5
    payload = {"title": message.title, "message": message.markdown, "priority": priority}
    response = session.post(url, json=payload, timeout=timeout)
    success = 200 <= response.status_code < 300
    message_text = response.text[:200] or response.reason
    return PushResult(provider.id, provider.name, provider.type, success, message_text, response.status_code)


PROVIDER_SENDERS = {
    "serverchan": send_serverchan,
    "pushplus": send_pushplus,
    "wecomchan": send_wecomchan,
    "wecom_bot": send_wecom_bot,
    "wxpusher": send_wxpusher,
    "bark": send_bark,
    "dingtalk_bot": send_dingtalk_bot,
    "feishu_bot": send_feishu_bot,
    "ntfy": send_ntfy,
    "gotify": send_gotify,
}


def send_provider(
    provider: ProviderConfig,
    message: NotificationMessage,
    *,
    session: HttpSession | None = None,
    timeout: int = 10,
) -> PushResult:
    missing = missing_required(provider)
    if missing:
        return PushResult(
            provider.id,
            provider.name,
            provider.type,
            False,
            f"缺少配置: {', '.join(missing)}",
        )

    client = session or requests.Session()
    try:
        sender = PROVIDER_SENDERS.get(provider.type)
        if sender is None:
            return PushResult(
                provider.id,
                provider.name,
                provider.type,
                False,
                f"未知通道类型: {provider.type}",
            )
        result = sender(provider, message, client, timeout)
        return PushResult(
            result.provider_id,
            result.provider_name,
            result.provider_type,
            result.success,
            redact_sensitive_text(provider, result.message),
            result.status_code,
        )
    except Exception as exc:
        return PushResult(
            provider.id,
            provider.name,
            provider.type,
            False,
            redact_sensitive_text(provider, str(exc)),
        )
