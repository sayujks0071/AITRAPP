from unittest.mock import MagicMock, patch
import pandas as pd
from datetime import datetime
import pytest
from packages.strategy_foundry.data.loader import DataLoader

def test_loader_cache(tmp_path):
    pass

@patch("packages.strategy_foundry.data.loader.DataLoader._fetch_yahoo")
def test_loader_fetches_and_caches(mock_fetch, tmp_path):
    # Setup mock return data that falls WITHIN market hours (09:15 - 15:30)
    dates = pd.date_range("2023-01-02 09:15", periods=10, freq="15min", tz="Asia/Kolkata")
    df = pd.DataFrame({
        "open": [100]*10, "high": [105]*10, "low": [95]*10, "close": [101]*10, "volume": [1000]*10, "date": dates
    }, index=dates)
    # mock_fetch returns DataFrame with date column or index? My impl of _fetch_yahoo returns df with index named 'date'
    # but the loader expects to save it to csv and reload.
    # The _fetch_yahoo returns a df with index set to date.

    mock_fetch.return_value = df

    # Init loader
    loader = DataLoader(cache_dir=str(tmp_path))

    # 1. Fetch
    df_res = loader.get_data("NIFTY", "15m", force_refresh=True)
    assert len(df_res) == 10
    mock_fetch.assert_called_once()

    # 2. Verify File Created
    cache_file = tmp_path / "NIFTY_15m.csv"
    assert cache_file.exists()

    # 3. Read from cache (force_refresh=False)
    mock_fetch.reset_mock()
    df_cached = loader.get_data("NIFTY", "15m", force_refresh=False)
    assert len(df_cached) == 10
    mock_fetch.assert_not_called()
