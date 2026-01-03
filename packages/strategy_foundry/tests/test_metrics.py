import unittest
from packages.strategy_foundry.backtest.metrics import compute_metrics

class TestMetrics(unittest.TestCase):
    def test_compute_metrics(self):
        trades = [
            {'pnl': 0.05},
            {'pnl': -0.02},
            {'pnl': 0.10}
        ]

        m = compute_metrics(trades)

        self.assertEqual(m['trades'], 3)
        self.assertAlmostEqual(m['net_return'], 0.13)
        self.assertTrue(m['sharpe'] > 0)
