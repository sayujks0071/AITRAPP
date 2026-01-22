
import unittest
import pandas as pd
import numpy as np
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import StrategyType, FilterType, ExitType

class MockEngine(BacktestEngine):
    def _generate_entry_signal(self, df, spec):
        df["entry_long"] = False
        if len(df) > 0:
            # Signal at first bar (09:15)
            df.iloc[0, df.columns.get_loc("entry_long")] = True

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

        engine = MockEngine()

        spec = {
            "strategy_type": StrategyType.BREAKOUT_DONCHIAN.value,
            "strategy_params": {"period": 2},
            "filter_type": "NONE",
            "filter_params": {},
            "exit_type": ExitType.TIME_BASED.value,
            "exit_params": {"sl_mult": 10.0, "tp_mult": 10.0, "max_bars": 1},
            "session_close_time": "15:25"
        }

        # Mock prepare_indicators to modify in place
        def mock_prepare(df, spec):
            df["atr"] = 1.0

        engine._prepare_indicators = mock_prepare

        res = engine.run(df, spec)
        trades = res["trades"]

        self.assertEqual(len(trades), 1)
        t = trades[0]

        # Signal at 09:15. Entry at Open of 09:20.
        expected_entry_ts = pd.Timestamp("2024-01-01 09:20:00")
        self.assertEqual(t["entry_time"], expected_entry_ts)

        # Held for 1 bar (09:20-09:25).
        # Exit check at end of 09:20 bar. bars_held=1.
        # Exit at Open of 09:25.
        expected_exit_ts = pd.Timestamp("2024-01-01 09:25:00")

        self.assertEqual(t["exit_time"], expected_exit_ts,
                         f"Expected exit time {expected_exit_ts}, got {t['exit_time']}")
        self.assertEqual(t["reason"], "TIME_STOP")

if __name__ == "__main__":
    unittest.main()
