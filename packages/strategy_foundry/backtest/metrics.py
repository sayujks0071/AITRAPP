import numpy as np
import pandas as pd
from typing import List, Dict, Any

def calculate_metrics(trades: List[Dict[str, Any]], equity_curve: pd.Series) -> Dict[str, float]:
    """
    Calculate performance metrics.
    """
    if not trades or equity_curve.empty:
        return {
            "total_return": 0.0,
            "cagr": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_drawdown": 0.0,
            "calmar": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "trades": 0,
            "avg_trade_return": 0.0
        }

    # Returns
    returns = equity_curve.pct_change().dropna()
    total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1

    # Days
    days = (equity_curve.index[-1] - equity_curve.index[0]).days
    years = days / 365.25
    if years < 0.1: # Too short
        cagr = 0.0
    else:
        cagr = (1 + total_return) ** (1 / years) - 1

    # Volatility
    ann_vol = returns.std() * np.sqrt(252)

    # Sharpe (Rf=0)
    if ann_vol == 0:
        sharpe = 0.0
    else:
        sharpe = (cagr) / ann_vol # using CAGR as ann return approximation or mean returns
        # Usually Sharpe = mean(daily_ret) / std(daily_ret) * sqrt(252)
        sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0

    # Sortino
    neg_returns = returns[returns < 0]
    downside_std = neg_returns.std() * np.sqrt(252)
    sortino = returns.mean() * np.sqrt(252) / downside_std if downside_std > 0 else 0

    # Drawdown
    peak = equity_curve.cummax()
    dd = (equity_curve - peak) / peak
    max_dd = abs(dd.min())

    # Calmar
    calmar = cagr / max_dd if max_dd > 0 else 0

    # Trade Metrics
    df_trades = pd.DataFrame(trades)
    if not df_trades.empty:
        win_rate = len(df_trades[df_trades["pnl"] > 0]) / len(df_trades)

        gross_profit = df_trades[df_trades["pnl"] > 0]["pnl"].sum()
        gross_loss = abs(df_trades[df_trades["pnl"] < 0]["pnl"].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        avg_trade_return = df_trades["return_pct"].mean()
    else:
        win_rate = 0.0
        profit_factor = 0.0
        avg_trade_return = 0.0

    return {
        "total_return": total_return,
        "cagr": cagr,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": max_dd,
        "calmar": calmar,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "trades": len(trades),
        "avg_trade_return": avg_trade_return,
        "ann_vol": ann_vol
    }
