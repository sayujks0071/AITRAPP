"""Metrics Calculation"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any

def calculate_metrics(trades: List[Dict], equity_curve: pd.Series, df: pd.DataFrame) -> Dict[str, Any]:
    if not trades:
        return {
            "cagr": 0.0,
            "max_dd": 0.0,
            "sharpe": 0.0,
            "calmar": 0.0,
            "trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0
        }

    trades_df = pd.DataFrame(trades)

    # CAGR
    total_ret = equity_curve.iloc[-1] - 1.0
    days = (equity_curve.index[-1] - equity_curve.index[0]).days
    if days > 0:
        cagr = (1 + total_ret) ** (365/days) - 1
    else:
        cagr = 0.0

    # Max DD
    cum_max = equity_curve.cummax()
    drawdown = (equity_curve - cum_max) / cum_max
    max_dd = abs(drawdown.min())

    # Sharpe (Annualized)
    # Using daily returns of equity curve
    daily_returns = equity_curve.resample("D").last().dropna().pct_change().dropna()
    if len(daily_returns) > 1 and daily_returns.std() > 0:
        sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
    else:
        sharpe = 0.0

    # Calmar
    calmar = cagr / max_dd if max_dd > 0 else 0.0

    # Trade Stats
    wins = trades_df[trades_df["return"] > 0]
    losses = trades_df[trades_df["return"] <= 0]

    win_rate = len(wins) / len(trades)

    gross_profit = wins["return"].sum()
    gross_loss = abs(losses["return"].sum())

    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999.0

    return {
        "cagr": cagr,
        "max_dd": max_dd,
        "sharpe": sharpe,
        "calmar": calmar,
        "trades": len(trades),
        "win_rate": win_rate,
        "profit_factor": profit_factor
    }
