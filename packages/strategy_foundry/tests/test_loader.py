
import pytest
import pandas as pd
from packages.strategy_foundry.data.loader import DataLoader

def test_loader_cache(tmp_path):
    loader = DataLoader(cache_dir=tmp_path)
    # Mock download or rely on internet (integration test?)
    # For unit test, we can manually write a cache file

    df = pd.DataFrame({
        "open": [100], "high": [110], "low": [90], "close": [105], "volume": [1000]
    }, index=pd.to_datetime(["2021-01-01"]).tz_localize("Asia/Kolkata"))

    cache_file = tmp_path / "TEST.csv"
    df.to_csv(cache_file)

    loaded = loader.get_data("TEST")
    assert not loaded.empty
    assert len(loaded) == 1
