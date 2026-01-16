"""Tests for Metrics"""
import unittest
import pandas as pd
from packages.strategy_foundry.backtest.metrics import calculate_metrics

class TestMetrics(unittest.TestCase):
    def test_metrics_calc(self):
        dates = pd.date_range("2023-01-01", periods=100)
        equity = pd.Series([100 * (1.01 ** i) for i in range(100)], index=dates) # Steady 1% daily
        trades = pd.DataFrame([{'pnl': 10}, {'pnl': -5}])

        m = calculate_metrics(equity, trades)
        self.assertGreater(m['cagr'], 0)
        self.assertGreater(m['sharpe'], 0)
        self.assertEqual(m['trades'], 2)
