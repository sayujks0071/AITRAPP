import unittest
import pandas as pd
import numpy as np
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import StrategyCandidate, Rule

class TestBacktestEngine(unittest.TestCase):
    def setUp(self):
        # Create dummy data
        dates = pd.date_range("2023-01-01", periods=10, freq="D")
        self.df = pd.DataFrame({
            "open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
            "high": [105, 106, 107, 108, 109, 110, 111, 112, 113, 114],
            "low": [95, 96, 97, 98, 99, 100, 101, 102, 103, 104],
            "close": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
            "atr_14": [1]*10
        }, index=dates)

    def test_run_simple_strategy(self):
        # Strategy: Enter if Open > 0 (Always True)
        # Entry at i=1 (since i starts at 1)

        def rule_always_true(df, params):
            return pd.Series(True, index=df.index)

        strat = StrategyCandidate(
            strategy_id="test",
            entry_rules=[Rule("Always", rule_always_true, {})],
            exit_rules=[],
            risk_params={"sl_atr": 10.0, "tp_atr": 0.0, "max_bars": 0} # Wide stop
        )

        engine = BacktestEngine(initial_capital=10000)
        res = engine.run(strat, self.df)

        trades = res["trades"]
        # Should enter at i=1 (Close[1] signal -> Open[2])?
        # My logic:
        # i=1: sig=1 (based on rule). pending_entry=True.
        # i=2: Execute pending. Entry at Open[2]=102.

        # Check if we have trades
        # If we never exit, we might not have a completed trade in "trades" list depending on implementation?
        # BacktestEngine records trade on EXIT.
        # If open at end, it is not in trades list?
        # My implementation: "if position_qty > 0... check exit".
        # It does NOT close at end of data explicitly.
        # So "trades" might be empty if hold till end.

        # Let's add an exit rule.
        def rule_exit_at_5(df, params):
            s = pd.Series(False, index=df.index)
            s.iloc[5] = True
            return s

        strat.exit_rules = [Rule("Exit", rule_exit_at_5, {})]

        res = engine.run(strat, self.df)
        trades = res["trades"]

        # i=1: Entry Sig -> Pending.
        # i=2: Enter at Open=102.
        # i=5: Exit Sig?
        # s.iloc[5] is True.
        # Loop i=5. Exit Sig detected. Exit at Close[5]=106.
        # Trade: Entry 102, Exit 106.

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades.iloc[0]["entry_price"], 102 * (1 + engine.slippage_bps))
        # Note: BacktestEngine uses slippage on entry and exit.

        self.assertGreater(res["metrics"]["total_return"], 0)

if __name__ == "__main__":
    unittest.main()
