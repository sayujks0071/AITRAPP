import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from packages.strategy_foundry.data.loader import DataLoader

class TestLoader(unittest.TestCase):
    @patch('packages.strategy_foundry.data.loader.download_yahoo_ohlcv')
    def test_get_data(self, mock_download):
        # Mock data
        df = pd.DataFrame({'close': [100, 101, 102]})
        mock_download.return_value = df

        loader = DataLoader()
        data = loader.get_data("NIFTY", "15m", refresh=True)

        self.assertFalse(data.empty)
        self.assertEqual(len(data), 3)
