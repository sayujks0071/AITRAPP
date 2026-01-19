import os
import unittest
from unittest.mock import patch

import pandas as pd

from packages.strategy_foundry.data.loader import DataLoader


class TestDataLoader(unittest.TestCase):
    def setUp(self):
        self.loader = DataLoader(cache_dir="/tmp/test_foundry_cache")

    def tearDown(self):
        import shutil
        if os.path.exists("/tmp/test_foundry_cache"):
            shutil.rmtree("/tmp/test_foundry_cache")

    def test_get_symbol(self):
        self.assertEqual(self.loader.get_symbol_for_instrument("NIFTY"), "^NSEI")
        self.assertEqual(self.loader.get_symbol_for_instrument("UNKNOWN"), "UNKNOWN")

    @patch("packages.strategy_foundry.data.loader.DataLoader._download_yahoo")
    def test_fetch_data_mock(self, mock_download):
        # Mock successful download
        df_mock = pd.DataFrame({
            "open": [100, 101],
            "high": [102, 103],
            "low": [99, 100],
            "close": [101, 102],
            "volume": [1000, 2000]
        }, index=pd.to_datetime(["2023-01-01 10:00", "2023-01-01 10:05"]))

        mock_download.return_value = df_mock

        df = self.loader.fetch_data("NIFTY", "5m", force_refresh=True)
        self.assertFalse(df.empty, "DataFrame should not be empty")
        self.assertEqual(len(df), 2)
        mock_download.assert_called_with("^NSEI", "5m")

    @patch("packages.strategy_foundry.data.loader.DataLoader._download_yahoo")
    def test_fetch_data_fallback(self, mock_download):
        # Mock failure for primary, success for fallback
        def side_effect(symbol, timeframe):
            if symbol == "^NSEI":
                return None
            if symbol == "NIFTYBEES.NS":
                return pd.DataFrame({
                    "open": [50, 51],
                    "high": [52, 53],
                    "low": [49, 50],
                    "close": [51, 52],
                    "volume": [100, 200]
                }, index=pd.to_datetime(["2023-01-01 10:00", "2023-01-01 10:05"]))
            return None

        mock_download.side_effect = side_effect

        df = self.loader.fetch_data("NIFTY", "5m", force_refresh=True)
        self.assertFalse(df.empty, "DataFrame should not be empty")
        self.assertEqual(df["close"].iloc[0], 51)

        # Verify calls
        # Should call primary then fallback
        self.assertTrue(mock_download.call_count >= 2)
