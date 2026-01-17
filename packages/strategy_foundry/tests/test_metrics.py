import unittest
import pandas as pd
from packages.strategy_foundry.backtest.metrics import calculate_metrics

class TestMetrics(unittest.TestCase):
    def test_metrics_calculation(self):
        trades = pd.DataFrame({
            "pnl": [100, -50, 200, -100, 50],
            "entry_time": pd.date_range("2023-01-01", periods=5)
        })

        metrics = calculate_metrics(trades)

        self.assertEqual(metrics["trades"], 5)
        self.assertEqual(metrics["win_rate"], 3/5)
        self.assertAlmostEqual(metrics["profit_factor"], 350/150)

    def test_empty_metrics(self):
        metrics = calculate_metrics(pd.DataFrame())
        self.assertEqual(metrics["trades"], 0)

if __name__ == '__main__':
    unittest.main()
