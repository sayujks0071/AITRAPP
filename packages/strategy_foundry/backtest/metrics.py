"""Backtest Metrics"""
import pandas as pd
import numpy as np

def calculate_metrics(equity_curve: pd.Series, trades: pd.DataFrame) -> dict:
    if len(equity_curve) < 2:
        return {}

    returns = equity_curve.pct_change().dropna()

    total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
    days = (equity_curve.index[-1] - equity_curve.index[0]).days
    cagr = ((1 + total_return) ** (365 / days)) - 1 if days > 0 else 0

    vol = returns.std() * np.sqrt(252)
    sharpe = (cagr / vol) if vol > 0 else 0

    # Drawdown
    peak = equity_curve.cummax()
    dd = (equity_curve - peak) / peak
    max_dd = dd.min()
    calmar = abs(cagr / max_dd) if max_dd != 0 else 0

    # Sortino
    downside = returns[returns < 0]
    downside_vol = downside.std() * np.sqrt(252)
    sortino = (cagr / downside_vol) if downside_vol > 0 else 0

    # Trade stats
    wins = trades[trades['pnl'] > 0]
    losses = trades[trades['pnl'] <= 0]

    win_rate = len(wins) / len(trades) if len(trades) > 0 else 0
    profit_factor = abs(wins['pnl'].sum() / losses['pnl'].sum()) if len(losses) > 0 else float('inf')

    return {
        "cagr": float(cagr),
        "total_return": float(total_return),
        "volatility": float(vol),
        "sharpe": float(sharpe),
        "max_drawdown": float(max_dd),
        "calmar": float(calmar),
        "sortino": float(sortino),
        "trades": len(trades),
        "win_rate": float(win_rate),
        "profit_factor": float(profit_factor)
    }
