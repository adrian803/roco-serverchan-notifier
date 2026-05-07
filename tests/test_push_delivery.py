from __future__ import annotations

import threading
import unittest
from unittest.mock import patch

try:
    from .helpers import FakeResponse, FakeSession, RocoTestCase, SessionFactory, load_cross_runtime_fixture
except ImportError:
    from helpers import FakeResponse, FakeSession, RocoTestCase, SessionFactory, load_cross_runtime_fixture

from roco_serverchan_notifier import push as push_module
from roco_serverchan_notifier import push_delivery as push_delivery_module
from roco_serverchan_notifier.push import DeliveryReport, NotificationMessage, ProviderConfig, PushResult, send_delivery


class PushDeliveryTests(RocoTestCase):
    def test_delivery_all_succeeds_when_at_least_one_provider_succeeds(self):
        providers = [
            ProviderConfig("bad", "serverchan", "Bad", True, {"sendkey": "bad"}),
            ProviderConfig("ok", "serverchan", "Ok", True, {"sendkey": "ok"}),
        ]
        message = NotificationMessage("标题", "摘要", "正文")
        factory = SessionFactory(
            [[FakeResponse({"code": 1, "message": "bad"})], [FakeResponse({"code": 0})]]
        )

        with patch.object(push_module.requests, "Session", factory):
            report = send_delivery(providers, message, mode="all")

        self.assertTrue(report.success)
        self.assertEqual(len(report.results), 2)

    def test_delivery_all_does_not_share_passed_session_between_threads(self):
        providers = [
            ProviderConfig("a", "serverchan", "A", True, {"sendkey": "a"}),
            ProviderConfig("b", "serverchan", "B", True, {"sendkey": "b"}),
        ]
        shared_session = FakeSession([FakeResponse({"code": 0}), FakeResponse({"code": 0})])
        seen_sessions = []

        def fake_send_provider(provider, message, *, session=None, timeout=10):
            seen_sessions.append(session)
            return PushResult(provider.id, provider.name, provider.type, True, "ok")

        factory = SessionFactory()
        with patch.object(push_module.requests, "Session", factory), patch.object(
            push_module,
            "send_provider",
            side_effect=fake_send_provider,
        ):
            report = send_delivery(
                providers,
                NotificationMessage("标题", "摘要", "正文"),
                mode="all",
                session=shared_session,
            )

        self.assertTrue(report.success)
        self.assertEqual(len(seen_sessions), 2)
        self.assertNotIn(shared_session, seen_sessions)
        self.assertEqual(len({id(session) for session in seen_sessions}), 2)

    def test_delivery_all_sends_enabled_providers_concurrently(self):
        providers = [
            ProviderConfig("a", "serverchan", "A", True, {"sendkey": "a"}),
            ProviderConfig("b", "serverchan", "B", True, {"sendkey": "b"}),
        ]
        barrier = threading.Barrier(len(providers))

        def fake_send_provider(provider, message, *, session=None, timeout=10):
            try:
                barrier.wait(timeout=1)
            except threading.BrokenBarrierError as exc:
                raise AssertionError("all mode did not send providers concurrently") from exc
            return PushResult(provider.id, provider.name, provider.type, True, "ok")

        with patch.object(push_module, "send_provider", side_effect=fake_send_provider):
            report = send_delivery(providers, NotificationMessage("标题", "摘要", "正文"), mode="all")

        self.assertTrue(report.success)
        self.assertEqual([result.provider_id for result in report.results], ["a", "b"])

    def test_delivery_all_reuses_module_level_executor(self):
        executor_id_before = id(push_delivery_module._ALL_MODE_EXECUTOR)
        providers = [
            ProviderConfig("a", "serverchan", "A", True, {"sendkey": "a"}),
            ProviderConfig("b", "serverchan", "B", True, {"sendkey": "b"}),
        ]

        with patch.object(push_module, "send_provider", return_value=PushResult("a", "A", "serverchan", True, "ok")):
            send_delivery(providers, NotificationMessage("标题", "摘要", "正文"), mode="all")
            send_delivery(providers, NotificationMessage("标题", "摘要", "正文"), mode="all")

        self.assertEqual(id(push_delivery_module._ALL_MODE_EXECUTOR), executor_id_before)

    def test_delivery_single_uses_selected_provider_only(self):
        providers = [
            ProviderConfig("a", "serverchan", "A", True, {"sendkey": "a"}),
            ProviderConfig("b", "serverchan", "B", True, {"sendkey": "b"}),
        ]
        session = FakeSession([FakeResponse({"code": 0})])

        report = send_delivery(
            providers,
            NotificationMessage("标题", "摘要", "正文"),
            mode="single",
            selected_provider="b",
            session=session,
        )

        self.assertTrue(report.success)
        self.assertEqual(len(report.results), 1)
        self.assertIn("/b.send", session.calls[0]["url"])

    def test_delivery_failover_stops_after_first_success(self):
        providers = [
            ProviderConfig("a", "serverchan", "A", True, {"sendkey": "a"}),
            ProviderConfig("b", "serverchan", "B", True, {"sendkey": "b"}),
            ProviderConfig("c", "serverchan", "C", True, {"sendkey": "c"}),
        ]
        session = FakeSession([FakeResponse({"code": 1}), FakeResponse({"code": 0}), FakeResponse({"code": 0})])

        report = send_delivery(
            providers,
            NotificationMessage("标题", "摘要", "正文"),
            mode="failover",
            failover_order=["a", "b", "c"],
            session=session,
        )

        self.assertTrue(report.success)
        self.assertEqual(len(report.results), 2)
        self.assertEqual(len(session.calls), 2)

    def test_delivery_failover_defaults_to_enabled_provider_order(self):
        providers = [
            ProviderConfig("a", "serverchan", "A", True, {"sendkey": "a"}),
            ProviderConfig("off", "serverchan", "Off", False, {"sendkey": "off"}),
            ProviderConfig("b", "serverchan", "B", True, {"sendkey": "b"}),
        ]
        session = FakeSession([FakeResponse({"code": 1}), FakeResponse({"code": 0})])

        report = send_delivery(
            providers,
            NotificationMessage("标题", "摘要", "正文"),
            mode="failover",
            session=session,
        )

        self.assertTrue(report.success)
        self.assertEqual([result.provider_id for result in report.results], ["a", "b"])
        self.assertEqual(len(session.calls), 2)

    def test_shared_delivery_summary_fixture_matches_python(self):
        fixture = load_cross_runtime_fixture()
        case = fixture["delivery_summary"]
        report_data = case["python_report"]
        results = [PushResult(**item) for item in report_data["results"]]
        report = DeliveryReport(report_data["success"], report_data["mode"], results)

        self.assertEqual(report.summary(), case["expected"])


if __name__ == "__main__":
    unittest.main()
