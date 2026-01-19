import unittest

import pandas as pd

from packages.strategy_foundry.backtest.metrics import calculate_metrics


class TestMetrics(unittest.TestCase):
    def test_calculate_metrics_empty(self):
        m = calculate_metrics(pd.DataFrame(), pd.Series())
        self.assertEqual(m["trades"], 0)
        self.assertEqual(m["sharpe"], -99.9)

    def test_calculate_metrics_basic(self):
        trades_df = pd.DataFrame([
            {"pnl": 100, "return_pct": 0.01},
            {"pnl": -50, "return_pct": -0.005}
        ])

        daily_returns = pd.Series([0.01, -0.005], index=pd.to_datetime(["2023-01-01", "2023-01-02"]))

        m = calculate_metrics(trades_df, daily_returns)
        self.assertEqual(m["trades"], 2)
        self.assertEqual(m["win_rate"], 0.5)
        self.assertEqual(m["profit_factor"], 2.0)
        self.assertNotEqual(m["sharpe"], 0.0)
