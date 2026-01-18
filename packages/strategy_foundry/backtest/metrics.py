import pandas as pd
import numpy as np
from typing import Dict

def compute_metrics(trades: pd.DataFrame, equity: pd.Series) -> Dict[str, float]:
    if trades.empty:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "cagr": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_dd": 0.0,
            "calmar": 0.0,
            "avg_trade_pct": 0.0,
            "avg_bars": 0.0
        }

    # Trade Metrics
    n = len(trades)
    winners = trades[trades["pnl"] > 0]
    win_rate = len(winners) / n
    avg_trade = trades["pnl"].mean()
    avg_bars = trades["bars"].mean()

    # Time Metrics (Equity)
    # Total Return
    total_ret = equity.iloc[-1] - 1.0

    # CAGR (approx)
    days = (equity.index[-1] - equity.index[0]).days
    years = max(days / 365.25, 0.1)
    cagr = (equity.iloc[-1])**(1/years) - 1.0

    # Volatility & Sharpe
    daily_rets = equity.pct_change().dropna()
    ann_vol = daily_rets.std() * np.sqrt(252)
    sharpe = (cagr / ann_vol) if ann_vol > 0 else 0.0

    # Sortino (downside vol)
    neg_rets = daily_rets[daily_rets < 0]
    down_vol = neg_rets.std() * np.sqrt(252)
    sortino = (cagr / down_vol) if down_vol > 0 else 0.0

    # Max Drawdown
    rolling_max = equity.cummax()
    drawdown = (equity - rolling_max) / rolling_max
    max_dd = abs(drawdown.min())

    calmar = (cagr / max_dd) if max_dd > 0 else 0.0

    return {
        "total_trades": n,
        "win_rate": round(win_rate, 4),
        "cagr": round(cagr, 4),
        "sharpe": round(sharpe, 4),
        "sortino": round(sortino, 4),
        "max_dd": round(max_dd, 4),
        "calmar": round(calmar, 4),
        "avg_trade_pct": round(avg_trade, 6),
        "avg_bars": round(avg_bars, 1)
    }

def calculate_stability(equity: pd.Series, window: int = 252) -> float:
    """
    Rolling Sharpe dispersion. Lower is better.
    """
    if len(equity) < window * 2:
        return 0.0

    rets = equity.pct_change().dropna()
    rolling_sharpe = rets.rolling(window).mean() / rets.rolling(window).std() * np.sqrt(252)
    return rolling_sharpe.std()
