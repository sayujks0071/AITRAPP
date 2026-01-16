"""Tests for Backtest Engine"""
import unittest
import pandas as pd
import numpy as np
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.factory.generator import StrategyCandidate
from packages.strategy_foundry.factory.grammar import Rule, StopLossRule

class MockRule(Rule):
    def generate_signal(self, df, ind):
        return pd.Series(1, index=df.index) # Always Long
    def description(self): return "Mock"

class TestEngine(unittest.TestCase):
    def setUp(self):
        dates = pd.date_range("2023-01-01", periods=100)
        self.df = pd.DataFrame({
            "open": 100 + np.random.randn(100),
            "high": 105 + np.random.randn(100),
            "low": 95 + np.random.randn(100),
            "close": 102 + np.random.randn(100),
            "volume": 1000
        }, index=dates)
        self.engine = BacktestEngine()

    def test_run_simple(self):
        strat = StrategyCandidate(MockRule(), MockRule(), StopLossRule(14, 2.0))
        res = self.engine.run(self.df, strat)

        self.assertIn('metrics', res)
        self.assertIn('equity', res)
        self.assertEqual(len(res['equity']), len(self.df))
