"""
Tests for Strategy Foundry Metrics
"""
import pytest
import pandas as pd
from packages.strategy_foundry.backtest.metrics import BacktestMetrics

class TestMetrics:
    def test_metrics_calculation(self):
        trades = pd.DataFrame([
            {'pnl': 100},
            {'pnl': -50},
            {'pnl': 100}
        ])

        # Equity curve: 100 -> 200 -> 150 -> 250
        dates = pd.date_range('2023-01-01', periods=4)
        equity = pd.Series([100000, 100100, 100050, 100150], index=dates)

        metrics = BacktestMetrics.calculate(trades, equity)

        assert metrics['total_trades'] == 3
        assert metrics['net_profit'] == 150
        assert metrics['win_rate'] == 2/3
        assert metrics['profit_factor'] == 200/50 # 4.0
        assert metrics['max_drawdown'] > 0
