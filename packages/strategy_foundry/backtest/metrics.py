import pandas as pd
import numpy as np
from typing import Dict, Any, List
from .engine import Trade

def calculate_metrics(equity_curve: pd.Series, trades: List[Trade]) -> Dict[str, float]:
    if equity_curve.empty or len(trades) == 0:
        return {
            "cagr": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_dd": 0.0,
            "calmar": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "trades": 0
        }

    # Returns
    returns = equity_curve.pct_change().dropna()

    # CAGR
    days = (equity_curve.index[-1] - equity_curve.index[0]).days
    if days > 0:
        cagr = (equity_curve.iloc[-1] / equity_curve.iloc[0]) ** (365/days) - 1
    else:
        cagr = 0.0

    # Volatility
    ann_vol = returns.std() * np.sqrt(252)

    # Sharpe
    sharpe = (cagr / ann_vol) if ann_vol > 0 else 0.0

    # Sortino
    downside_returns = returns[returns < 0]
    downside_vol = downside_returns.std() * np.sqrt(252)
    sortino = (cagr / downside_vol) if downside_vol > 0 else 0.0

    # Max Drawdown
    rolling_max = equity_curve.cummax()
    drawdown = (equity_curve - rolling_max) / rolling_max
    max_dd = abs(drawdown.min())

    # Calmar
    calmar = (cagr / max_dd) if max_dd > 0 else 0.0

    # Trade Stats
    pnls = [t.pnl for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    win_rate = len(wins) / len(trades)

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0

    return {
        "cagr": float(cagr),
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "max_dd": float(max_dd),
        "calmar": float(calmar),
        "win_rate": float(win_rate),
        "profit_factor": float(profit_factor),
        "trades": len(trades)
    }
