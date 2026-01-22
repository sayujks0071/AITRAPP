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

    @patch("packages.strategy_foundry.data.sources.YahooSource.fetch")
    def test_get_data_mock(self, mock_fetch):
        # Mock successful download
        df_mock = pd.DataFrame({
            "open": [100, 101],
            "high": [102, 103],
            "low": [99, 100],
            "close": [101, 102],
            "volume": [1000, 2000]
        }, index=pd.to_datetime(["2023-01-01 10:00", "2023-01-01 10:05"]))
        # Add timezone to match loader expectation
        df_mock.index = df_mock.index.tz_localize("Asia/Kolkata")

        mock_fetch.return_value = df_mock

        # DataLoader.get_data takes symbol, not instrument name
        df = self.loader.get_data("^NSEI", "5m", force_refresh=True)
        self.assertFalse(df.empty, "DataFrame should not be empty")
        self.assertEqual(len(df), 2)
        # Verify call args (symbol, tf, range)
        # range_map for 5m is '60d'
        mock_fetch.assert_called_with("^NSEI", "5m", "60d")
