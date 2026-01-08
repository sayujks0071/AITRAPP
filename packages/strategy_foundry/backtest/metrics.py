"""
Backtest Metrics.
Calculates CAGR, Sharpe, Drawdown, etc.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any

def calculate_metrics(equity_curve: pd.Series, trades: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate performance metrics.
    """
    if equity_curve.empty:
        return {}

    # CAGR
    start_val = equity_curve.iloc[0]
    end_val = equity_curve.iloc[-1]
    days = (equity_curve.index[-1] - equity_curve.index[0]).days
    years = days / 365.25
    if years > 0 and start_val > 0:
        cagr = (end_val / start_val) ** (1 / years) - 1
    else:
        cagr = 0.0

    # Returns
    returns = equity_curve.pct_change().dropna()

    # Sharpe (Annualized) - assuming daily data
    if returns.std() > 0:
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
    else:
        sharpe = 0.0

    # Sortino
    downside = returns[returns < 0]
    if downside.std() > 0:
        sortino = (returns.mean() / downside.std()) * np.sqrt(252)
    else:
        sortino = 0.0 if returns.mean() <= 0 else 100.0 # High if no downside

    # Drawdown
    peak = equity_curve.cummax()
    dd = (equity_curve - peak) / peak
    max_dd = dd.min()

    # Calmar
    calmar = 0.0
    if max_dd < 0:
        calmar = cagr / abs(max_dd)

    # Trade Stats
    total_trades = len(trades)
    win_rate = 0.0
    profit_factor = 0.0
    avg_trade = 0.0

    if total_trades > 0:
        wins = trades[trades["pnl"] > 0]
        losses = trades[trades["pnl"] <= 0]
        win_rate = len(wins) / total_trades

        gross_profit = wins["pnl"].sum()
        gross_loss = abs(losses["pnl"].sum())

        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        else:
            profit_factor = float('inf') if gross_profit > 0 else 0.0

        avg_trade = trades["return"].mean()

    # Stability (R-squared of log equity or Sharpe dispersion)
    # Simple proxy: 252d Sharpe dispersion?
    # Let's use annualized vol
    vol = returns.std() * np.sqrt(252)

    return {
        "cagr": cagr,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_dd": max_dd, # negative number
        "calmar": calmar,
        "volatility": vol,
        "total_trades": total_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_trade_return": avg_trade
    }
