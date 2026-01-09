"""
Tests for Data Loader
"""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.data.sources import DataSources

@pytest.fixture
def mock_yahoo_data():
    dates = pd.date_range(start="2023-01-01", periods=100, freq="15min")
    df = pd.DataFrame({
        "open": [100.0] * 100,
        "high": [105.0] * 100,
        "low": [95.0] * 100,
        "close": [102.0] * 100,
        "volume": [1000] * 100
    }, index=dates)
    return df

def test_loader_caches_data(tmp_path, mock_yahoo_data):
    with patch("packages.strategy_foundry.data.loader.CACHE_DIR", tmp_path), \
         patch.object(DataSources, 'get_yahoo_data', return_value=mock_yahoo_data) as mock_download:

        loader = DataLoader()

        df1 = loader.get_data("TEST", "15m")
        assert not df1.empty
        assert mock_download.call_count == 1

        cache_file = tmp_path / "TEST_15m.csv"
        assert cache_file.exists()

        df2 = loader.get_data("TEST", "15m")
        assert not df2.empty
        assert mock_download.call_count == 1

        # When reading from CSV, frequency metadata might be lost or inferred differently
        # So we relax the strict equality check slightly (check values and index)
        pd.testing.assert_frame_equal(df1, df2, check_freq=False)

def test_loader_filters_market_hours(tmp_path):
    dates = pd.date_range(start="2023-01-01 00:00", end="2023-01-01 23:59", freq="1h", tz="Asia/Kolkata")
    df = pd.DataFrame({"close": range(len(dates))}, index=dates)

    with patch("packages.strategy_foundry.data.loader.CACHE_DIR", tmp_path), \
         patch.object(DataSources, 'get_yahoo_data', return_value=df):

        loader = DataLoader()
        res = loader.get_data("TEST", "15m")

        assert not res.empty
        for ts in res.index:
            t = ts.time()
            assert t >= pd.Timestamp("09:15").time()
            assert t <= pd.Timestamp("15:30").time()
