import unittest
import pandas as pd
import numpy as np
import datetime
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import StrategyCandidate, StrategyBlock

class TestEngine(unittest.TestCase):
    def setUp(self):
        # Create Synthetic Data
        # 100 bars
        dates = pd.date_range("2023-01-01 09:15", periods=100, freq="15min")

        # Flat then massive jump
        open_arr = np.array([100.0] * 100)
        # Jump at index 10 (09:15 + 2.5h = 11:45) - Valid time
        open_arr[10:] = 120.0

        high_arr = open_arr + 1.0
        low_arr = open_arr - 1.0
        close_arr = open_arr + 0.5

        self.df = pd.DataFrame({
            "open": open_arr,
            "high": high_arr,
            "low": low_arr,
            "close": close_arr,
            "volume": [1000] * 100
        }, index=dates)

        # Simple Strategy: Breakout
        entry = StrategyBlock("DonchianBreakout", {"period": 5}) # Lower period
        # Exit: Time Stop 5 bars
        exits = [StrategyBlock("TimeStop", {"max_bars": 5})]
        # No filter
        filters = []

        self.candidate = StrategyCandidate(entry, exits, filters, "15m")

    def test_run_simple(self):
        engine = BacktestEngine(self.df)
        res = engine.run(self.candidate)

        trades = res["trades"]
        self.assertFalse(trades.empty)
        self.assertIn("pnl_pct", trades.columns)

    def test_indicators_computed(self):
        engine = BacktestEngine(self.df)
        engine._compute_indicators(self.df, self.candidate)

        # Check if Donchian cols exist
        self.assertIn("dc_upper_5", self.df.columns)

if __name__ == '__main__':
    unittest.main()
