import unittest
import pandas as pd
import numpy as np
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import StrategyCandidate, StrategyRule, Condition, IndicatorDef, Operator

class TestBacktestEngine(unittest.TestCase):
    def setUp(self):
        # Create dummy data
        dates = pd.date_range("2023-01-01", periods=200, freq="5min", tz="Asia/Kolkata")
        # Ensure we span enough time and have price movement to trigger trades
        # Need to be within market hours: 9:15 to 15:30.
        # "2023-01-01" is Sunday. Let's pick a Monday.
        dates = pd.date_range("2023-01-02 09:15", periods=75, freq="5min", tz="Asia/Kolkata") # One day

        self.data = pd.DataFrame({
            "open": np.linspace(100, 200, 75),
            "high": np.linspace(101, 201, 75),
            "low": np.linspace(99, 199, 75),
            "close": np.linspace(100.5, 200.5, 75),
            "volume": np.ones(75) * 1000
        }, index=dates)

        self.engine = BacktestEngine(self.data)

    def test_simple_strategy(self):
        # Strategy: Close > 0 (Always True)
        cond = Condition(
            indicator_a=IndicatorDef("close", {}),
            operator=Operator.GT,
            indicator_b=0
        )
        rule = StrategyRule(
            entry_conditions=[cond],
            exit_conditions=[],
            risk_params={"sl_atr": 1.0, "tp_atr": 1.0, "trailing": False},
            description="Test"
        )
        cand = StrategyCandidate("test_id", rule, "5m")

        res = self.engine.run(cand)
        self.assertIn("trades", res)
        trades = res["trades"]

        # It should trade because market is open and condition is true.
        # The data starts at 9:15.
        self.assertFalse(trades.empty)
        self.assertIn("pnl", trades.columns)

if __name__ == '__main__':
    unittest.main()
