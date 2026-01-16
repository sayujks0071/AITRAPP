import unittest
import pandas as pd
import numpy as np
from packages.strategy_foundry.backtest.metrics import calculate_metrics

class TestMetrics(unittest.TestCase):
    def test_calculate_metrics_empty(self):
        df = pd.DataFrame()
        m = calculate_metrics(df)
        self.assertEqual(m['total_trades'], 0)
        self.assertEqual(m['sharpe'], 0.0)

    def test_calculate_metrics_basic(self):
        trades = pd.DataFrame({
            "net_return": [0.01, 0.02, -0.01, 0.03],
            "bars_held": [5, 5, 5, 5]
        })
        m = calculate_metrics(trades)
        self.assertEqual(m['total_trades'], 4)
        self.assertGreater(m['net_return'], 0.0)
        self.assertGreater(m['sharpe'], 0.0)
