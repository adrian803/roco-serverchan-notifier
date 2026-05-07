from __future__ import annotations

import importlib
import unittest

try:
    from .helpers import FakeResponse, FakeSession, RocoTestCase
except ImportError:
    from helpers import FakeResponse, FakeSession, RocoTestCase

from roco_serverchan_notifier.provider_specs import PROVIDER_TYPES
from roco_serverchan_notifier.push import (
    PROVIDER_SENDERS,
    NotificationMessage,
    ProviderConfig,
    _WECOM_TOKEN_CACHE,
    send_provider,
)


class PushProviderSenderTests(RocoTestCase):
    def test_push_provider_senders_are_split_by_provider_modules(self):
        import importlib.util

        registry = importlib.import_module("roco_serverchan_notifier.push_provider_senders.registry")
        serverchan = importlib.import_module("roco_serverchan_notifier.push_provider_senders.serverchan")
        pushplus = importlib.import_module("roco_serverchan_notifier.push_provider_senders.pushplus")
        telegram = importlib.import_module("roco_serverchan_notifier.push_provider_senders.telegram")
        discord = importlib.import_module("roco_serverchan_notifier.push_provider_senders.discord")
        wecomchan = importlib.import_module("roco_serverchan_notifier.push_provider_senders.wecomchan")
        wecom_bot = importlib.import_module("roco_serverchan_notifier.push_provider_senders.wecom_bot")
        wxpusher = importlib.import_module("roco_serverchan_notifier.push_provider_senders.wxpusher")
        bark = importlib.import_module("roco_serverchan_notifier.push_provider_senders.bark")
        dingtalk_bot = importlib.import_module("roco_serverchan_notifier.push_provider_senders.dingtalk_bot")
        feishu_bot = importlib.import_module("roco_serverchan_notifier.push_provider_senders.feishu_bot")
        ntfy = importlib.import_module("roco_serverchan_notifier.push_provider_senders.ntfy")
        gotify = importlib.import_module("roco_serverchan_notifier.push_provider_senders.gotify")

        self.assertEqual(set(registry.PROVIDER_SENDERS), set(PROVIDER_SENDERS))
        self.assertEqual(set(registry.PROVIDER_SENDERS), set(PROVIDER_TYPES))
        self.assertIs(registry.PROVIDER_SENDERS["serverchan"], serverchan.send_serverchan)
        self.assertIs(registry.PROVIDER_SENDERS["pushplus"], pushplus.send_pushplus)
        self.assertIs(registry.PROVIDER_SENDERS["telegram"], telegram.send_telegram)
        self.assertIs(registry.PROVIDER_SENDERS["discord"], discord.send_discord)
        self.assertIs(registry.PROVIDER_SENDERS["wecomchan"], wecomchan.send_wecomchan)
        self.assertIs(registry.PROVIDER_SENDERS["wecom_bot"], wecom_bot.send_wecom_bot)
        self.assertIs(registry.PROVIDER_SENDERS["wxpusher"], wxpusher.send_wxpusher)
        self.assertIs(registry.PROVIDER_SENDERS["bark"], bark.send_bark)
        self.assertIs(registry.PROVIDER_SENDERS["dingtalk_bot"], dingtalk_bot.send_dingtalk_bot)
        self.assertIs(registry.PROVIDER_SENDERS["feishu_bot"], feishu_bot.send_feishu_bot)
        self.assertIs(registry.PROVIDER_SENDERS["ntfy"], ntfy.send_ntfy)
        self.assertIs(registry.PROVIDER_SENDERS["gotify"], gotify.send_gotify)
        self.assertIsNone(importlib.util.find_spec("roco_serverchan_notifier.push_provider_senders.token"))
        self.assertIsNone(importlib.util.find_spec("roco_serverchan_notifier.push_provider_senders.webhook"))
        self.assertIsNone(importlib.util.find_spec("roco_serverchan_notifier.push_provider_senders.chat"))
        self.assertIsNone(importlib.util.find_spec("roco_serverchan_notifier.push_provider_senders.wecom"))

    def test_serverchan_provider_posts_expected_payload(self):
        provider = ProviderConfig("p1", "serverchan", "Server 酱", True, {"sendkey": "SCT123"})
        message = NotificationMessage("标题", "摘要", "正文")
        session = FakeSession([FakeResponse({"code": 0})])

        result = send_provider(provider, message, session=session, timeout=7)

        self.assertTrue(result.success)
        self.assertEqual(session.calls[0]["url"], "https://sctapi.ftqq.com/SCT123.send")
        self.assertEqual(session.calls[0]["data"], {"title": "标题", "desp": "正文"})
        self.assertEqual(session.calls[0]["timeout"], 7)

    def test_serverchan_success_message_redacts_readkey(self):
        provider = ProviderConfig("p1", "serverchan", "Server 酱", True, {"sendkey": "SCT123"})
        message = NotificationMessage("标题", "摘要", "正文")
        session = FakeSession(
            [
                FakeResponse(
                    {
                        "code": 0,
                        "message": "",
                        "data": {
                            "pushid": "34197705",
                            "readkey": "SCTE0rv9wOx1IkO",
                            "error": "SUCCESS",
                        },
                    }
                )
            ]
        )

        result = send_provider(provider, message, session=session)

        self.assertTrue(result.success)
        self.assertIn("[已脱敏]", result.message)
        self.assertNotIn("SCTE0rv9wOx1IkO", result.message)

    def test_push_error_message_redacts_provider_secrets(self):
        class BrokenSession:
            def post(self, url, **kwargs):
                raise RuntimeError(f"failed POST {url}?access_token=LIVE_TOKEN&token=abc")

        provider = ProviderConfig("p1", "serverchan", "Server 酱", True, {"sendkey": "SCT_SECRET"})

        result = send_provider(
            provider,
            NotificationMessage("标题", "摘要", "正文"),
            session=BrokenSession(),
        )

        self.assertFalse(result.success)
        self.assertIn("[已脱敏]", result.message)
        self.assertNotIn("SCT_SECRET", result.message)
        self.assertNotIn("LIVE_TOKEN", result.message)
        self.assertNotIn("token=abc", result.message)

    def test_http_error_message_redacts_provider_secrets(self):
        provider = ProviderConfig(
            "p1",
            "gotify",
            "Gotify",
            True,
            {"base_url": "https://gotify.example", "app_token": "APP_TOKEN"},
        )
        session = FakeSession([FakeResponse({}, status_code=500, text="bad token=abc APP_TOKEN")])

        result = send_provider(provider, NotificationMessage("标题", "摘要", "正文"), session=session)

        self.assertFalse(result.success)
        self.assertNotIn("APP_TOKEN", result.message)
        self.assertNotIn("token=abc", result.message)

    def test_pushplus_provider_posts_expected_payload(self):
        provider = ProviderConfig("p1", "pushplus", "PushPlus", True, {"token": "tok", "topic": "ops"})
        message = NotificationMessage("标题", "摘要", "正文")
        session = FakeSession([FakeResponse({"code": 200})])

        result = send_provider(provider, message, session=session)

        self.assertTrue(result.success)
        self.assertEqual(session.calls[0]["url"], "https://www.pushplus.plus/send")
        self.assertEqual(session.calls[0]["json"]["token"], "tok")
        self.assertEqual(session.calls[0]["json"]["template"], "markdown")
        self.assertEqual(session.calls[0]["json"]["topic"], "ops")

    def test_telegram_provider_posts_expected_payload(self):
        provider = ProviderConfig(
            "telegram-env",
            "telegram",
            "Telegram",
            True,
            {"bot_token": "bot-token", "chat_id": "-1001234567890"},
        )
        message = NotificationMessage("标题", "摘要", "正文")
        session = FakeSession([FakeResponse({"ok": True, "result": {"message_id": 1}})])

        result = send_provider(provider, message, session=session)

        self.assertTrue(result.success)
        self.assertEqual(
            session.calls[0]["url"],
            "https://api.telegram.org/botbot-token/sendMessage",
        )
        self.assertEqual(
            session.calls[0]["json"],
            {"chat_id": "-1001234567890", "text": "标题\n\n正文"},
        )

    def test_discord_provider_posts_expected_payload(self):
        provider = ProviderConfig(
            "discord-env",
            "discord",
            "Discord",
            True,
            {"webhook": "https://discord.com/api/webhooks/123/secret"},
        )
        message = NotificationMessage("标题", "摘要", "正文")
        session = FakeSession([FakeResponse({"id": "1"}, status_code=200, text='{"id":"1"}')])

        result = send_provider(provider, message, session=session)

        self.assertTrue(result.success)
        self.assertEqual(
            session.calls[0]["url"],
            "https://discord.com/api/webhooks/123/secret?wait=true",
        )
        self.assertEqual(
            session.calls[0]["json"],
            {"content": "标题\n\n正文", "allowed_mentions": {"parse": []}},
        )

    def test_telegram_error_message_redacts_bot_token(self):
        class BrokenSession:
            def post(self, url, **kwargs):
                raise RuntimeError(f"failed POST {url}?token=bot-token")

        provider = ProviderConfig(
            "telegram-env",
            "telegram",
            "Telegram",
            True,
            {"bot_token": "bot-token", "chat_id": "-1001234567890"},
        )

        result = send_provider(
            provider,
            NotificationMessage("标题", "摘要", "正文"),
            session=BrokenSession(),
        )

        self.assertFalse(result.success)
        self.assertIn("[已脱敏]", result.message)
        self.assertNotIn("bot-token", result.message)

    def test_discord_error_message_redacts_webhook(self):
        provider = ProviderConfig(
            "discord-env",
            "discord",
            "Discord",
            True,
            {"webhook": "https://discord.com/api/webhooks/123/secret"},
        )
        session = FakeSession(
            [
                FakeResponse(
                    {},
                    status_code=500,
                    text="webhook=https://discord.com/api/webhooks/123/secret",
                )
            ]
        )

        result = send_provider(provider, NotificationMessage("标题", "摘要", "正文"), session=session)

        self.assertFalse(result.success)
        self.assertNotIn("https://discord.com/api/webhooks/123/secret", result.message)
        self.assertIn("[已脱敏]", result.message)

    def test_sender_required_validation_accepts_manifest_defaults(self):
        provider = ProviderConfig("p1", "bark", "Bark", True, {"device_key": "device-key"})
        message = NotificationMessage("标题", "摘要", "正文")
        session = FakeSession([FakeResponse({"code": 0})])

        result = send_provider(provider, message, session=session)

        self.assertTrue(result.success)
        self.assertEqual(session.calls[0]["url"], "https://api.day.app/device-key")
        self.assertEqual(session.calls[0]["json"]["group"], "洛克王国")

    def test_wecomchan_token_is_cached(self):
        _WECOM_TOKEN_CACHE.clear()
        provider = ProviderConfig(
            "p1",
            "wecomchan",
            "企微应用",
            True,
            {"corpid": "corp", "secret": "sec", "agentid": "1001", "touser": "@all"},
        )
        message = NotificationMessage("标题", "摘要", "正文")
        session = FakeSession(
            [
                FakeResponse({"errcode": 0, "access_token": "token", "expires_in": 7200}),
                FakeResponse({"errcode": 0}),
                FakeResponse({"errcode": 0}),
            ]
        )

        first = send_provider(provider, message, session=session)
        second = send_provider(provider, message, session=session)

        self.assertTrue(first.success)
        self.assertTrue(second.success)
        self.assertEqual(sum(1 for call in session.calls if call["method"] == "GET"), 1)
        self.assertEqual(sum(1 for call in session.calls if call["method"] == "POST"), 2)


if __name__ == "__main__":
    unittest.main()
