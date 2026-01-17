import pandas as pd
import numpy as np
from typing import Dict

def calculate_metrics(trades_df: pd.DataFrame, initial_capital: float = 100000.0) -> Dict[str, float]:
    """
    Calculate comprehensive performance metrics.
    """
    if trades_df.empty:
        return {
            "cagr": 0.0,
            "max_dd": 0.0,
            "sharpe": 0.0,
            "calmar": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "trades": 0
        }

    # Simple PnL based metrics
    # Note: For rigorous backtesting, we need equity curve.
    # Here we approximate from trade list.

    pnls = trades_df["pnl"]
    wins = pnls[pnls > 0]
    losses = pnls[pnls <= 0]

    gross_profit = wins.sum()
    gross_loss = abs(losses.sum())

    profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
    win_rate = len(wins) / len(trades_df)

    # Drawdown (approximate from cumulative pnl)
    equity = initial_capital + pnls.cumsum()
    peak = equity.cummax()
    dd = (peak - equity) / peak
    max_dd = dd.max()

    # Sharpe
    # Assuming daily returns logic roughly? Or per-trade?
    # Standard is annualized from period returns.
    # Let's use simple per-trade stats for ranking for now.
    avg_trade = pnls.mean()
    std_trade = pnls.std()
    sharpe = (avg_trade / std_trade * np.sqrt(len(trades_df))) if std_trade != 0 else 0

    return {
        "cagr": 0.0, # Requires time duration
        "max_dd": max_dd,
        "sharpe": sharpe,
        "calmar": 0.0, # TODO
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "trades": len(trades_df)
    }
