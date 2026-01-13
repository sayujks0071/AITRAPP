from packages.strategy_foundry.data.loader import get_historical_data
import os
from unittest.mock import patch, MagicMock

def test_loader_cache():
    # Mock requests
    with patch("requests.get") as mock_get:
        mock_get.return_value.text = "Date,Open,High,Low,Close,Volume\n2023-01-01,100,101,99,100.5,1000"
        mock_get.return_value.raise_for_status = MagicMock()

        # Test download
        df = get_historical_data("TEST_SYM", days=10)
        assert not df.empty
        assert "close" in df.columns

        # Verify cache file created
        cache_path = "packages/strategy_foundry/data/cache/TEST_SYM.csv"
        assert os.path.exists(cache_path)

        # Cleanup
        if os.path.exists(cache_path):
            os.remove(cache_path)
