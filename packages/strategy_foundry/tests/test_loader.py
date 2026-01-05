
import pytest
import pandas as pd
from packages.strategy_foundry.data.loader import fetch_data

def test_fetch_data_structure(mocker):
    # Mock requests
    mock_resp = mocker.Mock()
    mock_resp.text = "Date,Open,High,Low,Close,Volume\n2023-01-01,100,110,90,105,1000\n2023-01-02,105,115,95,110,1200"
    mock_resp.status_code = 200
    mocker.patch("requests.get", return_value=mock_resp)

    df = fetch_data("NIFTY")
    assert not df.empty
    assert "close" in df.columns
    assert isinstance(df.index, pd.DatetimeIndex)
    assert str(df.index.tz) == "Asia/Kolkata"

def test_loader_caches_data(mocker, tmp_path):
    mocker.patch("packages.strategy_foundry.data.loader.CACHE_DIR", tmp_path)

    mock_resp = mocker.Mock()
    mock_resp.text = "Date,Open,High,Low,Close,Volume\n2023-01-01,100,110,90,105,1000"
    mocker.patch("requests.get", return_value=mock_resp)

    fetch_data("NIFTY")

    assert (tmp_path / "NIFTY.csv").exists()
