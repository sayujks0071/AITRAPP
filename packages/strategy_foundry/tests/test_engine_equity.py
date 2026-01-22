import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from packages.strategy_foundry.backtest.engine import BacktestEngine

class TestBacktestBug(unittest.TestCase):
    def test_equity_curve_length_and_alignment(self):
        # 1. Create Data with Valid Market Hours (e.g., 10:00 AM)
        # Use weekdays (Jan 1 2024 is Monday)
        dates = [datetime(2024, 1, 1, 10, 0) + timedelta(days=i) for i in range(10)]
        # Skip weekends if any?
        # Jan 6, 7 are Sat, Sun.
        # Let's just use same day, different times to ensure market open.
        # 9:15, 9:20, ...
        dates = [datetime(2024, 1, 1, 9, 15) + timedelta(minutes=5*i) for i in range(10)]

        data = pd.DataFrame({
            "open": [100.0]*10,
            "high": [110.0]*10,
            "low": [90.0]*10,
            "close": [105.0]*10
        }, index=dates)

        # 2. Strategy
        # i=0 (09:15): Entry Signal -> Enter at Open[1] (09:20)
        # i=2 (09:25): Exit Signal -> Exit at Open[3] (09:30)

        class MockStrategy:
            def calculate_signals(self, data):
                entries = pd.Series(0, index=data.index)
                exits = pd.Series(False, index=data.index)

                # Signal at index 0 -> Enter at index 1
                entries.iloc[0] = 1

                # Signal at index 2 -> Exit at index 3
                exits.iloc[2] = True

                return entries, exits

            def get_risk_params(self):
                return {}

        strategy = MockStrategy()

        # 3. Run Engine
        engine = BacktestEngine(initial_capital=10000.0)
        equity, trades = engine.run(strategy, data)

        print(f"Data Length: {len(data)}")
        print(f"Equity Curve Length: {len(equity)}")
        print(f"Trades: {len(trades)}")

        if trades:
            print("Trade details:", trades[0])

        # 4. Verify
        self.assertEqual(len(equity), len(data), f"Equity curve length mismatch! Got {len(equity)}, expected {len(data)}")

if __name__ == "__main__":
    unittest.main()
