import numpy as np
import pandas as pd
from typing import Dict

def calculate_max_drawdown(equity_curve: pd.Series) -> float:
    """Calculate Maximum Drawdown (percentage)"""
    if equity_curve.empty:
        return 0.0

    running_max = equity_curve.cummax()
    drawdown = (equity_curve - running_max) / running_max
    return float(drawdown.min())

def calculate_metrics(trades: pd.DataFrame, initial_capital: float = 100000.0) -> Dict[str, float]:
    """
    Calculate comprehensive metrics from trades list.
    trades DataFrame columns: [entry_time, exit_time, entry_price, exit_price, pnl, return_pct, duration]
    """
    if trades.empty:
        return {
            "total_return": 0.0,
            "cagr": 0.0,
            "max_dd": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "trades": 0,
            "avg_trade": 0.0
        }

    total_pnl = trades["pnl"].sum()
    total_return = total_pnl / initial_capital

    # Win Rate
    wins = trades[trades["pnl"] > 0]
    losses = trades[trades["pnl"] <= 0]
    win_rate = len(wins) / len(trades)

    # Profit Factor
    gross_profit = wins["pnl"].sum()
    gross_loss = abs(losses["pnl"].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    # Equity Curve (approximate based on trade sequence)
    # Note: real equity curve needs daily data, but this is trade-based metrics
    equity = initial_capital + trades["pnl"].cumsum()
    max_dd = calculate_max_drawdown(equity)

    # Sharpe/Sortino (Trade based - not time based, so approximate)
    # Ideally should use daily returns for Sharpe.
    # We will compute daily returns from the equity curve if possible, or just use trade returns.
    # Using trade returns for now, annualized by assuming N trades per year?
    # Better: Use "Expectancy" or "Avg Return / Std Dev".

    returns = trades["return_pct"]
    mean_ret = returns.mean()
    std_ret = returns.std()

    sharpe = (mean_ret / std_ret) * np.sqrt(len(trades)) if std_ret > 0 else 0 # Simple trade-based Sharpe

    downside = returns[returns < 0]
    downside_std = downside.std()
    sortino = (mean_ret / downside_std) * np.sqrt(len(trades)) if downside_std > 0 else 0

    return {
        "total_return": float(total_return),
        "cagr": 0.0, # requires time duration
        "max_dd": abs(float(max_dd)),
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "win_rate": float(win_rate),
        "profit_factor": float(profit_factor),
        "trades": len(trades),
        "avg_trade": float(mean_ret)
    }

def annualized_metrics(daily_returns: pd.Series) -> Dict[str, float]:
    """
    Calculate annualized metrics from daily returns series.
    """
    if daily_returns.empty:
        return {}

    days = len(daily_returns)
    total_ret = (1 + daily_returns).prod() - 1
    cagr = (1 + total_ret) ** (252 / days) - 1

    mean = daily_returns.mean()
    std = daily_returns.std()

    sharpe = (mean / std) * np.sqrt(252) if std > 0 else 0

    downside = daily_returns[daily_returns < 0]
    std_down = downside.std()
    sortino = (mean / std_down) * np.sqrt(252) if std_down > 0 else 0

    return {
        "cagr": float(cagr),
        "sharpe": float(sharpe),
        "sortino": float(sortino)
    }
