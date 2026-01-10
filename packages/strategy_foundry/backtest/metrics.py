"""
Metrics calculation for backtests.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any

def calculate_metrics(trades: pd.DataFrame, equity_curve: pd.Series, initial_capital: float = 100000.0) -> Dict[str, Any]:
    """
    Calculate performance metrics.

    Args:
        trades: DataFrame with columns [entry_time, exit_time, entry_price, exit_price, pnl, quantity, side]
        equity_curve: Series of equity values (daily or per bar)
        initial_capital: Starting capital

    Returns:
        Dict of metrics
    """
    if trades.empty:
        return {
            "cagr": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_dd": 0.0,
            "calmar": 0.0,
            "trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0
        }

    # CAGR
    # Assuming equity curve is daily or we resample to daily
    # If equity curve is per-bar, we should resample to daily for CAGR/Sharpe convention
    # But for intraday, we might want to use the full curve? Standard is daily returns.

    # Ensure equity curve has datetime index
    if not isinstance(equity_curve.index, pd.DatetimeIndex):
         # If index is integers, we can't do time-based CAGR easily without total days
         # Assume total days from trades
         total_days = (trades["exit_time"].max() - trades["entry_time"].min()).days
         if total_days < 1: total_days = 1
    else:
         total_days = (equity_curve.index[-1] - equity_curve.index[0]).days
         if total_days < 1: total_days = 1

    final_equity = equity_curve.iloc[-1]
    total_return = (final_equity - initial_capital) / initial_capital
    cagr = ((1 + total_return) ** (365 / total_days)) - 1 if total_days > 0 else 0

    # Returns
    # Resample to daily for standard Sharpe
    if isinstance(equity_curve.index, pd.DatetimeIndex):
        daily_equity = equity_curve.resample("D").last().dropna()
        daily_returns = daily_equity.pct_change().dropna()
    else:
        # Fallback if no time index: use trade returns sequence
        daily_returns = pd.Series(trades["pnl"] / initial_capital) # Not accurate but proxy

    if len(daily_returns) > 1:
        mean_ret = daily_returns.mean()
        std_ret = daily_returns.std()
        sharpe = (mean_ret / std_ret) * np.sqrt(252) if std_ret > 0 else 0

        downside_returns = daily_returns[daily_returns < 0]
        downside_std = downside_returns.std()
        sortino = (mean_ret / downside_std) * np.sqrt(252) if downside_std > 0 else 0
    else:
        sharpe = 0
        sortino = 0

    # Max DD
    rolling_max = equity_curve.cummax()
    drawdown = (equity_curve - rolling_max) / rolling_max
    max_dd = abs(drawdown.min())

    # Calmar
    calmar = cagr / max_dd if max_dd > 0 else 0

    # Trade stats
    wins = trades[trades["pnl"] > 0]
    losses = trades[trades["pnl"] <= 0]
    win_rate = len(wins) / len(trades)

    gross_profit = wins["pnl"].sum()
    gross_loss = abs(losses["pnl"].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    return {
        "cagr": float(cagr),
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "max_dd": float(max_dd),
        "calmar": float(calmar),
        "trades": len(trades),
        "win_rate": float(win_rate),
        "profit_factor": float(profit_factor),
        "avg_trade": float(trades["pnl"].mean())
    }
