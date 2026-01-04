import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from packages.strategy_foundry.data.loader import load_instrument_data, SYMBOL_MAP

class TestLoader(unittest.TestCase):
    @patch('packages.strategy_foundry.data.loader.requests.get')
    def test_download_yahoo(self, mock_get):
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "chart": {
                "result": [{
                    "timestamp": [1609459200, 1609545600],
                    "indicators": {
                        "quote": [{
                            "open": [100, 101],
                            "high": [105, 106],
                            "low": [95, 96],
                            "close": [102, 104],
                            "volume": [1000, 1200]
                        }]
                    }
                }]
            }
        }
        mock_get.return_value = mock_response

        df = load_instrument_data("TEST_SYM", force_refresh=True)

        self.assertFalse(df.empty)
        self.assertEqual(len(df), 2)
        self.assertTrue("close" in df.columns)
        self.assertEqual(df.index[0].year, 2021)

if __name__ == '__main__':
    unittest.main()
