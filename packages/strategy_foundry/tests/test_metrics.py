import unittest
import pandas as pd
from packages.strategy_foundry.backtest.metrics import calculate_metrics

class TestMetrics(unittest.TestCase):
    def test_calculate_metrics(self):
        # Profitable equity curve
        dates = pd.date_range("2023-01-01", periods=10, freq="D")
        equity = pd.Series([100, 101, 102, 103, 104, 105, 106, 107, 108, 110], index=dates)
        trades = [{"pnl": 1}, {"pnl": 1}]

        metrics = calculate_metrics(equity, trades)

        self.assertTrue(metrics["sharpe"] > 0)
        self.assertTrue(metrics["cagr"] > 0)
        self.assertEqual(metrics["trades"], 2)

    def test_empty_metrics(self):
        metrics = calculate_metrics(pd.Series(), [])
        self.assertEqual(metrics["sharpe"], -99.0)

if __name__ == "__main__":
    unittest.main()
