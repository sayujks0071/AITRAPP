import pandas as pd
import numpy as np
from typing import Dict, Any

def calculate_metrics(returns: pd.Series, trades: pd.DataFrame) -> Dict[str, float]:
    if len(returns) < 2:
        return {}

    # Annualization factor
    ann_factor = 252

    # CAGR
    total_ret = (1 + returns).prod() - 1
    n_years = len(returns) / ann_factor
    cagr = (1 + total_ret) ** (1 / n_years) - 1 if n_years > 0 else 0

    # Volatility
    vol = returns.std() * np.sqrt(ann_factor)

    # Sharpe (rf=0)
    sharpe = (cagr / vol) if vol > 0 else 0

    # Sortino
    downside_returns = returns[returns < 0]
    downside_vol = downside_returns.std() * np.sqrt(ann_factor)
    sortino = (cagr / downside_vol) if downside_vol > 0 else 0

    # Max Drawdown
    cum_ret = (1 + returns).cumprod()
    peak = cum_ret.cummax()
    dd = (cum_ret - peak) / peak
    max_dd = dd.min()

    # Calmar
    calmar = (cagr / abs(max_dd)) if max_dd != 0 else 0

    # Trade Stats
    if not trades.empty:
        n_trades = len(trades)
        win_rate = len(trades[trades['pnl'] > 0]) / n_trades
        avg_trade = trades['pnl'].mean()

        winners = trades[trades['pnl'] > 0]['pnl']
        losers = trades[trades['pnl'] <= 0]['pnl']
        profit_factor = abs(winners.sum() / losers.sum()) if not losers.empty and losers.sum() != 0 else 0
    else:
        n_trades = 0
        win_rate = 0
        avg_trade = 0
        profit_factor = 0

    # Stability (Sharpe dispersion)
    # Rolling 6-month Sharpe
    rolling_sharpe = returns.rolling(window=126).apply(lambda x: (x.mean() / x.std() * np.sqrt(252)) if x.std() > 0 else 0)
    stability = 1.0 / (rolling_sharpe.std() + 0.1) # Inverse of dispersion

    return {
        "cagr": cagr,
        "volatility": vol,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_dd": max_dd,
        "calmar": calmar,
        "trades": n_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_trade": avg_trade,
        "stability": stability
    }
