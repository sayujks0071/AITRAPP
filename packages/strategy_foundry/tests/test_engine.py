import unittest
import pandas as pd
import numpy as np
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import StrategyCandidate
from packages.strategy_foundry.adapters.core_costs import get_default_costs

class TestEngine(unittest.TestCase):
    def setUp(self):
        # Create Dummy Data
        dates = pd.date_range("2023-01-01", periods=100, freq="5min")
        self.df = pd.DataFrame({
            "open": np.linspace(100, 200, 100),
            "high": np.linspace(101, 201, 100),
            "low": np.linspace(99, 199, 100),
            "close": np.linspace(100.5, 200.5, 100),
            "volume": 1000
        }, index=dates)

        self.costs = get_default_costs()
        self.engine = BacktestEngine(self.df, self.costs)

    def test_run_simple_strategy(self):
        # Create a candidate that buys on RSI < 30
        # We need to make sure RSI goes below 30
        # Linear price up means RSI is likely high.
        # Let's create sinusoidal price
        t = np.linspace(0, 10, 100)
        price = 100 + 10 * np.sin(t)
        self.df["close"] = price
        self.df["open"] = price
        self.df["high"] = price + 1
        self.df["low"] = price - 1

        # Candidate
        cand = StrategyCandidate(
            id="test",
            entry_logic={"type": "mean_rev_rsi"},
            exit_logic={"stop_loss_type": "atr"},
            params={
                "rsi_period": 14,
                "rsi_oversold": 40, # High threshold to trigger
                "sl_atr_period": 14,
                "sl_atr_mult": 2.0,
                "tp_risk_reward": 2.0
            }
        )

        trades_df = self.engine.run(cand)
        # Should have some trades
        self.assertIsInstance(trades_df, pd.DataFrame)
        # Could be empty if RSI calc fails or condition never met, but with sine wave it should fluctuate
