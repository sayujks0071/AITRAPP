"""Tests for Data Loader"""
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import pandas as pd
from packages.strategy_foundry.data.loader import DataLoader

class TestDataLoader(unittest.TestCase):
    def setUp(self):
        self.loader = DataLoader(cache_dir=Path("/tmp/test_cache"))

    @patch('requests.get')
    def test_download_yahoo(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "Date,Open,High,Low,Close,Adj Close,Volume\n2023-01-01,100,110,90,105,105,1000"
        mock_get.return_value = mock_resp

        df = self.loader._download_yahoo("TEST", 10)
        self.assertFalse(df.empty)
        self.assertIn('close', df.columns)
        self.assertEqual(len(df), 1)

    def test_cache_validation(self):
        p = Path("/tmp/test_cache/test.csv")
        if p.exists(): p.unlink()
        self.assertFalse(self.loader._is_cache_valid(p))
