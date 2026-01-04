import pandas as pd
import pytest

def test_walk_forward():
    from packages.strategy_foundry.backtest.walkforward import WalkForwardValidator

    dates = pd.date_range(start="2023-01-01", periods=200, freq="5min", tz="Asia/Kolkata")
    df = pd.DataFrame({
        "timestamp": dates,
        "open": [100 + i for i in range(200)],
        "high": [105 + i for i in range(200)],
        "low": [95 + i for i in range(200)],
        "close": [102 + i for i in range(200)],
        "volume": [1000] * 200
    })

    strat = {
        "id": "test",
        "entry": {"trend_ema_cross": {"fast": 5, "slow": 10}},
        "exit": {"atr_stop": {"period": 14, "multiple": 2.0}},
        "filters": []
    }

    costs = {"all_in_cost_bps_per_side": 3.0, "slippage_bps_per_side": 2.0}

    validator = WalkForwardValidator(df, strat, costs, folds=2)
    res = validator.run()

    assert res is not None
    assert "sharpe" in res
    assert "stability" in res

def test_sanity_check():
    from packages.strategy_foundry.backtest.sanity import SanityCheck

    dates = pd.date_range(start="2023-01-01", periods=100, freq="1D", tz="Asia/Kolkata")
    df = pd.DataFrame({
        "timestamp": dates,
        "open": [100 + i for i in range(100)],
        "high": [105 + i for i in range(100)],
        "low": [95 + i for i in range(100)],
        "close": [102 + i for i in range(100)],
        "volume": [1000] * 100
    })

    strat = {
        "id": "test",
        "entry": {"trend_ema_cross": {"fast": 5, "slow": 10}},
        "exit": {"atr_stop": {"period": 14, "multiple": 2.0}},
        "filters": []
    }
    costs = {"all_in_cost_bps_per_side": 3.0, "slippage_bps_per_side": 2.0}

    sanity = SanityCheck(df, costs)
    assert sanity.check(strat) is True
