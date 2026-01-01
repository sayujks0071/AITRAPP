"""Backtest Engine and Core Logic"""
import pandas as pd
from typing import Dict, Any
import logging
from packages.strategy_foundry.factory.grammar import StrategyGrammar
from packages.strategy_foundry.backtest.metrics import calculate_metrics

logger = logging.getLogger(__name__)

class BacktestEngine:
    def __init__(self, df: pd.DataFrame, initial_capital: float, costs_bps: float, slippage_bps: float):
        self.df = df
        self.initial_capital = initial_capital
        self.costs_pct = costs_bps / 10000.0
        self.slippage_pct = slippage_bps / 10000.0

    def run(self, strategy_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run backtest for a single strategy.
        Returns metrics dictionary.
        """
        grammar = StrategyGrammar(strategy_spec)
        signals = grammar.generate_signals(self.df)

        # Execution Logic: Next Open
        # Signal today (at close) -> Trade tomorrow Open

        # Shift signals to represent positions held
        # If signal[t] = 1, we enter at open[t+1].
        # So position[t+1] is 1.
        positions = signals.shift(1).fillna(0)

        # Calculate Returns
        # Strategy Return = Position * (Close - Open) / Open ???
        # Wait, if we enter at Open, the daily return is (Close - Open) / Open.
        # But we hold overnight? The prompt says "Daily timeframe".
        # Standard Daily Backtest:
        # Enter Open[t]. Exit Open[t+1] if signal changes? Or hold until signal changes.

        # Simpler Vectorized approach for "Next Open" execution:
        # PnL[t] = Position[t] * (Open[t+1] - Open[t]) / Open[t]  <-- This assumes we roll position at Open
        # Or more accurately for continuous holding:
        # PnL[t] = Position[t] * (Close[t] - Close[t-1]) / Close[t-1] -- This is Close-to-Close
        # BUT we execute at Open.

        # Let's align:
        # Signal calculated on Close[t].
        # Trade happens at Open[t+1].
        # So from Open[t+1] to Open[t+2], we hold the position determined by Signal[t].

        # Adjusted Price Series (with slippage)
        # It's hard to fully vectorize slippage/costs with varying turnover.
        # We will iterate or use a turnover proxy.

        # Turnover: sum(abs(positions - positions.shift(1)))
        trades = positions.diff().fillna(0).abs()

        # Log Returns (Close-to-Close for simplicity as proxy, or Open-to-Open)
        # Using Open-to-Open matches the execution model best.
        # Return[t] = (Open[t] - Open[t-1]) / Open[t-1]
        # Strategy Return[t] = Position[t-1] * Return[t] - Cost

        market_returns = self.df["Open"].pct_change().fillna(0)

        # Strategy returns
        # Position[t-1] determines exposure for Return[t]
        strategy_returns = positions.shift(1).fillna(0) * market_returns

        # Subtract Costs
        # Trade happened at t-1 close (logically) or t open?
        # Trades vector aligns with position changes.
        # Cost is incurred when position changes.
        # trades[t] is change from pos[t-1] to pos[t].
        # This trade happens at Open[t] (effectively).
        # So we subtract cost from Return[t].

        # Cost = Value Traded * (Cost% + Slippage%)
        # Value Traded approx 1.0 (100% equity).
        costs = trades * (self.costs_pct + self.slippage_pct)

        net_returns = strategy_returns - costs

        # Equity Curve
        equity_curve = (1 + net_returns).cumprod() * self.initial_capital

        # Metrics
        metrics = calculate_metrics(net_returns, equity_curve, trades, self.initial_capital)

        return {
            "metrics": metrics,
            "equity_curve": equity_curve.tolist() # for plotting/storage
        }
