from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from roco_serverchan_notifier.config_store import ConfigStore
from roco_serverchan_notifier.push import ProviderConfig
from roco_serverchan_notifier.settings import Settings


class ConfigStoreModuleTests(unittest.TestCase):
    def test_save_and_load_round_trip_settings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            store = ConfigStore(path)
            original = Settings(
                rocom_api_key="rocom-key",
                game_api_url="https://example.com/api",
                notify_empty=True,
                http_timeout=45,
                schedule_times="08:01,12:01",
                run_on_start=True,
                delivery_mode="single",
                selected_provider="serverchan-default",
                failover_order=["serverchan-default"],
                providers=[
                    ProviderConfig(
                        id="serverchan-default",
                        type="serverchan",
                        name="Server 酱",
                        enabled=True,
                        config={"sendkey": "send-key"},
                    )
                ],
                include_price_info=True,
            )

            store.save(original)
            loaded = store.load()

        self.assertEqual(loaded.to_dict(), original.to_dict())

    def test_update_writes_new_business_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            store = ConfigStore(path)
            store.save(
                Settings(
                    rocom_api_key="rocom-key",
                    game_api_url="https://example.com/api",
                    notify_empty=False,
                    http_timeout=30,
                    schedule_times="08:01,12:01",
                    run_on_start=False,
                    delivery_mode="all",
                    selected_provider="serverchan-default",
                    failover_order=["serverchan-default"],
                    providers=[
                        ProviderConfig(
                            id="serverchan-default",
                            type="serverchan",
                            name="Server 酱",
                            enabled=True,
                            config={"sendkey": "send-key"},
                        )
                    ],
                    include_price_info=False,
                )
            )

            updated = store.update({"notify_empty": True, "http_timeout": 60})

        self.assertTrue(updated.notify_empty)
        self.assertEqual(updated.http_timeout, 60)

    def test_config_store_module_exposes_console_auth_reader(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            path.write_text('{"console_auth":{"password_hash":"hash"}}', encoding="utf-8")

            store = ConfigStore(path)

            self.assertEqual(store.console_auth()["password_hash"], "hash")

    def test_load_invalid_json_records_issue_and_moves_original_to_backup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            path.write_text("{broken-json", encoding="utf-8")
            store = ConfigStore(path)

            settings = store.load()
            issue = store.load_issue_dict()

        self.assertEqual(settings.schedule_times, "08:05,12:05,16:05,20:05")
        self.assertIsNotNone(issue)
        self.assertIn("配置读取失败", issue["message"])
        self.assertTrue(issue["backup_path"])
        self.assertFalse(path.exists())

    def test_save_preserves_console_auth_payload(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "console_auth": {"password_hash": "hash"},
                        "rocom_api_key": "old",
                    }
                ),
                encoding="utf-8",
            )
            store = ConfigStore(path)
            store.save(
                Settings(
                    rocom_api_key="new",
                    game_api_url="https://example.com/api",
                    notify_empty=False,
                    http_timeout=30,
                    schedule_times="08:01,12:01",
                    run_on_start=False,
                    delivery_mode="all",
                    selected_provider="serverchan-default",
                    failover_order=["serverchan-default"],
                    providers=[
                        ProviderConfig(
                            id="serverchan-default",
                            type="serverchan",
                            name="Server 酱",
                            enabled=True,
                            config={"sendkey": "send-key"},
                        )
                    ],
                    include_price_info=False,
                )
            )

            saved = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(saved["console_auth"]["password_hash"], "hash")
        self.assertEqual(saved["rocom_api_key"], "new")

    def test_write_payload_is_atomic_via_temp_file_replace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            store = ConfigStore(path)
            store.save(
                Settings(
                    rocom_api_key="rocom-key",
                    game_api_url="https://example.com/api",
                    notify_empty=False,
                    http_timeout=30,
                    schedule_times="08:01,12:01",
                    run_on_start=False,
                    delivery_mode="all",
                    selected_provider="serverchan-default",
                    failover_order=["serverchan-default"],
                    providers=[
                        ProviderConfig(
                            id="serverchan-default",
                            type="serverchan",
                            name="Server 酱",
                            enabled=True,
                            config={"sendkey": "send-key"},
                        )
                    ],
                    include_price_info=False,
                )
            )

            tmp_files = list(path.parent.glob("*.tmp"))

        self.assertEqual(tmp_files, [])


if __name__ == "__main__":
    unittest.main()
