"""
Tests for Strategy Foundry Loader
"""
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.data.sources import DataSources

class TestLoader:
    @pytest.fixture
    def loader(self):
        return DataLoader()

    @patch('packages.strategy_foundry.data.sources.DataSources.get_yahoo_data')
    def test_get_data_fetches_yahoo(self, mock_get, loader):
        # Mock data
        mock_df = pd.DataFrame({
            'open': [100, 101],
            'high': [102, 103],
            'low': [99, 100],
            'close': [101, 102],
            'volume': [1000, 2000]
        }, index=pd.to_datetime(['2023-01-01 09:15', '2023-01-01 09:20']))
        mock_get.return_value = mock_df

        df = loader.get_data("TEST", "5m", force_refresh=True)

        assert not df.empty
        assert len(df) == 2
        mock_get.assert_called_once()

    def test_market_hours_filter(self, loader):
        # Create data with pre/post market hours
        dates = pd.to_datetime([
            '2023-01-01 09:00', # Pre
            '2023-01-01 09:15', # Open
            '2023-01-01 12:00', # Mid
            '2023-01-01 15:30', # Close
            '2023-01-01 16:00'  # Post
        ]).tz_localize('Asia/Kolkata')

        df = pd.DataFrame({
            'open': [100]*5, 'high': [100]*5, 'low': [100]*5, 'close': [100]*5, 'volume': [100]*5
        }, index=dates)

        filtered = loader._process_data(df, "5m")

        # Should keep 09:15, 12:00, 15:30
        assert len(filtered) == 3
        assert filtered.index[0].hour == 9 and filtered.index[0].minute == 15
