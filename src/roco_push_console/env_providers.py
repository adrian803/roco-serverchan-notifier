from __future__ import annotations

import os
from typing import Any

from .provider_specs import PROVIDER_TYPES, provider_secret_fields
from .push_models import ProviderConfig


ENV_PROVIDER_FIELDS: dict[str, dict[str, str]] = {
    "serverchan": {"sendkey": "SERVERCHAN_SENDKEY"},
    "pushplus": {
        "token": "PUSHPLUS_TOKEN",
        "topic": "PUSHPLUS_TOPIC",
        "channel": "PUSHPLUS_CHANNEL",
    },
    "wecomchan": {
        "corpid": "WECOM_CORPID",
        "secret": "WECOM_SECRET",
        "agentid": "WECOM_AGENTID",
        "touser": "WECOM_TOUSER",
    },
    "wecom_bot": {"webhook": "WECOM_BOT_WEBHOOK", "key": "WECOM_BOT_KEY"},
    "wxpusher": {
        "app_token": "WXPUSHER_APP_TOKEN",
        "uids": "WXPUSHER_UIDS",
        "topic_ids": "WXPUSHER_TOPIC_IDS",
    },
    "bark": {
        "server_url": "BARK_SERVER_URL",
        "device_key": "BARK_DEVICE_KEY",
        "group": "BARK_GROUP",
    },
    "dingtalk_bot": {"webhook": "DINGTALK_WEBHOOK", "secret": "DINGTALK_SECRET"},
    "feishu_bot": {"webhook": "FEISHU_WEBHOOK", "secret": "FEISHU_SECRET"},
    "ntfy": {
        "base_url": "NTFY_BASE_URL",
        "topic": "NTFY_TOPIC",
        "token": "NTFY_TOKEN",
        "priority": "NTFY_PRIORITY",
        "tags": "NTFY_TAGS",
    },
    "gotify": {
        "base_url": "GOTIFY_BASE_URL",
        "app_token": "GOTIFY_APP_TOKEN",
        "priority": "GOTIFY_PRIORITY",
    },
}

ENV_PROVIDER_IDS = {
    "serverchan": "serverchan-default",
    "pushplus": "pushplus-env",
    "wecomchan": "wecomchan-env",
    "wecom_bot": "wecom-bot-env",
    "wxpusher": "wxpusher-env",
    "bark": "bark-env",
    "dingtalk_bot": "dingtalk-env",
    "feishu_bot": "feishu-env",
    "ntfy": "ntfy-env",
    "gotify": "gotify-env",
}


def env_text(name: str) -> str:
    return os.environ.get(name, "").strip()


def env_text_or_default(name: str, default: str) -> str:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip() or default


def provider_order(providers: list[ProviderConfig]) -> list[str]:
    return [provider.id for provider in providers if provider.enabled]


def env_providers() -> list[ProviderConfig]:
    providers: list[ProviderConfig] = []
    for provider_type in ENV_PROVIDER_FIELDS:
        provider = env_provider(provider_type)
        if provider:
            providers.append(provider)
    return providers


def env_provider(provider_type: str) -> ProviderConfig | None:
    spec = PROVIDER_TYPES.get(provider_type, {})
    config, has_explicit_value = env_provider_config(provider_type, spec)
    required = provider_required_fields(spec)
    if not env_provider_is_complete(provider_type, config, has_explicit_value, required):
        return None

    return ProviderConfig(
        id=ENV_PROVIDER_IDS[provider_type],
        type=provider_type,
        name=str(spec.get("label") or provider_type),
        enabled=True,
        config=config,
    )


def env_provider_config(provider_type: str, spec: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    field_envs = ENV_PROVIDER_FIELDS[provider_type]
    config: dict[str, Any] = {}
    has_explicit_value = False

    for field in spec.get("fields", []):
        field_name = str(field["name"])
        value = env_text(field_envs.get(field_name, ""))
        if value:
            config[field_name] = value
            has_explicit_value = True
        elif "default" in field:
            config[field_name] = field["default"]

    return config, has_explicit_value


def provider_required_fields(spec: dict[str, Any]) -> list[str]:
    return [
        str(field["name"])
        for field in spec.get("fields", [])
        if field.get("required")
    ]


def env_provider_is_complete(
    provider_type: str, config: dict[str, Any], has_explicit_value: bool, required: list[str]
) -> bool:
    if provider_type == "wecom_bot":
        return bool(config.get("webhook") or config.get("key"))

    return has_explicit_value and all(str(config.get(name, "")).strip() for name in required)


def legacy_serverchan_provider(sendkey: str) -> ProviderConfig | None:
    sendkey = str(sendkey or "").strip()
    if not sendkey:
        return None
    return ProviderConfig(
        id="serverchan-default",
        type="serverchan",
        name="Server 酱",
        enabled=True,
        config={"sendkey": sendkey},
    )


def parse_providers(
    data: dict[str, Any],
    *,
    base_providers: list[ProviderConfig],
    keep_blank_secrets: bool,
) -> list[ProviderConfig]:
    raw_providers = data.get("providers")
    if not isinstance(raw_providers, list):
        legacy = legacy_serverchan_provider(data.get("serverchan_sendkey"))
        if legacy:
            return [legacy]
        return list(base_providers)

    previous = {provider.id: provider for provider in base_providers}
    providers: list[ProviderConfig] = []
    for item in raw_providers:
        if not isinstance(item, dict):
            continue
        provider = ProviderConfig.from_mapping(item)
        old = previous.get(provider.id)
        config = {
            key: value
            for key, value in dict(provider.config).items()
            if not str(key).startswith("has_")
        }
        if keep_blank_secrets and old:
            for field_name in provider_secret_fields(provider.type):
                if str(config.get(field_name, "")).strip() == "":
                    old_value = old.config.get(field_name)
                    if old_value not in (None, ""):
                        config[field_name] = old_value

        for field in PROVIDER_TYPES.get(provider.type, {}).get("fields", []):
            field_name = str(field["name"])
            if field_name not in config and "default" in field:
                config[field_name] = field["default"]

        providers.append(
            ProviderConfig(
                id=provider.id,
                type=provider.type,
                name=provider.name,
                enabled=provider.enabled,
                config=config,
            )
        )
    return providers
