"""Backtest Metrics and Metrics Calculation"""
import pandas as pd
import numpy as np

def calculate_metrics(trades_df: pd.DataFrame, equity_curve: list) -> dict:
    if trades_df.empty:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_drawdown": 0.0,
            "calmar": 0.0,
            "net_profit": 0.0
        }

    # Basic
    total_trades = len(trades_df)
    wins = trades_df[trades_df["pnl_net"] > 0]
    losses = trades_df[trades_df["pnl_net"] <= 0]
    win_rate = len(wins) / total_trades

    gross_profit = wins["pnl_net"].sum()
    gross_loss = abs(losses["pnl_net"].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 99.0

    # Sharpe approximation: sqrt(TradesPerYear) * (Mean / Std)
    # We estimate trades per year based on time span of trades
    if "entry_time" in trades_df.columns:
        times = pd.to_datetime(trades_df["entry_time"])
        days = (times.max() - times.min()).days
        if days < 1: days = 1
        trades_per_year = total_trades * (365 / days)
    else:
        # Fallback if no dates
        trades_per_year = total_trades # Assume 1 year data

    avg_ret = trades_df["pnl_net"].mean()
    std_ret = trades_df["pnl_net"].std()

    if std_ret > 0:
        sharpe = (avg_ret / std_ret) * np.sqrt(trades_per_year)
    else:
        sharpe = 0.0

    # Drawdown
    eq = np.array(equity_curve)
    peaks = np.maximum.accumulate(eq)
    dds = (peaks - eq) / peaks
    max_dd = np.max(dds)

    calmar = (eq[-1]/100.0 - 1) / max_dd if max_dd > 0 else 0

    return {
        "total_trades": total_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "calmar": calmar,
        "net_profit": eq[-1] - 100.0
    }
