import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from packages.strategy_foundry.data.loader import DataLoader

class TestLoader(unittest.TestCase):
    @patch("packages.strategy_foundry.data.loader.requests.get")
    def test_fetch_data_success(self, mock_get):
        # Mock Response for Chart API (JSON)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "chart": {
                "result": [{
                    "meta": {},
                    "timestamp": [1672531200, 1672617600],
                    "indicators": {
                        "quote": [{
                            "open": [100.0, 102.0],
                            "high": [110.0, 112.0],
                            "low": [90.0, 92.0],
                            "close": [105.0, 107.0],
                            "volume": [1000, 1200]
                        }]
                    }
                }],
                "error": None
            }
        }
        mock_get.return_value = mock_resp

        loader = DataLoader()
        # Mock cache check to fail so it fetches
        with patch("pathlib.Path.exists", return_value=False):
            df = loader.fetch_data("NIFTY", "1d")

        self.assertFalse(df.empty)
        self.assertEqual(len(df), 2)
        self.assertIn("close", df.columns)
        self.assertEqual(df.iloc[0]["close"], 105.0)

    @patch("packages.strategy_foundry.data.loader.requests.get")
    def test_fetch_data_failure(self, mock_get):
        mock_get.side_effect = Exception("Network Error")

        loader = DataLoader()
        with patch("pathlib.Path.exists", return_value=False):
             with self.assertRaises(ValueError):
                 loader.fetch_data("NIFTY", "1d")
