import unittest
import pandas as pd
import numpy as np
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import StrategyType, FilterType, ExitType

class TestEngine(unittest.TestCase):
    def setUp(self):
        self.engine = BacktestEngine()
        # Create dummy data
        dates = pd.date_range(start="2023-01-01 09:15", periods=100, freq="5min")
        self.df = pd.DataFrame({
            "open": np.arange(100, 200),
            "high": np.arange(101, 201),
            "low": np.arange(99, 199),
            "close": np.arange(100.5, 200.5),
            "volume": 1000
        }, index=dates)

    def test_run_breakout(self):
        spec = {
            "strategy_type": StrategyType.BREAKOUT_DONCHIAN.value,
            "strategy_params": {"period": 10},
            "filter_type": FilterType.NO_FILTER.value,
            "filter_params": {},
            "exit_type": ExitType.FIXED_RR.value,
            "exit_params": {"sl_mult": 2.0, "tp_mult": 4.0},
            "session_close_time": "15:25"
        }

        # Donchian will have period 10.
        # Data is constantly rising.
        # Breakout should trigger constantly after period 10.

        res = self.engine.run(self.df, spec)
        trades = res["trades"]
        # Should have trades
        self.assertTrue(len(trades) > 0)

        # Check Final Position
        self.assertIn("final_position", res)

    def test_sanity_metrics(self):
        # Empty run
        spec = {
            "strategy_type": StrategyType.BREAKOUT_DONCHIAN.value,
            "strategy_params": {"period": 200}, # Period longer than data
            "filter_type": FilterType.NO_FILTER.value,
            "filter_params": {},
            "exit_type": ExitType.FIXED_RR.value,
            "exit_params": {"sl_mult": 2.0, "tp_mult": 4.0}
        }
        res = self.engine.run(self.df, spec)
        self.assertEqual(len(res["trades"]), 0)
        self.assertEqual(res["metrics"]["sharpe"], -99.9) # Default for no trades
