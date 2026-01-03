import unittest
import pandas as pd
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.generator import StrategyCandidate

class TestEngine(unittest.TestCase):
    def test_run_simple(self):
        # Create dummy data
        dates = pd.date_range(start='2023-01-01', periods=100, freq='15T')
        df = pd.DataFrame({
            'open': [100] * 100,
            'high': [105] * 100,
            'low': [95] * 100,
            'close': [100] * 100,
            'volume': [1000] * 100,
            # Indicators
            'ema_10': [100] * 100,
            'ema_20': [99] * 100, # Fast > Slow always
            'ema_50': [98] * 100,
            'ema_200': [90] * 100,
            'atr_14': [1] * 100,
            'rsi_14': [50] * 100,
            'adx_14': [25] * 100
        }, index=dates)

        # Candidate
        cand = StrategyCandidate(
            id="test",
            entry_rules=[{"type": "ema_cross", "fast": 10, "slow": 20}],
            exit_rules=[{"type": "stop_loss_atr", "multiplier": 1.0}],
            filters=[],
            timeframe="15m",
            instrument="NIFTY"
        )

        engine = BacktestEngine(df, cand)
        res = engine.run()

        self.assertIn("trades", res)
        # Since Fast > Slow always, and logic looks for crossover (Fast > Slow AND PrevFast <= PrevSlow),
        # we need to simulate a crossover.

        # Modify data to have crossover
        df.iloc[0:10, df.columns.get_loc('ema_10')] = 90 # Fast < Slow
        df.iloc[10:, df.columns.get_loc('ema_10')] = 110 # Fast > Slow

        engine = BacktestEngine(df, cand)
        res = engine.run()

        # Should have at least one trade
        self.assertTrue(len(res['trades']) > 0)
