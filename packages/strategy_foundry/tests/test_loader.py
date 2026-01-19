import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from packages.strategy_foundry.data.loader import DataLoader

@patch("requests.get")
def test_download_yahoo(mock_get):
    # Mock response
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    csv_content = """Date,Open,High,Low,Close,Adj Close,Volume
2023-01-01,18000,18100,17900,18050,18050,100000
2023-01-02,18050,18200,18000,18150,18150,120000
"""
    mock_resp.text = csv_content
    mock_get.return_value = mock_resp

    loader = DataLoader()
    # Bypass file system cache for unit test by mocking _download_yahoo directly or checking calls
    # but here we test the internal _download_yahoo if we want, or the public get_data

    # Let's test _download_yahoo directly via the mock above being used inside get_data
    # But get_data writes to file. We should mock pathlib.Path.

    with patch("pathlib.Path.exists", return_value=False), \
         patch("pathlib.Path.mkdir"), \
         patch("pandas.DataFrame.to_csv"): # Avoid writing to disk

        df = loader.get_data("TEST")

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "close" in df.columns
        assert df.index.tz.zone == "Asia/Kolkata"

def test_integration_download_real():
    # Only run this if we want to verify network (optional, skipped by default in CI usually)
    pass
