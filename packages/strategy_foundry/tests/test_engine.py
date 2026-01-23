import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import StrategyCandidate, StrategyComponent, EntryType, RiskType

class TestEngine(unittest.TestCase):
    def setUp(self):
        # Create synthetic data: 100 bars, uptrend
        dates = pd.date_range("2023-01-02 09:15", periods=200, freq="5min", tz="Asia/Kolkata")

        # Simple uptrend
        # Make close price cross EMA
        close = np.linspace(100, 200, 200)
        # Add some noise
        close += np.sin(np.linspace(0, 10, 200)) * 2

        data = pd.DataFrame({
            "open": close - 0.5,
            "high": close, # No upper wick to ensure breakout logic works on simple uptrend
            "low": close - 1.0,
            "close": close,
            "volume": 1000
        }, index=dates)

        self.data = data
        self.engine = BacktestEngine()

    def test_simple_breakout(self):
        # Create a candidate: Breakout 10, ATR Stop 2.0
        candidate = StrategyCandidate(
            id="test_1",
            entry=StrategyComponent(type="BREAKOUT", params={"period": 10}),
            exit=StrategyComponent(type="ATR_STOP", params={"stop_mult": 2.0, "atr_period": 14}),
            filters=[],
            generation_ts=0
        )

        results = self.engine.run(candidate, self.data)

        self.assertIn("metrics", results)
        self.assertGreater(results["metrics"]["total_trades"], 0)
        self.assertGreater(results["metrics"]["pnl_net"], 0)

        print("\nBreakout Results:")
        print(results["metrics"])

    def test_trend_cross(self):
         # Create a candidate: Trend EMA 9/20
        candidate = StrategyCandidate(
            id="test_2",
            entry=StrategyComponent(type="TREND", params={"fast_period": 10, "slow_period": 30}),
            exit=StrategyComponent(type="ATR_STOP", params={"stop_mult": 2.0, "atr_period": 14}),
            filters=[],
            generation_ts=0
        )

        results = self.engine.run(candidate, self.data)
        self.assertIn("metrics", results)
        print("\nTrend Results:")
        print(results["metrics"])

if __name__ == "__main__":
    unittest.main()
