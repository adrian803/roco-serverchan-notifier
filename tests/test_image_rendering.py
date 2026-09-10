from __future__ import annotations

import importlib.util
import io
import json
import sys
import unittest
from dataclasses import replace
from types import ModuleType
from unittest.mock import Mock, patch, sentinel

try:
    from .helpers import RocoTestCase, make_temp_store
except ImportError:
    from helpers import RocoTestCase, make_temp_store

from roco_serverchan_notifier import app as app_module
from roco_serverchan_notifier.merchant_message import build_notification_message
from roco_serverchan_notifier.push import DeliveryReport
from roco_serverchan_notifier.settings import Settings


class ImageRenderingSettingsTests(RocoTestCase):
    def test_render_image_defaults_to_false(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertIs(Settings.from_env().render_image, False)
            self.assertIs(Settings.from_mapping({}).render_image, False)
        self.assertIs(self.make_settings().render_image, False)

    def test_render_image_environment_values(self):
        cases = {
            "true": True,
            " ON ": True,
            "yes": True,
            "1": True,
            "false": False,
            "off": False,
            "no": False,
            "0": False,
            "": False,
        }
        for value, expected in cases.items():
            with self.subTest(value=value), patch.dict(
                "os.environ", {"RENDER_IMAGE": value}, clear=True
            ):
                self.assertIs(Settings.from_env().render_image, expected)

    def test_mapping_inherits_render_image_from_base(self):
        for enabled in (False, True):
            for data in ({}, {"render_image": None}):
                with self.subTest(enabled=enabled, data=data):
                    base = self.make_settings(render_image=enabled)
                    self.assertIs(Settings.from_mapping(data, base=base).render_image, enabled)

    def test_mapping_coerces_render_image(self):
        cases = (
            (True, True),
            (False, False),
            ("true", True),
            (" ON ", True),
            ("false", False),
            ("off", False),
            ("", False),
            (1, True),
            (0, False),
        )
        for value, expected in cases:
            with self.subTest(value=value):
                base = self.make_settings(render_image=not expected)
                settings = Settings.from_mapping({"render_image": value}, base=base)
                self.assertIs(settings.render_image, expected)

    def test_render_image_to_dict_round_trip(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                original = self.make_settings(
                    render_image=enabled, failover_order=["serverchan-default"]
                )
                payload = original.to_dict()
                self.assertIs(payload["render_image"], enabled)
                loaded = Settings.from_mapping(payload, base=replace(original, render_image=not enabled))
                self.assertEqual(loaded.to_dict(), payload)

    def test_config_store_save_load_preserves_render_image_over_environment(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled), patch.dict(
                "os.environ", {"RENDER_IMAGE": str(not enabled)}, clear=True
            ):
                original = self.make_settings(
                    render_image=enabled, failover_order=["serverchan-default"]
                )
                with make_temp_store(original) as (store, path):
                    self.assertIs(json.loads(path.read_text(encoding="utf-8"))["render_image"], enabled)
                    self.assertEqual(store.load().to_dict(), original.to_dict())

    def test_config_store_update_inherits_and_coerces_render_image(self):
        with patch.dict("os.environ", {}, clear=True), make_temp_store(
            self.make_settings(render_image=True)
        ) as (store, _):
            self.assertIs(store.update({"http_timeout": 42}).render_image, True)
            self.assertIs(store.load().render_image, True)
            self.assertIs(store.update({"render_image": "off"}).render_image, False)
            self.assertIs(store.load().render_image, False)
            self.assertIs(store.update({"render_image": "on"}).render_image, True)
            self.assertIs(store.load().render_image, True)


class ImageRenderingAppTests(RocoTestCase):
    def setUp(self):
        self.processed = {
            "title": "远行商人",
            "products": [{"name": "咕噜球", "time_label": "08:00-12:00"}],
            "round_info": {"current": 1, "total": 4, "countdown": "01:00:00"},
        }
        self.text_message = build_notification_message(self.processed)

    def _run_with_renderer(self, settings, render):
        # Stub the lazy import so app behavior is covered even without Pillow.
        renderer = ModuleType("roco_serverchan_notifier.image_renderer")
        renderer.render_merchant_card = render
        report = DeliveryReport(True, "all", [])
        with (
            patch.dict(sys.modules, {renderer.__name__: renderer}),
            patch.object(app_module.requests, "Session", return_value=sentinel.session),
            patch.object(app_module, "fetch_merchant_data", return_value={}),
            patch.object(app_module, "process_merchant_data", return_value=self.processed),
            patch.object(app_module, "send_delivery", return_value=report) as send,
            patch("sys.stdout", new_callable=io.StringIO),
        ):
            result = app_module.run_once(settings)

        self.assertEqual(result.exit_code, 0)
        self.assertIs(result.report, report)
        send.assert_called_once()
        return send.call_args.args[1]

    def test_run_once_defaults_to_text_without_rendering(self):
        render = Mock()
        message = self._run_with_renderer(self.make_settings(), render)

        render.assert_not_called()
        self.assertEqual(message, self.text_message)
        self.assertIsNone(message.image_data)

    def test_run_once_explicitly_disabled_uses_text_without_rendering(self):
        render = Mock()
        message = self._run_with_renderer(self.make_settings(render_image=False), render)

        render.assert_not_called()
        self.assertEqual(message, self.text_message)

    def test_run_once_enabled_attaches_image_and_preserves_text(self):
        image_data = b"rendered-png"
        render = Mock(return_value=image_data)
        message = self._run_with_renderer(self.make_settings(render_image=True), render)

        render.assert_called_once_with(self.processed)
        self.assertEqual(message, replace(self.text_message, image_data=image_data))

    def test_run_once_failed_render_falls_back_to_text(self):
        render = Mock(side_effect=RuntimeError("render failed"))
        message = self._run_with_renderer(self.make_settings(render_image=True), render)

        render.assert_called_once_with(self.processed)
        self.assertEqual(message, self.text_message)
        self.assertIsNone(message.image_data)


@unittest.skipUnless(importlib.util.find_spec("PIL") is not None, "Pillow is not installed")
class ImageRendererSmokeTests(unittest.TestCase):
    def setUp(self):
        from PIL import Image
        from roco_serverchan_notifier import image_renderer

        self.image_class = Image
        self.renderer = image_renderer

    def _assert_png(self, image_data):
        self.assertTrue(image_data.startswith(b"\x89PNG\r\n\x1a\n"))
        with self.image_class.open(io.BytesIO(image_data)) as image:
            image.load()
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.mode, "RGB")
            self.assertEqual(image.width, self.renderer.CANVAS_WIDTH)
            self.assertGreater(image.height, 0)

    def test_empty_merchant_renders_png_without_network(self):
        with patch.object(self.renderer.requests, "get") as get:
            image_data = self.renderer.render_merchant_card({"products": []})

        get.assert_not_called()
        self._assert_png(image_data)

    def test_one_product_renders_png_with_mocked_image_download(self):
        with io.BytesIO() as buffer:
            with self.image_class.new("RGBA", (120, 120), (80, 140, 200, 255)) as image:
                image.save(buffer, format="PNG")
            response = Mock(content=buffer.getvalue())
        image_url = "https://example.invalid/product.png"
        processed = {
            "title": "远行商人",
            "subtitle": "本轮商品",
            "products": [
                {
                    "name": "咕噜球",
                    "time_label": "08:00-12:00",
                    "image": image_url,
                    "price": 100,
                    "buy_limit_num": 3,
                }
            ],
        }
        with patch.object(self.renderer.requests, "get", return_value=response) as get:
            image_data = self.renderer.render_merchant_card(processed)

        get.assert_called_once_with(image_url, timeout=8)
        response.raise_for_status.assert_called_once_with()
        self._assert_png(image_data)


if __name__ == "__main__":
    unittest.main()
