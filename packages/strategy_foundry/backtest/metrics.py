"""Backtest Metrics Calculation"""
import pandas as pd
import numpy as np
from typing import Dict, List

def calculate_metrics(equity_curve: pd.Series, trades: List[Dict]) -> Dict:
    """
    Calculate performance metrics.
    """
    if len(equity_curve) < 2:
        return {}

    start_equity = equity_curve.iloc[0]
    end_equity = equity_curve.iloc[-1]

    # CAGR
    days = (equity_curve.index[-1] - equity_curve.index[0]).days
    years = days / 365.25
    if years > 0 and start_equity > 0:
        cagr = (end_equity / start_equity) ** (1/years) - 1
    else:
        cagr = 0.0

    # Drawdown
    peak = equity_curve.cummax()
    dd = (equity_curve - peak) / peak
    max_dd = dd.min()

    # Returns
    returns = equity_curve.pct_change().dropna()

    # Sharpe (Annualized)
    # Daily returns * sqrt(252)
    mean_ret = returns.mean()
    std_ret = returns.std()

    if std_ret > 0:
        sharpe = (mean_ret / std_ret) * np.sqrt(252)
    else:
        sharpe = 0.0

    # Sortino
    neg_ret = returns[returns < 0]
    downside_std = neg_ret.std()
    if downside_std > 0:
        sortino = (mean_ret / downside_std) * np.sqrt(252)
    else:
        sortino = 0.0

    # Calmar
    if max_dd < 0:
        calmar = cagr / abs(max_dd)
    else:
        calmar = 0.0

    # Stability (R-squared of log equity)
    # Simple proxy: 1 - std(returns) ? No.
    # We will skip complex stability for now.

    return {
        "cagr": float(cagr),
        "max_dd": float(max_dd), # negative number
        "sharpe": float(sharpe),
        "calmar": float(calmar),
        "total_trades": len(trades),
        "win_rate": len([t for t in trades if t["pnl"] > 0]) / len(trades) if trades else 0.0
    }
