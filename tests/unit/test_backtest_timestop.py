
import unittest

import pandas as pd

from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import Strategy


class MockStrategy(Strategy):
    """
    Mock strategy that forces an entry at the first bar.
    """
    def __init__(self, exit_blocks):
        # We only care about exit blocks for this test
        # Pass empty lists for entry_blocks and filters, they are not used by MockStrategy.calculate_signals
        super().__init__([], exit_blocks, [])

    def calculate_signals(self, df: pd.DataFrame):
        entries = pd.Series(0, index=df.index)
        exits = pd.Series(False, index=df.index)

        # Force Entry Long at first bar (09:15)
        if len(df) > 0:
            entries.iloc[0] = 1

        return entries, exits

class TestBacktestTimeStop(unittest.TestCase):
    def test_time_stop_timestamp_correctness(self):
        # Create small DF
        dates = pd.date_range(start="2024-01-01 09:15", periods=10, freq="5min")
        df = pd.DataFrame({
            "open": [100.0]*10,
            "high": [105.0]*10,
            "low": [95.0]*10,
            "close": [101.0]*10,
            "volume": [1000]*10
        }, index=dates)

        # Standard Engine
        engine = BacktestEngine(initial_capital=100000.0)

        # Strategy with Time Stop of 1 bar
        # Note: BacktestEngine logic is: bars_held = current_idx - entry_idx
        # If bars_held >= time_stop_bars, exit.
        # Entry at i=1 (09:20).
        # i=2 (09:25): bars_held = 1. Exit triggered.
        # Execution at Open of i+1 (09:30).
        # So duration is 09:20 to 09:30 (10 mins, 2 bars).
        # The engine effectively interprets "time_stop_bars" as "minimum full bars to hold BEFORE checking exit condition".
        strategy = MockStrategy(exit_blocks=[{"type": "time_stop", "params": {"bars": 1}}])

        equity, trades = engine.run(strategy, df)

        self.assertEqual(len(trades), 1)
        t = trades[0]

        # Signal at 09:15 (i=0).
        # Entry at Open of next bar (i=1) => 09:20.
        expected_entry_ts = pd.Timestamp("2024-01-01 09:20:00")
        self.assertEqual(t["entry_time"], expected_entry_ts)

        # Based on current engine logic (verified by manual trace):
        # Exit should happen at 09:30.
        expected_exit_ts = pd.Timestamp("2024-01-01 09:30:00")

        self.assertEqual(t["exit_time"], expected_exit_ts,
                         f"Expected exit time {expected_exit_ts}, got {t['exit_time']}")
        self.assertEqual(t["reason"], "time_stop")

if __name__ == "__main__":
    unittest.main()
