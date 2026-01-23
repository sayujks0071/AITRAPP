import unittest
import pandas as pd
import numpy as np
from packages.strategy_foundry.backtest.metrics import calculate_metrics

class TestMetrics(unittest.TestCase):
    def test_metrics(self):
        dates = pd.date_range("2023-01-01", periods=100, freq="D")
        # Simple uptrend
        prices = np.linspace(100, 200, 100)
        equity = pd.Series(prices * 1000, index=dates) # 100k to 200k

        trades = [
            {"pnl": 1000, "entry_time": dates[0], "exit_time": dates[10]},
            {"pnl": -500, "entry_time": dates[20], "exit_time": dates[30]}
        ]

        metrics = calculate_metrics(equity, trades, initial_capital=100000)

        self.assertGreater(metrics["cagr"], 0)
        self.assertEqual(metrics["total_trades"], 2)
        self.assertEqual(metrics["win_rate"], 0.5)
        self.assertEqual(metrics["profit_factor"], 2.0)

        print(metrics)

if __name__ == "__main__":
    unittest.main()
