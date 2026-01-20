"""Backtest metrics calculation"""
import pandas as pd
import numpy as np
from typing import Dict

def calculate_metrics(equity_curve: pd.Series, trades: pd.DataFrame, initial_capital: float = 100000.0) -> Dict:
    """
    Calculate comprehensive metrics.
    """
    if equity_curve.empty:
        return {}

    # Returns
    returns = equity_curve.pct_change().dropna()

    # CAGR
    days = (equity_curve.index[-1] - equity_curve.index[0]).days
    if days < 1:
        days = 1
    total_ret = (equity_curve.iloc[-1] / initial_capital) - 1
    cagr = ((1 + total_ret) ** (365 / days)) - 1

    # Volatility (Annualized) - assuming 252 days * 75 bars (5m) or 25 bars (15m)?
    # To be safe, calculate daily returns from equity curve resampling
    daily_equity = equity_curve.resample('D').last().dropna()
    daily_returns = daily_equity.pct_change().dropna()

    ann_vol = daily_returns.std() * np.sqrt(252)
    ann_sharpe = 0.0
    if ann_vol > 0:
        ann_sharpe = (cagr - 0.05) / ann_vol # Risk free 5%

    # Sortino
    downside_returns = daily_returns[daily_returns < 0]
    downside_vol = downside_returns.std() * np.sqrt(252)
    ann_sortino = 0.0
    if downside_vol > 0:
        ann_sortino = (cagr - 0.05) / downside_vol

    # Drawdown
    peak = equity_curve.cummax()
    dd = (equity_curve - peak) / peak
    max_dd = dd.min()

    calmar = 0.0
    if max_dd < 0:
        calmar = cagr / abs(max_dd)

    # Trade Stats
    total_trades = len(trades)
    win_rate = 0.0
    profit_factor = 0.0
    avg_trade = 0.0

    if total_trades > 0:
        wins = trades[trades['pnl_pct'] > 0]
        losses = trades[trades['pnl_pct'] <= 0]
        win_rate = len(wins) / total_trades

        gross_profit = (wins['pnl_pct'] * initial_capital).sum() # approx
        gross_loss = abs((losses['pnl_pct'] * initial_capital).sum())

        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        else:
            profit_factor = float('inf') if gross_profit > 0 else 0

        avg_trade = trades['pnl_pct'].mean()

    # Late Day Dependence
    # Check if profits come from exits after 15:00
    late_day_pnl = 0.0
    total_pnl = 0.0
    if total_trades > 0:
        # Assuming trades df has exit_time
        # Convert exit_time to time object if not already
        # It is datetime usually from engine
        exit_times = pd.to_datetime(trades['exit_time']).dt.time
        late_mask = exit_times >= pd.to_datetime("15:00").time()

        late_day_pnl = trades[late_mask]['pnl_pct'].sum()
        total_pnl = trades['pnl_pct'].sum()

    late_day_ratio = 0.0
    if total_pnl > 0:
        late_day_ratio = late_day_pnl / total_pnl

    return {
        "cagr": cagr,
        "sharpe": ann_sharpe,
        "sortino": ann_sortino,
        "max_dd": max_dd,
        "calmar": calmar,
        "volatility": ann_vol,
        "total_trades": total_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_trade_pct": avg_trade,
        "late_day_ratio": late_day_ratio
    }
