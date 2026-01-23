import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from pathlib import Path
import shutil
import os
from packages.strategy_foundry.data.loader import DataLoader

class TestLoader(unittest.TestCase):
    def setUp(self):
        self.cache_dir = "packages/strategy_foundry/tests/temp_cache"
        self.loader = DataLoader(cache_dir=self.cache_dir)

    def tearDown(self):
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)

    @patch("packages.strategy_foundry.data.loader.requests.get")
    def test_download_and_cache(self, mock_get):
        # Mock response
        csv_content = b"Datetime,Open,High,Low,Close,Volume\n2023-01-01 09:15:00,100,105,95,102,1000\n2023-01-01 09:20:00,102,108,100,105,1500"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = csv_content
        mock_get.return_value = mock_response

        # Fetch
        df = self.loader.get_data("TEST", "5m", days=1, use_cache=False)

        self.assertFalse(df.empty)
        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[0]["close"], 102)

        # Verify cache file created
        cache_file = Path(self.cache_dir) / "TEST_5m.csv"
        self.assertTrue(cache_file.exists())

        # Test loading from cache (mock get shouldn't be called again if we use cache, but here we force use_cache=True and it should exist)
        mock_get.reset_mock()
        df_cached = self.loader.get_data("TEST", "5m", days=1, use_cache=True)
        self.assertEqual(len(df_cached), 2)
        mock_get.assert_not_called()

if __name__ == "__main__":
    unittest.main()
