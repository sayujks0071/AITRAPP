import pandas as pd
import numpy as np
from typing import Dict

def calculate_metrics(trades_df: pd.DataFrame, initial_capital: float = 100000.0) -> Dict[str, float]:
    if trades_df.empty:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "sharpe": -99.0,
            "calmar": -99.0,
            "max_dd_pct": 0.0,
            "net_return_pct": 0.0,
            "cagr": 0.0,
            "stability": 0.0
        }

    # Trades returns are percentage returns
    returns = trades_df["return"].values

    n_trades = len(trades_df)
    n_wins = np.sum(returns > 0)
    win_rate = n_wins / n_trades if n_trades > 0 else 0

    gross_profit = np.sum(returns[returns > 0])
    gross_loss = np.abs(np.sum(returns[returns < 0]))

    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 99.0

    # Equity Curve (Simple compounding or fixed fractional?)
    # foundry.yaml says "fixed fraction" or "1x notional".
    # Assuming full capital reinvestment for compounding stats (CAGR),
    # or simple sum for fixed sizing.
    # Let's use simple cumulative sum of returns for Sharpe to be robust against sizing.
    # Or equity curve:
    equity = np.cumprod(1 + returns)

    # Max DD
    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak
    max_dd = np.min(drawdown) # Negative value

    # Sharpe (Annualized)
    # How many trades per year?
    # We need time duration.
    start_time = trades_df["entry_time"].min()
    end_time = trades_df["exit_time"].max()
    duration_days = (end_time - start_time).days
    if duration_days < 1: duration_days = 1

    years = duration_days / 365.25

    # Simple average return per trade * trades per year?
    # Or resample equity curve to daily?
    # Resampling is better for Sharpe.
    # But we only have trade endpoints.
    # Let's map trades to a daily series.

    # Construct Daily Returns Series
    # We need a daily index from start to end.
    daily_idx = pd.date_range(start=start_time.date(), end=end_time.date(), freq='D')
    daily_pnl = pd.Series(0.0, index=daily_idx)

    for _, row in trades_df.iterrows():
        # Attribute pnl to exit day
        d = row["exit_time"].date()
        if d in daily_pnl.index:
            daily_pnl[d] += row["return"]

    # Calculate Daily Stats
    daily_ret = daily_pnl
    mean_daily = daily_ret.mean()
    std_daily = daily_ret.std()

    sharpe = 0.0
    if std_daily > 0:
        sharpe = (mean_daily / std_daily) * np.sqrt(252)

    cagr = (equity[-1] ** (1/years)) - 1 if years > 0 and equity[-1] > 0 else 0

    calmar = cagr / abs(max_dd) if max_dd != 0 else 0

    return {
        "total_trades": int(n_trades),
        "win_rate": float(win_rate),
        "profit_factor": float(profit_factor),
        "sharpe": float(sharpe),
        "calmar": float(calmar),
        "max_dd_pct": float(abs(max_dd) * 100),
        "net_return_pct": float((equity[-1] - 1) * 100),
        "cagr": float(cagr),
        "stability": float(sharpe) # Placeholder
    }
