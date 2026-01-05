"""
Strategy Foundry - Metrics.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any

def compute_metrics(equity_curve: pd.Series, trades: pd.DataFrame) -> Dict[str, float]:
    """
    Compute performance metrics.
    """
    if len(equity_curve) < 2:
        return {}

    # CAGR
    start_date = equity_curve.index[0]
    end_date = equity_curve.index[-1]
    years = (end_date - start_date).days / 365.25
    if years <= 0: years = 0.001

    total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
    cagr = (1 + total_return) ** (1/years) - 1

    # Volatility (Annualized)
    daily_returns = equity_curve.pct_change().dropna()
    vol = daily_returns.std() * np.sqrt(252)

    # Sharpe (rf=0)
    sharpe = (cagr / vol) if vol > 0 else 0.0

    # Drawdown
    running_max = equity_curve.cummax()
    drawdown = (equity_curve - running_max) / running_max
    max_dd = drawdown.min()

    # Calmar
    calmar = (cagr / abs(max_dd)) if max_dd != 0 else 0.0

    # Trade Stats
    num_trades = len(trades)
    win_rate = 0.0
    profit_factor = 0.0
    avg_trade = 0.0

    if num_trades > 0:
        win_rate = len(trades[trades["return"] > 0]) / num_trades
        avg_trade = trades["return"].mean()

        gross_profit = trades[trades["return"] > 0]["return"].sum()
        gross_loss = abs(trades[trades["return"] < 0]["return"].sum())

        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        else:
            profit_factor = gross_profit # or inf

    return {
        "cagr": cagr,
        "volatility": vol,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "calmar": calmar,
        "trades": num_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_trade_return": avg_trade
    }
