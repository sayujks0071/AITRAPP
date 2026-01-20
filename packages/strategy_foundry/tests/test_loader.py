import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import os
import shutil
from packages.strategy_foundry.data.loader import DataLoader

class TestDataLoader(unittest.TestCase):
    def setUp(self):
        self.test_cache = "packages/strategy_foundry/tests/temp_cache"
        self.loader = DataLoader(cache_dir=self.test_cache)

    def tearDown(self):
        if os.path.exists(self.test_cache):
            shutil.rmtree(self.test_cache)

    @patch('requests.get')
    def test_download_and_cache(self, mock_get):
        # Mock Yahoo CSV response
        csv_content = """Date,Open,High,Low,Close,Adj Close,Volume
2023-01-01,18000,18100,17900,18050,18050,100000
2023-01-02,18050,18200,18000,18150,18150,150000
"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = csv_content
        mock_get.return_value = mock_response

        df = self.loader.fetch_data("NIFTY", force_refresh=True)

        self.assertFalse(df.empty)
        self.assertEqual(len(df), 2)
        self.assertIn("open", df.columns)
        self.assertTrue(os.path.exists(os.path.join(self.test_cache, "NIFTY_1D.csv")))

        # Test loading from cache
        df_cached = self.loader.fetch_data("NIFTY", force_refresh=False)
        self.assertEqual(len(df_cached), 2)
        # Check timezone
        self.assertEqual(str(df_cached.index.tz), "Asia/Kolkata")

if __name__ == "__main__":
    unittest.main()
