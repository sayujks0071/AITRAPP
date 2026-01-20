import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
import datetime
import pytz
from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.data.sources import YahooSource

class TestDataLoader(unittest.TestCase):
    def setUp(self):
        self.loader = DataLoader(cache_dir="packages/strategy_foundry/tests/cache_tmp")
        self.ist = pytz.timezone("Asia/Kolkata")

    @patch("packages.strategy_foundry.data.loader.YahooSource.fetch_ohlcv")
    def test_get_data_mock(self, mock_fetch):
        # Setup mock return
        dates = pd.date_range("2023-01-01 09:15", periods=10, freq="1d", tz="UTC")
        df = pd.DataFrame({
            "open": np.random.rand(10),
            "high": np.random.rand(10),
            "low": np.random.rand(10),
            "close": np.random.rand(10),
            "volume": np.random.rand(10)
        }, index=dates)
        mock_fetch.return_value = df

        # Call
        result = self.loader.get_data("^NSEI", "1d", force_refresh=True)

        self.assertIsNotNone(result)
        self.assertEqual(len(result), 10)
        # Verify timezone conversion to IST (UTC+5:30)
        # 09:15 UTC -> 14:45 IST
        self.assertEqual(result.index[0].time(), datetime.time(14, 45))

    def test_process_dataframe_filtering(self):
        # Create a DF with times outside 09:15-15:30 IST
        # Note: Input to _process_dataframe is expected to be localized or UTC

        dates = pd.date_range("2023-01-01 09:00", "2023-01-01 16:00", freq="30min", tz="Asia/Kolkata")
        # 09:00, 09:30, 10:00, ... 15:30, 16:00
        # Valid: 09:30, 10:00 ... 15:30.
        # 09:00 is Invalid. 16:00 is Invalid.

        df = pd.DataFrame({
            "open": range(len(dates)),
            "high": range(len(dates)),
            "low": range(len(dates)),
            "close": range(len(dates)),
            "volume": range(len(dates))
        }, index=dates)

        # Loader assumes input might be UTC, converts to IST.
        # If input is already IST, _process_dataframe handles it (tz_convert is smart).

        processed = self.loader._process_dataframe(df)

        # 09:00 should be gone
        # 16:00 should be gone
        self.assertFalse(datetime.time(9, 0) in [t.time() for t in processed.index])
        self.assertFalse(datetime.time(16, 0) in [t.time() for t in processed.index])
        self.assertTrue(datetime.time(9, 30) in [t.time() for t in processed.index])

if __name__ == '__main__':
    unittest.main()
