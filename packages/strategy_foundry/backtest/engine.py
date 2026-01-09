import pandas as pd
import numpy as np
from typing import Dict, Any, List
from datetime import datetime
from packages.strategy_foundry.factory.generator import GeneratedStrategy
from packages.strategy_foundry.adapters.core_costs import FoundryCosts

class FastBacktestEngine:
    """
    Vectorized/Iterative backtest engine for Strategy Foundry.
    Optimized for speed (FAST_MODE).
    """

    def __init__(self, data: pd.DataFrame, initial_capital: float = 100000.0, allow_short: bool = False):
        self.data = data
        self.initial_capital = initial_capital
        self.allow_short = allow_short
        self.costs = FoundryCosts()

    def run(self, strategy: GeneratedStrategy) -> Dict[str, Any]:
        """
        Run backtest for a single strategy.
        Returns metrics and curves.
        """
        # 1. Generate Signal Positions (Series of -1, 0, 1)
        # This already includes risk overlay (stops/exits)
        positions = strategy.generate_positions(self.data)

        if not self.allow_short:
            positions[positions < 0] = 0

        # 2. Calculate Returns
        # We assume "Next Open" execution.
        # Position determined at close of day i, entered at Open of day i+1.

        # Shift positions by 1 to represent execution next day
        # pos[i] is position held DURING day i.
        # Generated positions[i] is the target position based on data UP TO close of i.
        # So we enter at Open[i+1]. Thus position held during day i+1 is positions[i].

        # held_pos[i] = positions[i-1]
        held_pos = positions.shift(1).fillna(0)

        # Daily Returns: (Close - PrevClose) / PrevClose?
        # Actually more precise: (Close - Open) + (Open - PrevClose)?
        # Or just (Close[i] - Close[i-1]) / Close[i-1] * held_pos[i]?
        # But this ignores Open/Close gaps if we execute at Open.

        # Accurate PnL:
        # If held_pos[i] == 1:
        #   Buy at Open[i] (if pos changed from 0) OR hold from PrevClose[i-1].
        #   PnL = Close[i] - Open[i] (if new)
        #   PnL = Close[i] - PrevClose[i-1] (if held)

        # Let's simplify:
        # Daily Return of underlying: (Close / PrevClose) - 1
        # Strategy Return = Underlying Return * Held Pos

        # To handle transaction costs, we need to detect trades.
        trades = held_pos.diff().fillna(0) != 0 # True if position changed

        # Vectorized PnL
        pct_change = self.data["close"].pct_change().fillna(0)
        strategy_rets = pct_change * held_pos

        # Subtract costs
        # We estimate cost as bps penalty on trade days
        # Cost applied on full turnover.
        # Turnover approx = 1.0 (100% portfolio) whenever trade happens (0->1, 1->0, 1->-1 is 200%)
        # Trade magnitude = abs(held_pos - prev_pos)
        trade_turnover = held_pos.diff().abs().fillna(0)

        # Total cost bps = slippage + brokerage + tax
        # Approx 10bps (0.1%) per side is conservative
        cost_bps = 0.0010
        costs = trade_turnover * cost_bps

        net_rets = strategy_rets - costs

        # Equity Curve
        equity_curve = (1 + net_rets).cumprod() * self.initial_capital

        # Metrics
        metrics = self._calculate_metrics(net_rets, equity_curve, trades)

        return {
            "metrics": metrics,
            "equity_curve": equity_curve,
            "positions": positions, # Target positions
            "trades": trade_turnover.sum() # Total turnover units
        }

    def _calculate_metrics(self, returns: pd.Series, equity: pd.Series, trades: pd.Series) -> Dict[str, float]:
        total_ret = (equity.iloc[-1] / self.initial_capital) - 1
        n_days = len(returns)
        years = n_days / 252

        if years > 0:
            cagr = (1 + total_ret) ** (1 / years) - 1
        else:
            cagr = 0

        vol = returns.std() * np.sqrt(252)
        sharpe = (cagr - 0.05) / vol if vol > 0 else 0 # Rf = 5%

        # Drawdown
        peaks = equity.cummax()
        dd = (equity - peaks) / peaks
        max_dd = dd.min()

        calmar = cagr / abs(max_dd) if max_dd != 0 else 0

        return {
            "cagr": float(cagr),
            "volatility": float(vol),
            "sharpe": float(sharpe),
            "max_dd": float(max_dd),
            "calmar": float(calmar),
            "total_trades": int(trades.sum())
        }
