from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

import requests

try:
    from .helpers import FakeResponse, FakeSession
except ImportError:
    from helpers import FakeResponse, FakeSession

from roco_serverchan_notifier.push_models import NotificationMessage, ProviderConfig
from roco_serverchan_notifier.push_provider_auth import _WECOM_TOKEN_CACHE, feishu_sign
from roco_serverchan_notifier.push_provider_senders import feishu_bot
from roco_serverchan_notifier.push_providers import send_provider


class ScriptedSession(FakeSession):
    def _next(self):
        if not self.responses:
            raise AssertionError("Unexpected HTTP request")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class InvalidJsonResponse(FakeResponse):
    def json(self):
        raise ValueError("Invalid JSON")


class ImageSenderTests(unittest.TestCase):
    def setUp(self):
        self.image = b"\x89PNG\r\n\x1a\nimage-bytes"
        self.message = NotificationMessage("Title_[", "Body * @everyone", "**Details**", self.image)
        self.providers = {
            "telegram": ProviderConfig(
                "tg", "telegram", "Telegram", True,
                {"bot_token": "bot-token", "chat_id": "-123"},
            ),
            "discord": ProviderConfig(
                "dc", "discord", "Discord", True,
                {"webhook": "https://discord.com/api/webhooks/123/webhook-secret?thread_id=42"},
            ),
            "feishu_bot": ProviderConfig(
                "fs", "feishu_bot", "Feishu", True,
                {"webhook": "https://open.feishu.cn/open-apis/bot/v2/hook/webhook-secret",
                 "secret": "signing-secret"},
            ),
            "wecomchan": ProviderConfig(
                "wc", "wecomchan", "WeCom", True,
                {"corpid": "corp", "secret": "corp-secret", "agentid": "1001", "touser": "alice"},
            ),
        }
        feishu_bot._token_cache.clear()
        _WECOM_TOKEN_CACHE.clear()
        self.addCleanup(feishu_bot._token_cache.clear)
        self.addCleanup(_WECOM_TOKEN_CACHE.clear)
        self.enterContext(patch.dict(os.environ, {"FEISHU_APP_ID": "app-one", "FEISHU_APP_SECRET": "app-secret"}))
        # Image delivery must not need a writable /data directory or write any files.
        self.mkdir = self.enterContext(patch("pathlib.Path.mkdir", side_effect=PermissionError("read-only")))
        self.write_bytes = self.enterContext(patch("pathlib.Path.write_bytes", side_effect=PermissionError("read-only")))

    def send(self, provider_type, responses, message=None):
        session = ScriptedSession(responses)
        result = send_provider(
            self.providers[provider_type], message or self.message, session=session, timeout=7,
        )
        return result, session.calls

    def assert_upload(self, call, field):
        filename, content, content_type = call["kwargs"]["files"][field]
        self.assertTrue(filename.endswith(".png"))
        self.assertEqual(content_type, "image/png")
        self.assertEqual(content if isinstance(content, bytes) else content.getvalue(), self.image)
        self.assertEqual(call["timeout"], 7)

    def assert_text_payload(self, provider_type, call):
        payload = call["json"]
        if provider_type == "telegram":
            self.assertEqual(payload, {"chat_id": "-123", "text": "Title_[\n\n**Details**"})
            self.assertTrue(call["url"].endswith("/sendMessage"))
        elif provider_type == "discord":
            self.assertEqual(payload, {"content": "Title_[\n\n**Details**", "allowed_mentions": {"parse": []}})
        elif provider_type == "feishu_bot":
            expected = {
                "msg_type": "post",
                "content": {"post": {"zh_cn": {
                    "title": "Title_[",
                    "content": [[{"tag": "text", "text": "Body * @everyone\n\n**Details**"}]],
                }}},
            }
            self.assertEqual({key: value for key, value in payload.items() if key not in ("timestamp", "sign")}, expected)
            self.assertEqual(payload["sign"], feishu_sign("signing-secret", payload["timestamp"]))
        else:
            self.assertEqual(payload, {
                "touser": "alice", "msgtype": "text", "agentid": 1001,
                "text": {"content": "Title_[\n\nBody * @everyone\n\n**Details**"}, "safe": 0,
            })
        self.assertEqual(call["timeout"], 7)
        self.assertNotIn("files", call["kwargs"])

    def success_response(self, provider_type):
        if provider_type == "telegram":
            return FakeResponse({"ok": True})
        return FakeResponse({"code": 0, "errcode": 0})

    def image_prelude(self, provider_type):
        if provider_type == "feishu_bot":
            return [
                FakeResponse({"code": 0, "tenant_access_token": "tenant-token", "expire": 7200}),
                FakeResponse({"code": 0, "data": {"image_key": "image-key"}}),
            ]
        if provider_type == "wecomchan":
            return [
                FakeResponse({"errcode": 0, "access_token": "corp-token", "expires_in": 7200}),
                FakeResponse({"errcode": 0, "media_id": "media-id"}),
            ]
        return []

    def test_no_image_preserves_all_default_payloads(self):
        for provider_type in self.providers:
            with self.subTest(provider=provider_type):
                responses = self.image_prelude(provider_type)[:1] if provider_type == "wecomchan" else []
                responses.append(self.success_response(provider_type))
                message = NotificationMessage(self.message.title, self.message.body, self.message.markdown)
                result, calls = self.send(provider_type, responses, message)
                self.assertTrue(result.success, result.message)
                self.assertEqual(len(calls), 2 if provider_type == "wecomchan" else 1)
                self.assert_text_payload(provider_type, calls[-1])

    def test_empty_image_uses_text_path(self):
        for provider_type in self.providers:
            with self.subTest(provider=provider_type):
                responses = self.image_prelude(provider_type)[:1] if provider_type == "wecomchan" else []
                responses.append(self.success_response(provider_type))
                message = NotificationMessage(self.message.title, self.message.body, self.message.markdown, b"")
                result, calls = self.send(provider_type, responses, message)
                self.assertTrue(result.success, result.message)
                self.assert_text_payload(provider_type, calls[-1])

    def test_telegram_photo_uses_plain_caption_and_multipart(self):
        result, calls = self.send("telegram", [FakeResponse({"ok": True})])
        self.assertTrue(result.success, result.message)
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0]["url"].endswith("/sendPhoto"))
        self.assertEqual(calls[0]["data"], {"chat_id": "-123", "caption": "Title_[\n\nBody * @everyone"})
        self.assert_upload(calls[0], "photo")

    def test_telegram_caption_is_limited(self):
        message = NotificationMessage("Title", "x" * 1500, "Details", self.image)
        result, calls = self.send("telegram", [FakeResponse({"ok": True})], message)
        self.assertTrue(result.success, result.message)
        self.assertEqual(len(calls[0]["data"]["caption"]), 1024)
        self.assertTrue(calls[0]["data"]["caption"].endswith("..."))

    def test_discord_multipart_preserves_allowed_mentions_in_payload_json(self):
        result, calls = self.send("discord", [FakeResponse({"id": "123"})])
        self.assertTrue(result.success, result.message)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["url"], self.providers["discord"].config["webhook"] + "&wait=true")
        self.assertEqual(set(calls[0]["data"]), {"payload_json"})
        self.assertEqual(json.loads(calls[0]["data"]["payload_json"]), {
            "content": "Title_[\n\nBody * @everyone", "allowed_mentions": {"parse": []},
        })
        self.assert_upload(calls[0], "files[0]")

    def test_feishu_uploads_bytes_without_filesystem_access(self):
        result, calls = self.send("feishu_bot", self.image_prelude("feishu_bot") + [FakeResponse({"code": 0})])
        self.assertTrue(result.success, result.message)
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[0]["url"], "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal")
        self.assertEqual(calls[0]["json"], {"app_id": "app-one", "app_secret": "app-secret"})
        self.assertEqual(calls[1]["url"], "https://open.feishu.cn/open-apis/im/v1/images")
        self.assertEqual(calls[1]["headers"], {"Authorization": "Bearer tenant-token"})
        self.assertEqual(calls[1]["data"], {"image_type": "message"})
        self.assert_upload(calls[1], "image")
        self.assertEqual(calls[2]["json"]["msg_type"], "image")
        self.assertEqual(calls[2]["json"]["content"], {"image_key": "image-key"})
        payload = calls[2]["json"]
        self.assertEqual(payload["sign"], feishu_sign("signing-secret", payload["timestamp"]))
        self.mkdir.assert_not_called()
        self.write_bytes.assert_not_called()

    def test_wecom_application_uploads_media_then_sends_media_id(self):
        result, calls = self.send("wecomchan", self.image_prelude("wecomchan") + [FakeResponse({"errcode": 0})])
        self.assertTrue(result.success, result.message)
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[1]["url"], "https://qyapi.weixin.qq.com/cgi-bin/media/upload?access_token=corp-token&type=image")
        self.assert_upload(calls[1], "media")
        self.assertEqual(calls[2]["url"], "https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=corp-token")
        self.assertEqual(calls[2]["json"], {
            "touser": "alice", "msgtype": "image", "agentid": 1001,
            "image": {"media_id": "media-id"}, "safe": 0,
        })

    def test_image_send_http_failure_falls_back_to_original_text(self):
        for provider_type in self.providers:
            with self.subTest(provider=provider_type):
                responses = self.image_prelude(provider_type) + [
                    FakeResponse({"ok": False, "code": 400, "errcode": 400}, status_code=400),
                    self.success_response(provider_type),
                ]
                result, calls = self.send(provider_type, responses)
                self.assertTrue(result.success, result.message)
                self.assertEqual(len(calls), 4 if provider_type in ("feishu_bot", "wecomchan") else 2)
                self.assert_text_payload(provider_type, calls[-1])

    def test_image_send_api_failure_falls_back_to_original_text(self):
        for provider_type in ("telegram", "feishu_bot", "wecomchan"):
            with self.subTest(provider=provider_type):
                responses = self.image_prelude(provider_type) + [
                    FakeResponse({"ok": False, "code": 400, "errcode": 400}),
                    self.success_response(provider_type),
                ]
                result, calls = self.send(provider_type, responses)
                self.assertTrue(result.success, result.message)
                self.assert_text_payload(provider_type, calls[-1])

    def test_image_send_network_failure_falls_back_to_original_text(self):
        for provider_type in self.providers:
            with self.subTest(provider=provider_type):
                responses = self.image_prelude(provider_type) + [
                    requests.Timeout("image request timed out"), self.success_response(provider_type),
                ]
                result, calls = self.send(provider_type, responses)
                self.assertTrue(result.success, result.message)
                self.assert_text_payload(provider_type, calls[-1])

    def test_failed_text_fallback_returns_failure_with_redaction(self):
        for provider_type in self.providers:
            with self.subTest(provider=provider_type):
                responses = self.image_prelude(provider_type) + [
                    FakeResponse({"ok": False, "code": 400, "errcode": 400}, status_code=400),
                    FakeResponse({}, status_code=503, text="bot-token corp-secret access_token=private-token webhook=private-hook"),
                ]
                result, calls = self.send(provider_type, responses)
                self.assertFalse(result.success)
                self.assertEqual(result.status_code, 503)
                self.assertNotIn("private-token", result.message)
                self.assertNotIn("private-hook", result.message)
                if provider_type == "telegram":
                    self.assertNotIn("bot-token", result.message)
                if provider_type == "wecomchan":
                    self.assertNotIn("corp-secret", result.message)
                self.assert_text_payload(provider_type, calls[-1])

    def test_upload_failures_fall_back_to_text(self):
        failures = [
            FakeResponse({"code": 234006, "errcode": 40005}),
            FakeResponse({"code": 0, "errcode": 0, "media_id": "bad", "data": {"image_key": "bad"}}, status_code=503),
            FakeResponse({"code": 0, "errcode": 0}),
            FakeResponse({"code": 0, "errcode": 0, "media_id": 123, "data": {"image_key": 123}}),
            FakeResponse([]), InvalidJsonResponse(), requests.ConnectionError("upload failed"),
        ]
        for provider_type in ("feishu_bot", "wecomchan"):
            for failure in failures:
                with self.subTest(provider=provider_type, failure=repr(failure)):
                    feishu_bot._token_cache.clear()
                    _WECOM_TOKEN_CACHE.clear()
                    responses = self.image_prelude(provider_type)[:1] + [failure, self.success_response(provider_type)]
                    result, calls = self.send(provider_type, responses)
                    self.assertTrue(result.success, result.message)
                    self.assertEqual(len(calls), 3)
                    self.assert_text_payload(provider_type, calls[-1])

    def test_feishu_token_failures_fall_back_to_text(self):
        failures = [
            FakeResponse({"code": 999}),
            FakeResponse({"code": 0, "tenant_access_token": "bad"}, status_code=503),
            FakeResponse({"code": 0}),
            FakeResponse({"code": 0, "tenant_access_token": 123}),
            FakeResponse([]), InvalidJsonResponse(), requests.Timeout("auth failed"),
        ]
        for failure in failures:
            with self.subTest(failure=repr(failure)):
                feishu_bot._token_cache.clear()
                result, calls = self.send("feishu_bot", [failure, FakeResponse({"code": 0})])
                self.assertTrue(result.success, result.message)
                self.assertEqual(len(calls), 2)
                self.assert_text_payload("feishu_bot", calls[-1])

    def test_feishu_without_app_credentials_falls_back_to_post(self):
        with patch.dict(os.environ, {"FEISHU_APP_ID": "", "FEISHU_APP_SECRET": ""}):
            result, calls = self.send("feishu_bot", [FakeResponse({"code": 0})])
        self.assertTrue(result.success, result.message)
        self.assertEqual(len(calls), 1)
        self.assert_text_payload("feishu_bot", calls[0])

    def test_feishu_unsigned_default_post_omits_signature(self):
        self.providers["feishu_bot"].config.pop("secret")
        message = NotificationMessage("Title", "Body", "Markdown")
        result, calls = self.send("feishu_bot", [FakeResponse({"code": 0})], message)
        self.assertTrue(result.success, result.message)
        self.assertEqual(calls[0]["json"], {
            "msg_type": "post", "content": {"post": {"zh_cn": {
                "title": "Title", "content": [[{"tag": "text", "text": "Body\n\nMarkdown"}]],
            }}},
        })

    def test_feishu_token_cache_tracks_app_id_and_secret(self):
        session = ScriptedSession([
            FakeResponse({"code": 0, "tenant_access_token": "token-one", "expire": 7200}),
            FakeResponse({"code": 0, "tenant_access_token": "token-two", "expire": 7200}),
            FakeResponse({"code": 0, "tenant_access_token": "token-three", "expire": 7200}),
        ])
        self.assertEqual(feishu_bot._get_tenant_token(session, 7), "token-one")
        self.assertEqual(feishu_bot._get_tenant_token(session, 7), "token-one")
        with patch.dict(os.environ, {"FEISHU_APP_ID": "app-two"}):
            self.assertEqual(feishu_bot._get_tenant_token(session, 7), "token-two")
        with patch.dict(os.environ, {"FEISHU_APP_SECRET": "rotated-secret"}):
            self.assertEqual(feishu_bot._get_tenant_token(session, 7), "token-three")
        self.assertEqual(feishu_bot._get_tenant_token(session, 7), "token-one")
        self.assertEqual(len(session.calls), 3)

    def test_feishu_removed_credentials_do_not_reuse_cached_token(self):
        session = ScriptedSession([FakeResponse({"code": 0, "tenant_access_token": "token-one", "expire": 7200})])
        self.assertEqual(feishu_bot._get_tenant_token(session, 7), "token-one")
        for field in ("FEISHU_APP_ID", "FEISHU_APP_SECRET"):
            with self.subTest(field=field), patch.dict(os.environ, {field: ""}):
                self.assertIsNone(feishu_bot._get_tenant_token(session, 7))
        self.assertEqual(len(session.calls), 1)

    def test_feishu_token_cache_refreshes_near_expiry(self):
        session = ScriptedSession([
            FakeResponse({"code": 0, "tenant_access_token": "old", "expire": 7200}),
            FakeResponse({"code": 0, "tenant_access_token": "new", "expire": 7200}),
        ])
        with patch.object(feishu_bot.time, "time", return_value=1000):
            self.assertEqual(feishu_bot._get_tenant_token(session, 7), "old")
        with patch.object(feishu_bot.time, "time", return_value=8090):
            self.assertEqual(feishu_bot._get_tenant_token(session, 7), "new")
        self.assertEqual(len(session.calls), 2)


if __name__ == "__main__":
    unittest.main()
