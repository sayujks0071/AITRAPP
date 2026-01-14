import pytest
from unittest.mock import MagicMock, patch
from packages.strategy_foundry.data.loader import DataLoader
import pandas as pd
from pathlib import Path
from datetime import datetime

def test_loader_instantiation():
    loader = DataLoader()
    assert loader.session is not None

@patch("packages.strategy_foundry.data.loader.DataLoader.fetch_yahoo")
def test_loader_cache_logic(mock_fetch, tmp_path):
    # Test that loader checks cache
    # We override cache_dir to tmp_path

    loader = DataLoader(cache_dir=str(tmp_path))

    # Create a dummy cache file
    instrument = "TEST"
    timeframe = "5m"
    cache_file = tmp_path / f"{instrument}_{timeframe}.csv"

    df_cached = pd.DataFrame({"timestamp": [datetime.now(), datetime.now()], "close": [100, 101]})
    df_cached.to_csv(cache_file, index=False)

    # Run get_data
    # get_data calls read_csv which might fail on parsing timestamp if not careful,
    # but my loader code does pd.read_csv then converts timestamp.
    # The saved csv stringifies datetime. pd.read_csv reads as string.
    # Loader: df["timestamp"] = pd.to_datetime(df["timestamp"])

    df = loader.get_data(instrument, timeframe)

    assert not df.empty
    assert len(df) == 2
    mock_fetch.assert_not_called()

@patch("packages.strategy_foundry.data.loader.DataLoader.fetch_yahoo")
def test_loader_fetch_logic(mock_fetch, tmp_path):
    loader = DataLoader(cache_dir=str(tmp_path))

    # Mock return
    mock_fetch.return_value = pd.DataFrame({"timestamp": [datetime.now()], "close": [200]})

    df = loader.get_data("MISSING", "5m")

    assert not df.empty
    assert df.iloc[0]["close"] == 200
    mock_fetch.assert_called_once()
