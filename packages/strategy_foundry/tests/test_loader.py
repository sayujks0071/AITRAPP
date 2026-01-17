import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
from packages.strategy_foundry.data.loader import DataLoader

class TestLoader(unittest.TestCase):
    def setUp(self):
        self.loader = DataLoader()
        self.loader.sources.get_yahoo = MagicMock()

    def test_get_data_cache_miss(self):
        # Mock Yahoo return
        mock_df = pd.DataFrame({
            "open": [100], "high": [110], "low": [90], "close": [105], "volume": [1000]
        }, index=pd.to_datetime(["2023-01-01 10:00:00"]).tz_localize("Asia/Kolkata"))

        self.loader.sources.get_yahoo().fetch_ohlcv.return_value = mock_df

        # Call
        df = self.loader.get_data("NIFTY", "5m", refresh=True)

        self.assertFalse(df.empty)
        self.assertEqual(df.iloc[0]["close"], 105)
        self.loader.sources.get_yahoo().fetch_ohlcv.assert_called()

    def test_get_data_unknown_symbol(self):
        df = self.loader.get_data("UNKNOWN", "5m")
        self.assertTrue(df.empty)

if __name__ == '__main__':
    unittest.main()
