from __future__ import annotations

import unittest

try:
    from .helpers import FakeResponse, FakeSession
except ImportError:
    from helpers import FakeResponse, FakeSession

from roco_serverchan_notifier.push_http import JsonPostRequest, post_json
from roco_serverchan_notifier.push_models import ProviderConfig


class PushHttpTests(unittest.TestCase):
    def test_post_json_uses_success_codes_and_redacts_http_error_text(self):
        provider = ProviderConfig(
            id="p1",
            type="pushplus",
            name="PushPlus",
            enabled=True,
            config={"token": "secret-token"},
        )
        session = FakeSession([FakeResponse({}, status_code=500, text="bad token=abc secret-token")])

        result = post_json(
            JsonPostRequest(
                provider=provider,
                session=session,
                url="https://example.com/send",
                payload={"message": "hello"},
                timeout=30,
                success_codes={200, "200", 0, "0"},
            )
        )

        self.assertFalse(result.success)
        self.assertEqual(result.status_code, 500)
        self.assertEqual(result.message, "bad token=[已脱敏] [已脱敏]")

    def test_post_json_supports_telegram_ok_responses(self):
        provider = ProviderConfig(
            id="telegram-env",
            type="telegram",
            name="Telegram",
            enabled=True,
            config={"bot_token": "bot-secret", "chat_id": "-100123"},
        )
        session = FakeSession([FakeResponse({"ok": True, "result": {"message_id": 1}}, text="sent")])

        result = post_json(
            JsonPostRequest(
                provider=provider,
                session=session,
                url="https://api.telegram.org/botbot-secret/sendMessage",
                payload={"chat_id": "-100123", "text": "hello"},
                timeout=30,
            )
        )

        self.assertTrue(result.success)

    def test_post_json_uses_telegram_description_for_http_errors(self):
        provider = ProviderConfig(
            id="telegram-env",
            type="telegram",
            name="Telegram",
            enabled=True,
            config={"bot_token": "bot-secret", "chat_id": "-100123"},
        )
        session = FakeSession(
            [
                FakeResponse(
                    {"ok": False, "description": "Bad Request: chat not found"},
                    status_code=400,
                    text='{"ok":false,"description":"Bad Request: chat not found"}',
                )
            ]
        )

        result = post_json(
            JsonPostRequest(
                provider=provider,
                session=session,
                url="https://api.telegram.org/botbot-secret/sendMessage",
                payload={"chat_id": "-100123", "text": "hello"},
                timeout=30,
            )
        )

        self.assertFalse(result.success)
        self.assertEqual(result.status_code, 400)
        self.assertEqual(result.message, "Bad Request: chat not found")


if __name__ == "__main__":
    unittest.main()
