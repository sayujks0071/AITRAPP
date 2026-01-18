import unittest
import pandas as pd
import numpy as np
from packages.strategy_foundry.backtest.metrics import compute_metrics, calculate_stability

class TestMetrics(unittest.TestCase):
    def test_metrics_calculation(self):
        # Mock trades
        trades = pd.DataFrame([
            {"pnl": 0.1, "bars": 5},
            {"pnl": -0.05, "bars": 3},
            {"pnl": 0.02, "bars": 4}
        ])

        # Mock equity
        idx = pd.date_range("2023-01-01", periods=100)
        equity = pd.Series(np.linspace(1.0, 1.2, 100), index=idx)

        m = compute_metrics(trades, equity)

        self.assertEqual(m["total_trades"], 3)
        self.assertGreater(m["cagr"], 0)
        self.assertGreater(m["win_rate"], 0.6)

    def test_empty_trades(self):
        trades = pd.DataFrame()
        equity = pd.Series([1.0], index=[pd.Timestamp("2023-01-01")])
        m = compute_metrics(trades, equity)
        self.assertEqual(m["total_trades"], 0)
        self.assertEqual(m["sharpe"], 0.0)

if __name__ == '__main__':
    unittest.main()
