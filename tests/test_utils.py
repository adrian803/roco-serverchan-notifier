from __future__ import annotations

import unittest
from unittest.mock import patch

from roco_serverchan_notifier.utils import coerce_bool, env_bool, to_int


class UtilsTests(unittest.TestCase):
    def test_coerce_bool_handles_none_bool_numeric_and_text(self):
        self.assertTrue(coerce_bool(None, True))
        self.assertFalse(coerce_bool(None, False))
        self.assertTrue(coerce_bool(True, False))
        self.assertFalse(coerce_bool(False, True))
        self.assertTrue(coerce_bool(1, False))
        self.assertFalse(coerce_bool(0, True))
        self.assertTrue(coerce_bool(" yes ", False))
        self.assertFalse(coerce_bool("no", True))

    def test_env_bool_reads_truthy_and_defaults(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertTrue(env_bool("FLAG", True))
            self.assertFalse(env_bool("FLAG", False))

        with patch.dict("os.environ", {"FLAG": "On"}, clear=True):
            self.assertTrue(env_bool("FLAG"))

        with patch.dict("os.environ", {"FLAG": "off"}, clear=True):
            self.assertFalse(env_bool("FLAG", True))

    def test_to_int_accepts_int_like_values_and_rejects_invalid_values(self):
        self.assertEqual(to_int(5), 5)
        self.assertEqual(to_int("42"), 42)
        self.assertEqual(to_int(" 7 "), 7)
        self.assertIsNone(to_int(""))
        self.assertIsNone(to_int("abc"))
        self.assertIsNone(to_int(None))


if __name__ == "__main__":
    unittest.main()
