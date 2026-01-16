import numpy as np
import pandas as pd
from typing import Dict, List, Any

def calculate_metrics(trades_df: pd.DataFrame, initial_capital: float = 100000.0) -> Dict[str, Any]:
    if trades_df.empty:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "net_return": 0.0,
            "cagr": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_drawdown": 0.0,
            "calmar": 0.0,
            "avg_trade_return": 0.0,
            "avg_bars_held": 0.0
        }

    # Net Return
    # trades_df['net_return'] is % return per trade.
    # Cumulative return: prod(1 + r) - 1
    equity_curve = (1 + trades_df['net_return']).cumprod()
    total_return = equity_curve.iloc[-1] - 1

    # Win Rate
    wins = trades_df[trades_df['net_return'] > 0]
    losses = trades_df[trades_df['net_return'] <= 0]
    win_rate = len(wins) / len(trades_df)

    # Profit Factor
    gross_win = wins['net_return'].sum()
    gross_loss = abs(losses['net_return'].sum())
    profit_factor = gross_win / gross_loss if gross_loss > 0 else 999.0

    # Sharpe / Sortino
    # We need time series of returns? Or just trade returns?
    # Trade-based Sharpe is less accurate than Time-based.
    # But usually sufficient for relative ranking.
    # Let's use Trade-based for now.
    returns = trades_df['net_return']
    avg_ret = returns.mean()
    std_ret = returns.std()

    # Annualize? N trades per year?
    # We don't know duration exactly here.
    # Let's assume standard Sharpe based on sqrt(Trades) if we treat each trade as a period?
    # No, that's wrong.
    # Proper way: Resample Equity Curve to daily/hourly.
    # But we don't have equity curve over time here easily without replaying.
    # Proxy: Sharpe = mean / std (per trade) * sqrt(Trades per Year)
    # This is rough.

    # Let's stick to simple mean/std for ranking stability.
    if std_ret == 0:
        sharpe = 0.0
    else:
        sharpe = avg_ret / std_ret
        # Note: This is "Per Trade Sharpe". Not annualized.

    # Sortino
    downside = returns[returns < 0]
    if len(downside) == 0:
        sortino = 999.0
    else:
        downside_std = downside.std()
        if downside_std == 0:
            sortino = 999.0
        else:
            sortino = avg_ret / downside_std

    # Max Drawdown
    # From trade equity curve
    running_max = equity_curve.cummax()
    drawdown = (equity_curve - running_max) / running_max
    max_dd = abs(drawdown.min())

    # Calmar
    calmar = total_return / max_dd if max_dd > 0 else 999.0

    return {
        "total_trades": len(trades_df),
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "net_return": total_return,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": max_dd,
        "calmar": calmar,
        "avg_trade_return": avg_ret,
        "avg_bars_held": trades_df['bars_held'].mean()
    }
