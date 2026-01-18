import unittest
import pandas as pd
import numpy as np
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import StrategyCandidate
from packages.strategy_foundry.adapters.core_costs import TransactionCosts

class TestEngine(unittest.TestCase):
    def setUp(self):
        # Create dummy data
        idx = pd.date_range("2023-01-01", periods=100)
        self.df = pd.DataFrame({
            "open": np.linspace(100, 110, 100),
            "high": np.linspace(101, 111, 100),
            "low": np.linspace(99, 109, 100),
            "close": np.linspace(100.5, 110.5, 100),
            "volume": [1000]*100
        }, index=idx)

        # Dummy indicators
        self.indicators = pd.DataFrame({
            "ema_fast": np.linspace(100, 110, 100),
            "ema_slow": np.linspace(99, 109, 100), # Fast > Slow always
            "adx": [30]*100,
            "rsi": [40]*100,
            "supertrend": np.linspace(90, 100, 100),
            "supertrend_dir": [1]*100, # Bullish
            "donchian_upper": [112]*100,
            "bb_lower": [90]*100
        }, index=idx)

        self.engine = BacktestEngine()

    def test_basic_long_strategy(self):
        # Create a candidate that buys if ema_fast > ema_slow (always true)
        params = {
            "entry_type": "ema_cross",
            "use_adx_filter": False,
            "adx_threshold": 20,
            "stop_loss_pct": 5.0,
            "take_profit_pct": 0.0,
            "trailing_stop_activation_pct": 0.0,
            "trailing_stop_callback_pct": 0.0,
            "max_bars_hold": 10,
            "direction": "long_only"
        }
        cand = StrategyCandidate(strategy_id="test", params=params)

        res = self.engine.run(self.df, cand, self.indicators)

        trades = res["trades"]
        # Since it's always Long, and we exit after 10 bars (max_hold), we should have multiple trades.
        # Trade 1: Enter T=1 (Signal at T=0). Exit T=11.
        # Trade 2: Enter T=11 (Signal at T=10, but we were in position until T=11 Open?
        # If we exit at Open of T=11, we are flat. Signal at T=10 says Enter.
        # Do we re-enter same bar?
        # Logic: Position becomes 0 at T=11.
        # Loop continues to check Entry.
        # If signal_prev (T=10) is 1, we Enter at T=11 Open?
        # Yes, re-entry.

        self.assertTrue(len(trades) > 0)
        self.assertTrue("pnl" in trades.columns)

if __name__ == '__main__':
    unittest.main()
