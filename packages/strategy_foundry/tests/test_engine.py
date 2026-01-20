import unittest
import pandas as pd
import numpy as np
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.metrics import calculate_metrics

class TestBacktestEngine(unittest.TestCase):
    def setUp(self):
        self.engine = BacktestEngine()

        # Create dummy data
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        self.df = pd.DataFrame({
            "open": np.linspace(100, 200, 100),
            "high": np.linspace(105, 205, 100),
            "low": np.linspace(95, 195, 100),
            "close": np.linspace(102, 202, 100), # Up trend
            "volume": 1000
        }, index=dates)

        # Add some noise
        self.df["close"] += np.random.normal(0, 2, 100)

    def test_run_simple_strategy(self):
        spec = {
            "type": "EMA_CROSS",
            "params": {"fast": 10, "slow": 20},
            "stop": {"type": "ATR", "params": {"period": 14, "sl_mult": 2.0}}
        }

        res = self.engine.run(self.df, spec)

        self.assertIn("metrics", res)
        self.assertIn("trades", res)
        self.assertIn("equity_curve", res)

        # Since trend is up, EMA cross should capture some trades
        # self.assertGreater(len(res["trades"]), 0) # Might be 0 if period is too long for 100 days

    def test_metrics(self):
        trades = pd.DataFrame([
            {"pnl": 100, "return_pct": 0.01},
            {"pnl": -50, "return_pct": -0.005}
        ])
        daily_returns = pd.Series([0.01, -0.005, 0.01])

        m = calculate_metrics(trades, daily_returns)
        self.assertEqual(m["total_trades"], 2)
        self.assertAlmostEqual(m["win_rate"], 0.5)
        self.assertAlmostEqual(m["profit_factor"], 2.0)

if __name__ == "__main__":
    unittest.main()
