from packages.strategy_foundry.backtest.metrics import calculate_cagr, calculate_sharpe

def test_metrics_empty():
    assert calculate_cagr(1.0, 1.0, 1.0) == 0.0

def test_metrics_basic():
    # Double in 1 year
    cagr = calculate_cagr(100, 200, 1)
    assert abs(cagr - 1.0) < 0.01
