import pandas as pd
from packages.strategy_foundry.backtest.metrics import calculate_metrics

def test_metrics_calc():
    equity = pd.Series([100, 105, 110, 108, 115], index=pd.date_range("2023-01-01", periods=5))
    trades = pd.DataFrame({
        "pnl": [5, 5, -2, 7],
        "pnl_pct": [0.05, 0.05, -0.02, 0.06]
    })

    m = calculate_metrics(equity, trades)

    assert m['total_return'] == 0.15
    assert m['trades'] == 4
    assert m['max_drawdown'] < 0
