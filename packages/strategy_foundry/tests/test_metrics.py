import unittest
import pandas as pd
import numpy as np
from packages.strategy_foundry.backtest.metrics import calculate_metrics

class TestMetrics(unittest.TestCase):
    def test_calculate_metrics(self):
        # Create dummy equity curve
        dates = pd.date_range(start="2023-01-01", periods=10, freq="D")
        equity = pd.Series([100000, 101000, 102000, 101500, 103000, 104000, 105000, 104000, 106000, 107000], index=dates)
        trades = pd.DataFrame([{
            "entry_time": dates[0], "exit_time": dates[1], "pnl_pct": 0.01
        }])

        m = calculate_metrics(equity, trades)

        self.assertGreater(m["cagr"], 0)
        self.assertGreater(m["sharpe"], 0)
        self.assertEqual(m["total_trades"], 1)

if __name__ == '__main__':
    unittest.main()
