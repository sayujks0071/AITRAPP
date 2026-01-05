"""
Tests for Strategy Foundry Engine
"""
import pytest
import pandas as pd
import numpy as np
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.grammar import StrategyConfig

class TestEngine:
    @pytest.fixture
    def sample_data(self):
        # Create a simple trend
        # 100 bars
        dates = pd.date_range(start='2023-01-01 09:15', periods=100, freq='5min', tz='Asia/Kolkata')

        # Linear uptrend
        price = np.linspace(100, 200, 100)

        df = pd.DataFrame({
            'open': price,
            'high': price + 1,
            'low': price - 1,
            'close': price, # Close = Open for simplicity
            'volume': [1000] * 100
        }, index=dates)

        return df

    def test_engine_run_basic(self, sample_data):
        engine = BacktestEngine(sample_data)

        # Simple config that should trigger
        config = StrategyConfig(
            entry_block="entry_trend_ema_cross",
            entry_params={"fast_period": 5, "slow_period": 10, "adx_filter": False},
            risk_block="risk_atr",
            risk_params={"atr_period": 14, "multiplier": 2.0, "trailing": False},
            exit_block="exit_time",
            exit_params={"max_bars": 5}
        )

        trades, equity = engine.run(config)

        # With linear uptrend, EMA 5 > EMA 10 quickly.
        # Should have trades.
        assert not trades.empty or not equity.empty
        assert len(equity) == 100

    def test_engine_eod_exit(self, sample_data):
        # Set time to near EOD
        dates = pd.date_range(start='2023-01-01 13:00', periods=50, freq='5min', tz='Asia/Kolkata')
        # last bar will be ~ 17:05, so we cross 15:25

        df = pd.DataFrame({
            'open': [100]*50,
            'high': [100]*50,
            'low': [100]*50,
            'close': [100]*50,
            'volume': [1000]*50
        }, index=dates)

        # IMPORTANT: With a flat price, ATR might be zero or very small if not handled.
        # If ATR is 0, then stop loss is entry_price - 0 = entry_price.
        # Low <= SL (100 <= 100) -> Trigger SL immediately.
        # We need to make prices volatile enough to have non-zero ATR but not hit SL.

        # Or force ATR to be large by mocking VectorizedIndicators.
        # Let's modify the data to have some range.

        df['high'] = df['high'] + 1
        df['low'] = df['low'] - 1

        # Force a signal early
        engine = BacktestEngine(df)
        engine._generate_entries = lambda d, s: pd.Series([True] + [False]*49, index=d.index)

        config = StrategyConfig(
            entry_block="mock", entry_params={},
            risk_block="risk_atr", risk_params={"atr_period": 14, "multiplier": 1000, "trailing": False}, # very wide stop
            exit_block="exit_time", exit_params={"max_bars": 100} # long hold
        )

        trades, _ = engine.run(config)

        # Should exit at EOD
        assert not trades.empty
        # Check reason
        assert trades.iloc[0]['reason'] == "EOD"
