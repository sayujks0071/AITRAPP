from unittest.mock import MagicMock, patch
import pandas as pd
from datetime import datetime, timedelta
import pytest
from packages.strategy_foundry.data.loader import DataLoader

def test_loader_cache(tmp_path):
    pass

@patch("packages.strategy_foundry.data.sources.YahooSource.download_csv")
def test_loader_fetches_and_caches(mock_download, tmp_path):
    # Setup mock return data that falls WITHIN market hours (09:15 - 15:30)
    # 2023-01-02 was a Monday
    dates = pd.date_range("2023-01-02 09:15", periods=10, freq="15min")
    df = pd.DataFrame({
        "Open": [100]*10, "High": [105]*10, "Low": [95]*10, "Close": [101]*10, "Volume": [1000]*10
    }, index=dates)
    mock_download.return_value = df

    # Init loader
    loader = DataLoader()
    loader.cache_dir = tmp_path

    # 1. Fetch
    df_res = loader.get_data("NIFTY", "15m", force_refresh=True)
    assert len(df_res) == 10
    mock_download.assert_called_once()

    # 2. Verify File Created
    cache_file = tmp_path / "NIFTY_15m.csv"
    assert cache_file.exists()

    # 3. Read from cache (force_refresh=False)
    mock_download.reset_mock()
    df_cached = loader.get_data("NIFTY", "15m", force_refresh=False)
    assert len(df_cached) == 10
    mock_download.assert_not_called()
