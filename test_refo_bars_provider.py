import json
import os
import unittest
from unittest.mock import Mock

from refo_bars_provider import RefoBarsError, RefoBarsProvider


class RefoBarsProviderTests(unittest.TestCase):
    def setUp(self):
        self.old = dict(os.environ)
        os.environ["REFO_BARS_ENABLED"] = "true"
        os.environ["REFO_BARS_URL"] = "https://example.invalid/down/share"
        os.environ["REFO_BARS_PASSWORD"] = "test-secret"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old)

    def test_daily_payload_is_normalized_and_non_live(self):
        session = Mock()
        session.cookies = {"session": "opaque"}
        auth = Mock(status_code=200)
        auth.raise_for_status = Mock()
        session.post.return_value = auth
        body = {
            "lastRefreshCairoDate": "2026-09-19",
            "lastRefreshWasPostClose": False,
            "bars": [
                {"date": "2026-09-17", "open": 131.75, "high": 134, "low": 131.31,
                 "close": 132.5, "volume": 11412459}
            ],
        }
        download = Mock(status_code=200)
        download.raise_for_status = Mock()
        download.json.return_value = body
        session.get.return_value = download
        p = RefoBarsProvider(session=session)
        result = p.history("COMI")
        self.assertEqual(result["mode"], "EOD")
        self.assertFalse(result["is_live"])
        self.assertEqual(result["latest_bar_date"], "2026-09-17")
        session.post.assert_called_once()
        self.assertNotIn("test-secret", json.dumps(result))

    def test_failed_symbol_is_rejected(self):
        with self.assertRaises(RefoBarsError):
            RefoBarsProvider._validate_payload("ACFR", {
                "bars": [], "failed": True, "error": "upstream failed"
            })


if __name__ == "__main__":
    unittest.main()
