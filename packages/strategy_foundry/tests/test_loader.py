import unittest
from unittest.mock import patch, MagicMock
from packages.strategy_foundry.data.loader import DataLoader
import pandas as pd
from datetime import datetime

class TestDataLoader(unittest.TestCase):
    def setUp(self):
        self.loader = DataLoader()

    def test_get_symbol(self):
        self.assertEqual(self.loader.get_symbol_for_instrument("NIFTY"), "^NSEI")
        self.assertEqual(self.loader.get_symbol_for_instrument("UNKNOWN"), "UNKNOWN")

    @patch("requests.get")
    def test_fetch_data_mock(self, mock_get):
        # Mock response
        # 1672633800 = 2023-01-02 04:30:00 UTC = 10:00 IST
        # 1672634100 = 2023-01-02 04:35:00 UTC = 10:05 IST
        ts1 = 1672633800
        ts2 = 1672634100

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "chart": {
                "result": [{
                    "timestamp": [ts1, ts2],
                    "indicators": {
                        "quote": [{
                            "open": [100, 101],
                            "high": [102, 103],
                            "low": [99, 100],
                            "close": [101, 102],
                            "volume": [1000, 2000]
                        }]
                    }
                }]
            }
        }
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        df = self.loader.fetch_data("NIFTY", "5m", force_refresh=True)
        self.assertFalse(df.empty, "DataFrame should not be empty")
        self.assertEqual(len(df), 2)
        self.assertIn("close", df.columns)
