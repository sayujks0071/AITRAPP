import pandas as pd
from packages.strategy_foundry.backtest.metrics import calculate_metrics

def test_metrics_zeros():
    returns = pd.Series([0, 0, 0, 0])
    trades = pd.DataFrame()
    m = calculate_metrics(returns, trades)
    assert m['sharpe'] == 0
    assert m['max_dd'] == 0

def test_metrics_positive():
    # If returns are constant, std() is 0.
    # Volatility is 0.
    # Sharpe calculation: cagr / vol.
    # If vol is 0, our code returns 0 (safety check).
    # So for perfect consistency, Sharpe is 0 in our implementation.

    # Let's add slight noise to make vol > 0 but small.
    returns = pd.Series([0.01, 0.011, 0.009, 0.01])
    trades = pd.DataFrame([{'pnl': 0.01}, {'pnl': 0.01}])
    m = calculate_metrics(returns, trades)

    # With small vol, Sharpe should be high
    assert m['sharpe'] > 2.0
    assert abs(m['max_dd']) < 0.01
    assert m['win_rate'] == 1.0
