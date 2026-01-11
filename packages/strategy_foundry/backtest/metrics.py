import pandas as pd
import numpy as np
from typing import Dict, Any

def calculate_metrics(trades_df: pd.DataFrame, initial_capital: float = 100000.0) -> Dict[str, float]:
    if trades_df.empty:
        return {
            "total_return": 0.0,
            "cagr": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_drawdown": 0.0,
            "calmar": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "trades": 0
        }

    # Simple Metrics based on trade returns
    returns = trades_df["return_pct"]

    total_return = returns.sum() # Simple sum (log returns would be additive, pct returns arithmetic approx)
    # Compounded: (1+r1)*(1+r2)...
    total_ret_comp = (1 + returns).prod() - 1

    wins = returns[returns > 0]
    losses = returns[returns <= 0]

    win_rate = len(wins) / len(returns) if len(returns) > 0 else 0

    avg_win = wins.mean() if not wins.empty else 0
    avg_loss = losses.mean() if not losses.empty else 0

    profit_factor = abs(wins.sum() / losses.sum()) if not losses.empty and losses.sum() != 0 else 999.0

    # To get Sharpe/Drawdown properly, we need a time series of equity.
    # Reconstructing rough equity curve from trade exits (sparse)
    # Ideally backtest engine returns daily equity.
    # For MVP fast evaluation, trade stats might suffice for Ranker?
    # No, Ranker wants Sharpe/MaxDD.

    # We will approximate Sharpe from trade returns assuming 1 trade at a time.
    # Annualized Sharpe = mean(ret) / std(ret) * sqrt(TradesPerYear) ?
    # Or sqrt(252) if daily.

    # Let's use the trade exit timestamps to determine duration.
    start_date = trades_df["entry_time"].min()
    end_date = trades_df["exit_time"].max()
    duration_days = (end_date - start_date).days
    years = max(duration_days / 365.25, 0.01)

    cagr = (1 + total_ret_comp) ** (1 / years) - 1

    # Estimate Drawdown from cumulative returns
    cum_ret = (1 + returns).cumprod()
    peak = cum_ret.cummax()
    dd = (cum_ret - peak) / peak
    max_dd = dd.min() # Negative value

    # Sharpe (Trade based)
    # Not strictly time-based Sharpe, but a proxy "Trade Sharpe"
    # To be comparable to standard Sharpe (daily), we need daily returns.
    # We will accept Trade Sharpe for now or 0 if single trade.

    std_dev = returns.std()
    sharpe = (returns.mean() / std_dev) * np.sqrt(len(returns)/years) if std_dev > 0 else 0

    calmar = cagr / abs(max_dd) if max_dd != 0 else 0

    return {
        "total_return": total_ret_comp,
        "cagr": cagr,
        "sharpe": sharpe,
        "sortino": 0.0, # TODO
        "max_drawdown": abs(max_dd),
        "calmar": calmar,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "trades": len(trades_df)
    }
