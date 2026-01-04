import unittest
import pandas as pd
import numpy as np
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import Strategy

class TestEngine(unittest.TestCase):
    def setUp(self):
        # Create dummy data
        dates = pd.date_range(start="2023-01-01", periods=100)
        self.df = pd.DataFrame({
            "open": np.linspace(100, 200, 100),
            "high": np.linspace(105, 205, 100),
            "low": np.linspace(95, 195, 100),
            "close": np.linspace(102, 202, 100),
            "volume": [1000]*100
        }, index=dates)

    def test_basic_run(self):
        # Simple strategy that always enters
        config = {
            "blocks": [
                {"type": "ema_cross", "category": "entry", "params": {"fast": 5, "slow": 10}}, # Won't trigger easily on linear data without crossover
                # Let's force a simpler condition or mock generate_positions
            ]
        }

        # We can subclass Strategy to force positions for testing
        class MockStrategy(Strategy):
            def generate_positions(self, df):
                return pd.Series([1]*len(df), index=df.index)

        strategy = MockStrategy(config)
        engine = BacktestEngine()
        metrics = engine.run(strategy, self.df)

        self.assertIn("total_return", metrics)
        self.assertIn("sharpe", metrics)
        self.assertGreater(metrics["cagr"], 0)

if __name__ == '__main__':
    unittest.main()
