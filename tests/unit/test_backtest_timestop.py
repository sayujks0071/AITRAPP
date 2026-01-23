import unittest
import pandas as pd
from unittest.mock import MagicMock
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import Strategy

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

        engine = BacktestEngine()

        # Mock Strategy
        mock_strategy = MagicMock(spec=Strategy)

        # calculate_signals returns entries, exits
        entries = pd.Series(0, index=df.index)
        entries.iloc[0] = 1 # Long signal at 09:15 (first bar) -> Entry at 09:20

        exits = pd.Series(False, index=df.index)

        mock_strategy.calculate_signals.return_value = (entries, exits)

        # Risk params with time stop
        mock_strategy.get_risk_params.return_value = {"time_stop_bars": 1}

        res_equity, trades = engine.run(mock_strategy, df)

        self.assertEqual(len(trades), 1)
        t = trades[0]

        # Entry at Open of 09:20
        expected_entry_ts = pd.Timestamp("2024-01-01 09:20:00")
        self.assertEqual(t["entry_time"], expected_entry_ts)

        # Expected exit logic:
        # i=0 (09:15): Signal -> Entry set for 09:20 (idx 1)
        # i=1 (09:20): Entry happens. bars_held = 1-1=0. 0 < 1. No exit.
        # i=2 (09:25): bars_held = 2-1=1. 1 >= 1. Exit triggers.
        # Exit executes at Open of i+1 = 3 (09:30).

        expected_exit_ts = pd.Timestamp("2024-01-01 09:30:00")

        self.assertEqual(t["exit_time"], expected_exit_ts,
                         f"Expected exit time {expected_exit_ts}, got {t['exit_time']}")
        self.assertEqual(t["reason"], "time_stop")

if __name__ == "__main__":
    unittest.main()
