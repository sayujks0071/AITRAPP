from packages.strategy_foundry.data.loader import DataLoader
from unittest.mock import patch, MagicMock
import pandas as pd
import pytest

def test_loader_cache_hit(tmp_path):
    loader = DataLoader(cache_dir=tmp_path)

    # Create fake cache
    csv_file = tmp_path / "NIFTY.csv"
    df_fake = pd.DataFrame({
        "open": [100], "high": [110], "low": [90], "close": [105], "volume": [1000]
    }, index=pd.to_datetime(["2023-01-01"]).tz_localize("Asia/Kolkata"))
    df_fake.index.name = "date"
    df_fake.to_csv(csv_file)

    # Mock request to ensure it's not called
    with patch("requests.get") as mock_get:
        df = loader.get_history("NIFTY")
        mock_get.assert_not_called()
        assert not df.empty
        assert len(df) == 1

def test_loader_download(tmp_path):
    loader = DataLoader(cache_dir=tmp_path)

    # Mock response
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "chart": {
            "result": [{
                "timestamp": [1672531200], # 2023-01-01
                "indicators": {
                    "quote": [{
                        "open": [100], "high": [110], "low": [90], "close": [105], "volume": [1000]
                    }]
                }
            }]
        }
    }
    mock_resp.status_code = 200

    with patch("requests.get", return_value=mock_resp):
        df = loader.get_history("NIFTY")
        assert len(df) == 1
        assert df.index[0].year == 2023

    # Check cache created
    assert (tmp_path / "NIFTY.csv").exists()
