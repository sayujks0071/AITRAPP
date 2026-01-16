import unittest
import pandas as pd
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.costs import CostModel
from packages.strategy_foundry.factory.grammar import StrategyConfig, Rule
from packages.strategy_foundry.factory.generator import StrategyGenerator

class TestEngine(unittest.TestCase):
    def setUp(self):
        self.cost_model = CostModel(5.0, 20.0, 2.0, 3.0)
        self.engine = BacktestEngine(self.cost_model)

    def test_run_empty(self):
        df = pd.DataFrame()
        # Create dummy config
        config = StrategyConfig("test", [], [], 1.0, 1.0, None, 10)
        trades = self.engine.run(df, config)
        self.assertTrue(trades.empty)

    def test_basic_trade(self):
        # Create synthetic data
        dates = pd.date_range("2021-01-01", periods=100, freq="5T")
        df = pd.DataFrame({
            "datetime": dates,
            "open": [100]*100,
            "high": [105]*100,
            "low": [95]*100,
            "close": [100]*100,
            "volume": [1000]*100
        })

        # Rule: Close > 0 (Always True)
        rule = Rule("trend", "close", {}, ">", 0)
        config = StrategyConfig("test", [rule], [], 1.0, 2.0, None, 5, exit_time="23:59")

        # Engine run
        trades = self.engine.run(df, config)
        # Should trade continuously?
        # If in_trade, it holds until exit.
        # Exit condition: SL/TP or Time.
        # SL=1.0 ATR. ATR is 0? (High=Low=Close? No High=105, Low=95).
        # TR = 10. ATR will be ~10.
        # SL = 1.0 * 10 = 10. Stop at 90.
        # TP = 2.0 * 10 = 20. Target 120.
        # Max bars = 5.

        # It should enter at index 1 (signal at 0).
        # Exit at index 6 (Time stop).
        # Then re-enter at index 7?

        self.assertFalse(trades.empty)
        self.assertIn("reason", trades.columns)
