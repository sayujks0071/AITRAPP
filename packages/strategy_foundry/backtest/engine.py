import pandas as pd
import numpy as np
from typing import Dict, Any, List
import structlog

# Simple Backtest Engine for Strategy Foundry
# Daily Timeframe
# Execution: Next Bar Open
# Vectorized/Loop Hybrid

logger = structlog.get_logger(__name__)

class BacktestResult:
    def __init__(self, trades: pd.DataFrame, equity_curve: pd.Series, stats: Dict[str, Any]):
        self.trades = trades
        self.equity_curve = equity_curve
        self.stats = stats

class Engine:
    def __init__(self, data: pd.DataFrame, initial_capital: float = 100000.0,
                 slippage_bps: float = 5.0, cost_bps: float = 10.0):
        self.data = data
        self.initial_capital = initial_capital
        self.slippage = slippage_bps / 10000.0
        self.cost = cost_bps / 10000.0

    def run(self, signals: pd.Series) -> BacktestResult:
        """
        Run backtest.
        signals: Series of target positions (-1, 0, 1) indexed by date.
        Interpretation: Signal at index `t` executes at `Open` of `t+1`.
        """
        # Align signals with data
        # Shift signals by 1 to represent "Action at Next Open"
        # If signal[t] = 1, then position[t+1] should be 1.

        # Current Position held at END of day t
        # If we execute at Open t, the position covers the day t.
        # Wait. "Execution: next-bar open".
        # Signal generated at Close of Day T.
        # Trade happens at Open of Day T+1.
        # So Position for Day T+1 is determined by Signal at T.

        # Let `pos` be the position held during the day.
        # pos[t] comes from signal[t-1].

        pos = signals.shift(1).fillna(0)

        # Calculate Returns
        # Strategy Return = Position[t] * (Close[t] - Open[t]) / Open[t] ??
        # Or (Close[t] - Close[t-1])/Close[t-1]?
        # If we enter at Open[t], our return for day t is (Close[t] - Open[t]).
        # But we also hold overnight?
        # Usually strategy positions are "Target Position".
        # If pos[t] == pos[t-1], we hold.
        # Return is (Close[t] - Close[t-1]) / Close[t-1].

        # But if we change position at Open[t]?
        # Then on Day T:
        # We hold pos[t] from Open[t] to Close[t].
        # Return = pos[t] * (Close[t] - Open[t]) / Open[t] ... plus gap?
        # No, if we execute at Open, we capture Open->Close movement.
        # What about Close[t-1] -> Open[t] gap?
        # That belongs to pos[t-1].

        # Accurate PnL:
        # Day T:
        # Gap PnL = pos[t-1] * (Open[t] - Close[t-1])
        # Intraday PnL = pos[t] * (Close[t] - Open[t])
        # Total PnL = Gap + Intraday
        # Total Return = PnL / Close[t-1]

        # Let's vectorize this.

        opens = self.data['open']
        closes = self.data['close']
        prev_closes = closes.shift(1)
        prev_pos = pos.shift(1).fillna(0)

        # Gap return
        gap_ret = (opens - prev_closes) / prev_closes * prev_pos

        # Intraday return
        intra_ret = (closes - opens) / opens * pos

        # Note: Denominators are approximations of capital base.
        # Strictly: PnL / Capital.
        # Assume 100% allocation.

        # Combine
        # This is approximation (sum of logs or simple sum for small returns).
        # Let's use simple returns.
        # Strategy Daily Return approx = gap_ret + intra_ret
        # (ignoring compounding within the day for gap+intra)

        strat_ret = gap_ret.fillna(0) + intra_ret.fillna(0)

        # Costs
        # Trades occur when pos[t] != pos[t-1]
        # We trade at Open[t].
        trades_mask = (pos != prev_pos)

        # Cost penalty: applied on turnover
        # Turnover value approx = abs(pos - prev_pos) * 1.0 (since 100% equity)
        turnover = abs(pos - prev_pos)

        # Cost deduction
        # slippage + commission
        total_cost_bps = self.slippage + self.cost
        cost_deduction = turnover * total_cost_bps

        net_ret = strat_ret - cost_deduction

        # Equity Curve
        equity_curve = (1 + net_ret).cumprod() * self.initial_capital

        # Generate Trade List
        trades_list = []
        # Identify trade entry/exits
        # This is bit harder to vectorise perfectly for trade table, but we can loop the transitions
        trade_indices = trades_mask[trades_mask].index

        current_trade = {}

        # Simple loop for trade stats
        for d in trade_indices:
            p_curr = pos[d]
            p_prev = prev_pos[d]

            # Close previous trade
            if p_prev != 0:
                # We are closing or flipping
                # Exit Price = Open[d]
                pass

        # Actually, for "trades table", we just need to list actions.
        # Or matched trades (Entry -> Exit).
        # Let's stick to vector stats for metrics first, as table is secondary for now.

        stats = {
            "total_return": (equity_curve.iloc[-1] / self.initial_capital) - 1 if not equity_curve.empty else 0,
            "cagr": self._cagr(equity_curve),
            "max_drawdown": self._max_dd(equity_curve),
            "sharpe": self._sharpe(net_ret),
            "trades": trades_mask.sum()
        }

        return BacktestResult(pd.DataFrame(), equity_curve, stats)

    def _cagr(self, equity: pd.Series) -> float:
        if equity.empty: return 0.0
        days = (equity.index[-1] - equity.index[0]).days
        if days <= 0: return 0.0
        total_ret = equity.iloc[-1] / equity.iloc[0]
        return (total_ret ** (365.0/days)) - 1

    def _max_dd(self, equity: pd.Series) -> float:
        if equity.empty: return 0.0
        peak = equity.cummax()
        dd = (equity - peak) / peak
        return abs(dd.min())

    def _sharpe(self, returns: pd.Series) -> float:
        if returns.empty or returns.std() == 0: return 0.0
        return np.sqrt(252) * returns.mean() / returns.std()
