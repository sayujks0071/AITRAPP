"""
Tests for Metrics and Ranking
"""
import pandas as pd
from packages.strategy_foundry.backtest.metrics import BacktestMetrics
from packages.strategy_foundry.selection.ranker import Ranker
from packages.strategy_foundry.backtest.sanity import SanityChecker

def test_metrics_calculation():
    trades = pd.DataFrame({
        "pnl": [100, -50, 100, -50],
        "entry_time": pd.date_range("2023-01-01", periods=4),
        "exit_time": pd.date_range("2023-01-01 01:00", periods=4)
    })
    equity = pd.Series([100000, 100100, 100050, 100150, 100100],
                       index=pd.date_range("2023-01-01", periods=5))

    m = BacktestMetrics.calculate(trades, equity)

    assert m['total_trades'] == 4
    assert m['net_profit'] == 100
    assert m['win_rate'] == 0.5
    assert m['profit_factor'] == 2.0
    assert m['max_drawdown'] >= 0

def test_ranker_score():
    metrics = {
        "sharpe": 2.0,
        "calmar": 3.0,
        "cagr": 0.5,
        "max_drawdown": 0.1,
        "sanity_passed": True
    }
    weights = {
        "sharpe": 0.25,
        "calmar": 0.25,
        "return": 0.20,
        "stability": 0.15,
        "low_turnover": 0.10,
        "sanity": 0.05
    }

    score = Ranker.calculate_score(metrics, weights)
    assert score > 0

    # Test penalty
    bad_metrics = metrics.copy()
    bad_metrics['max_drawdown'] = 0.3 # > 0.2

    bad_score = Ranker.calculate_score(bad_metrics, weights)
    assert bad_score < score

def test_sanity_checker():
    # Test Overtrading
    dates = [pd.Timestamp("2023-01-01") for _ in range(20)]
    trades = [{"pnl": 1, "entry_time": d, "exit_time": d} for d in dates]

    res = SanityChecker.check_intraday_sanity(trades, "5m")
    assert res['overtrading'] == True
    assert res['passed'] == False

    # Test Late Day Dependence
    t1 = [{"pnl": 100, "entry_time": pd.Timestamp("2023-01-01 15:10"), "exit_time": pd.Timestamp("2023-01-01 15:15")}] # Late
    t2 = [{"pnl": 10, "entry_time": pd.Timestamp("2023-01-01 10:00"), "exit_time": pd.Timestamp("2023-01-01 10:15")}] # Early

    # Total 110. Late 100. Ratio > 0.5
    res = SanityChecker.check_intraday_sanity(t1 + t2, "5m")
    assert res['late_day_dependence'] == True
    assert res['passed'] == False
