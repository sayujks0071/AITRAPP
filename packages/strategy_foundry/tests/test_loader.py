import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import io
import os
from packages.strategy_foundry.data.loader import load_data, SYMBOL_MAP, CACHE_DIR

@patch('packages.strategy_foundry.data.loader.requests.get')
@patch('packages.strategy_foundry.data.loader.os.path.exists')
def test_load_data_download(mock_exists, mock_requests_get):
    # Setup mocks
    mock_exists.return_value = False # Cache miss

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "Date,Open,High,Low,Close,Volume\n2023-01-01,100,105,95,102,1000"
    mock_requests_get.return_value = mock_response

    # We need to ensure that pd.read_csv inside _download_yahoo works correctly
    # Since we are not mocking pd.read_csv globally, it should work with io.StringIO

    # However, we are also saving to cache using to_csv.
    # And potentially creating dirs.
    # We should mock to_csv and makedirs to avoid side effects.

    with patch('packages.strategy_foundry.data.loader.pd.DataFrame.to_csv') as mock_to_csv:
        with patch('packages.strategy_foundry.data.loader.os.makedirs') as mock_makedirs:
             df = load_data("NIFTY")

    assert df is not None
    assert len(df) == 1
    assert "close" in df.columns
    mock_requests_get.assert_called_once()
    assert SYMBOL_MAP["NIFTY"] in mock_requests_get.call_args[0][0]

@patch('packages.strategy_foundry.data.loader.pd.read_csv')
@patch('packages.strategy_foundry.data.loader.os.path.exists')
def test_load_data_cache_hit(mock_exists, mock_read_csv):
    mock_exists.return_value = True

    # Mock cached dataframe
    cached_df = pd.DataFrame({
        "open": [100], "high": [105], "low": [95], "close": [102], "volume": [1000]
    }, index=pd.date_range("2023-01-01", periods=1))

    # Set index name
    cached_df.index.name = "Date"

    # Make it look fresh (today)
    cached_df.index = [pd.Timestamp.now()]

    mock_read_csv.return_value = cached_df

    df = load_data("NIFTY")

    assert df is not None
    mock_read_csv.assert_called()
    # Should not trigger download
