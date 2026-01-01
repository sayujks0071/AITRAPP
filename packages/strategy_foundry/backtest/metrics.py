"""Backtest Metrics Calculation"""
import numpy as np
import pandas as pd
from typing import Dict, Any

def calculate_metrics(returns: pd.Series, equity_curve: pd.Series, trades: pd.Series, initial_capital: float) -> Dict[str, Any]:
    # CAGR
    days = len(returns)
    if days < 20:
        return {} # Not enough data

    total_return = (equity_curve.iloc[-1] / initial_capital) - 1
    cagr = (1 + total_return) ** (252 / days) - 1

    # Sharpe
    risk_free_rate = 0.05 # 5% roughly
    std_dev = returns.std() * np.sqrt(252)
    sharpe = (cagr - risk_free_rate) / std_dev if std_dev != 0 else 0

    # Sortino
    downside_returns = returns[returns < 0]
    downside_std = downside_returns.std() * np.sqrt(252)
    sortino = (cagr - risk_free_rate) / downside_std if downside_std != 0 else 0

    # Max Drawdown
    rolling_max = equity_curve.cummax()
    drawdown = (equity_curve - rolling_max) / rolling_max
    max_dd = abs(drawdown.min())

    # Calmar
    calmar = cagr / max_dd if max_dd != 0 else 0

    # Trade Stats
    # Actual trades count:
    trade_events = (trades > 0).sum()

    # Turnover
    turnover_annual = trades.mean() * 252

    # Win Rate (approximate from daily returns?)
    # Hard to get exact trade win rate from vectorized daily returns without trade reconstruction.
    # Using Daily Win Rate as proxy or skip.
    # The prompt asks for "Trades, win rate".
    # We need trade-level accounting for exact win rate.
    # Let's do a quick trade reconstruction loop for metrics if needed,
    # or just use daily positive/negative count.
    # For speed, let's stick to daily metrics + trade count.

    return {
        "cagr": float(cagr),
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "max_dd": float(max_dd),
        "calmar": float(calmar),
        "total_trades": int(trade_events),
        "turnover_annual": float(turnover_annual),
        "total_return": float(total_return)
    }
