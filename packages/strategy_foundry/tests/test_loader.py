import pytest
from unittest.mock import patch, MagicMock
from packages.strategy_foundry.data.loader import get_data
import pandas as pd

def test_loader_cache_logic():
    with patch("packages.strategy_foundry.data.loader.os.path.exists") as mock_exists, \
         patch("packages.strategy_foundry.data.loader.os.path.getmtime") as mock_mtime, \
         patch("packages.strategy_foundry.data.loader.pd.read_csv") as mock_read:

        mock_exists.return_value = True
        # Mock mtime to be recent
        import time
        mock_mtime.return_value = time.time()

        mock_read.return_value = pd.DataFrame({
            "open": [100], "high": [110], "low": [90], "close": [105], "volume": [1000]
        }, index=pd.to_datetime(["2023-01-01"]))

        # Should return cached data
        df = get_data("NIFTY")
        assert not df.empty
        assert "close" in df.columns
