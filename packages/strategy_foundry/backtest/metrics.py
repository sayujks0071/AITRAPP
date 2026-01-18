import pandas as pd
import numpy as np

def calculate_metrics(trades_df: pd.DataFrame, daily_returns: pd.Series, initial_capital: float = 100000.0):
    """
    Calculates performance metrics from trades and daily returns.
    """
    if trades_df.empty:
        return {
            "cagr": 0.0,
            "sharpe": -99.9,
            "sortino": -99.9,
            "calmar": -99.9,
            "max_dd": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "trades": 0,
            "avg_trade_pct": 0.0
        }

    # Trade-based metrics
    wins = trades_df[trades_df["pnl"] > 0]
    losses = trades_df[trades_df["pnl"] <= 0]

    win_rate = len(wins) / len(trades_df) if len(trades_df) > 0 else 0
    gross_profit = wins["pnl"].sum()
    gross_loss = abs(losses["pnl"].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    avg_trade_pct = trades_df["return_pct"].mean()

    # Time-series metrics
    # Resample to daily if intraday
    # daily_returns should be % returns series

    # CAGR
    # Assuming daily_returns index is datetime
    if len(daily_returns) > 1:
        total_ret = (1 + daily_returns).prod() - 1
        days = (daily_returns.index[-1] - daily_returns.index[0]).days
        if days > 0:
            cagr = (1 + total_ret) ** (365 / days) - 1
        else:
            cagr = 0.0
    else:
        cagr = 0.0

    # Sharpe
    mean_ret = daily_returns.mean()
    std_ret = daily_returns.std()
    sharpe = (mean_ret / std_ret * np.sqrt(252)) if std_ret > 0 else 0.0

    # Sortino
    downside_ret = daily_returns[daily_returns < 0]
    std_down = downside_ret.std()
    sortino = (mean_ret / std_down * np.sqrt(252)) if std_down > 0 else 0.0

    # Max Drawdown
    cum_ret = (1 + daily_returns).cumprod()
    peak = cum_ret.cummax()
    drawdown = (cum_ret - peak) / peak
    max_dd = abs(drawdown.min())

    # Calmar
    calmar = cagr / max_dd if max_dd > 0 else 0.0

    return {
        "cagr": cagr,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "max_dd": max_dd,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "trades": len(trades_df),
        "avg_trade_pct": avg_trade_pct
    }
