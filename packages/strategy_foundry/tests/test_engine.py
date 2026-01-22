import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import Strategy

class TestBacktestEngine(unittest.TestCase):
    def setUp(self):
        # Generate synthetic data
        # 2023-01-02 is a Monday
        dates = pd.date_range(start="2023-01-02 09:15", periods=100, freq="5min", tz="Asia/Kolkata")
        self.data = pd.DataFrame({
            "open": np.linspace(100, 110, 100),
            "high": np.linspace(101, 111, 100),
            "low": np.linspace(99, 109, 100),
            "close": np.linspace(100.5, 110.5, 100),
            "volume": 1000
        }, index=dates)

        self.engine = BacktestEngine(initial_capital=100000.0)

    def test_simple_long_strategy(self):
        # Manually construct a strategy that enters long at index 10 and exits at index 20
        # We can mock calculate_signals by subclassing or mocking

        class MockStrategy:
            def calculate_signals(self, df):
                entries = pd.Series(0, index=df.index)
                exits = pd.Series(False, index=df.index)

                # Enter Long at index 10
                entries.iloc[10] = 1

                # Exit at index 20
                exits.iloc[20] = True

                return entries, exits

            def get_risk_params(self):
                return {}

        strategy = MockStrategy()
        equity, trades = self.engine.run(strategy, self.data)

        self.assertEqual(len(trades), 1)
        self.assertTrue(equity.iloc[-1] > equity.iloc[0]) # Should be profitable given uptrend data

    def test_time_stop(self):
        class MockStrategy:
            def calculate_signals(self, df):
                entries = pd.Series(0, index=df.index)
                exits = pd.Series(False, index=df.index)
                entries.iloc[10] = 1
                return entries, exits

            def get_risk_params(self):
                return {"time_stop_bars": 5}

        strategy = MockStrategy()
        equity, trades = self.engine.run(strategy, self.data)

        self.assertEqual(len(trades), 1)
        # Entry at 11 (signal at 10), Exit at 11+5 = 16?
        # Logic: bars_held = i - entry_bar_idx. if bars_held >= 5.
        # Check reasons
        self.assertEqual(trades[0]["reason"], "time_stop")

if __name__ == "__main__":
    unittest.main()
