import unittest
import pandas as pd
from datetime import datetime
from packages.strategy_foundry.backtest.metrics import calculate_metrics

class TestMetrics(unittest.TestCase):
    def test_calculate_metrics(self):
        trades = pd.DataFrame([
            {"entry_time": datetime(2023,1,1), "exit_time": datetime(2023,1,2), "return": 0.05, "entry_price": 100, "exit_price": 105},
            {"entry_time": datetime(2023,1,3), "exit_time": datetime(2023,1,4), "return": -0.02, "entry_price": 100, "exit_price": 98}
        ])

        m = calculate_metrics(trades)

        self.assertEqual(m["total_trades"], 2)
        self.assertEqual(m["win_rate"], 0.5)
        # Gross profit 0.05, Gross loss 0.02 -> PF 2.5
        self.assertAlmostEqual(m["profit_factor"], 2.5)
        self.assertGreater(m["net_return_pct"], 0)
        self.assertLess(m["max_dd_pct"], 5.0) # approx 2% dd
