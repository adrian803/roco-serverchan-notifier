from __future__ import annotations

import unittest
from unittest.mock import patch

try:
    from .helpers import RocoTestCase
except ImportError:
    from helpers import RocoTestCase

from roco_serverchan_notifier import app as app_module
from roco_serverchan_notifier.push import DeliveryReport, PushResult


class AppTests(RocoTestCase):
    def test_run_once_returns_no_report_when_empty_is_skipped(self):
        settings = self.make_settings(notify_empty=False)

        with patch.object(app_module, "fetch_merchant_data", return_value={"merchantActivities": []}):
            result = app_module.run_once(settings)

        self.assertEqual(result.exit_code, 0)
        self.assertIsNone(result.report)

    def test_run_once_returns_delivery_report(self):
        settings = self.make_settings(notify_empty=True)
        report = DeliveryReport(True, "all", [PushResult("p1", "通道", "serverchan", True, "ok")])
        raw_data = {
            "merchantActivities": [
                {
                    "name": "远行商人",
                    "get_props": [{"name": "咕噜球"}],
                    "get_pets": [],
                }
            ]
        }

        with patch.object(app_module, "fetch_merchant_data", return_value=raw_data), patch.object(
            app_module,
            "send_delivery",
            return_value=report,
        ):
            result = app_module.run_once(settings)

        self.assertEqual(result.exit_code, 0)
        self.assertIs(result.report, report)

    def test_push_uses_configured_timeout(self):
        settings = self.make_settings(http_timeout=42, notify_empty=True)
        raw_data = {
            "merchantActivities": [
                {
                    "name": "远行商人",
                    "get_props": [{"name": "咕噜球"}],
                    "get_pets": [],
                }
            ]
        }

        with patch.object(app_module, "fetch_merchant_data", return_value=raw_data), patch.object(
            app_module,
            "send_delivery",
            return_value=DeliveryReport(True, "all", []),
        ) as send_mock:
            exit_code = app_module.run_once(settings)

        self.assertEqual(exit_code, 0)
        self.assertEqual(send_mock.call_args.kwargs["options"].timeout, 42)


if __name__ == "__main__":
    unittest.main()
