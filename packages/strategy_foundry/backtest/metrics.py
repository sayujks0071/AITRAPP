# StrategyFoundry Implementation
import pandas as pd
import numpy as np
from typing import Dict

def calculate_metrics(equity_curve: pd.Series, trades: list) -> Dict[str, float]:
    """
    Calculate performance metrics.
    """
    if equity_curve.empty or len(trades) == 0:
        return {
            "sharpe": -99.0,
            "calmar": -99.0,
            "cagr": 0.0,
            "max_dd": 100.0,
            "trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0
        }

    # Returns
    returns = equity_curve.pct_change().dropna()

    # CAGR
    days = (equity_curve.index[-1] - equity_curve.index[0]).days
    if days < 1:
        days = 1
    total_ret = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
    cagr = ((1 + total_ret) ** (365 / days)) - 1

    # Volatility (Annualized)
    # Assuming intraday 5m bars? No, equity curve might be sparsely sampled if we only mark on close?
    # Better to resample equity curve to daily for Sharpe/CAGR standard comparisons
    # or keep high freq.
    # Let's use high freq annualized.
    # 5m bars: ~75 per day. 252 days.
    # But equity curve index is timestamps.
    # Let's resample to Daily for robust Sharpe.
    daily_equity = equity_curve.resample("D").last().dropna()
    daily_returns = daily_equity.pct_change().dropna()

    if len(daily_returns) < 2:
        sharpe = 0.0
    else:
        sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)

    # Max Drawdown
    rolling_max = equity_curve.cummax()
    drawdown = (equity_curve - rolling_max) / rolling_max
    max_dd = abs(drawdown.min())

    # Calmar
    calmar = cagr / max_dd if max_dd > 0 else 0.0

    # Trade Stats
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]

    win_rate = len(wins) / len(trades) if len(trades) > 0 else 0.0

    gross_win = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))

    profit_factor = gross_win / gross_loss if gross_loss > 0 else 99.0

    return {
        "sharpe": sharpe,
        "calmar": calmar,
        "cagr": cagr,
        "max_dd": max_dd * 100, # percent
        "trades": len(trades),
        "win_rate": win_rate,
        "profit_factor": profit_factor
    }
