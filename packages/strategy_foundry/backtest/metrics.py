"""Backtest metrics calculation"""
import pandas as pd
import numpy as np
from typing import List, Dict
from packages.strategy_foundry.backtest.engine import Trade

def calculate_metrics(trades: List[Trade], equity_curve: pd.DataFrame, initial_capital: float = 100000.0) -> Dict[str, float]:
    if not trades or equity_curve.empty:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "net_profit": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_drawdown": 0.0,
            "calmar": 0.0,
            "profit_factor": 0.0,
            "cagr": 0.0
        }

    # Trade Metrics
    pnls = [t.pnl_net for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    total_trades = len(trades)
    win_rate = len(wins) / total_trades if total_trades > 0 else 0

    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = gross_win / gross_loss if gross_loss > 0 else float('inf')

    net_profit = sum(pnls)

    # Time Series Metrics (Daily returns for Sharpe)
    # Resample equity to daily
    daily_equity = equity_curve.resample('D').last().dropna()
    # If gaps, ffill?
    daily_equity = daily_equity.ffill()

    # Calculate returns
    # We assume equity curve is purely PnL accumulation.
    # To get returns, we need a base capital.
    # Virtual capital = Initial + CumSum
    capital_curve = initial_capital + daily_equity["equity"]
    returns = capital_curve.pct_change().dropna()

    if len(returns) < 2:
        sharpe = 0.0
        sortino = 0.0
        max_dd = 0.0
        cagr = 0.0
    else:
        # Annualized metrics (assuming 252 days)
        mean_ret = returns.mean() * 252
        vol = returns.std() * np.sqrt(252)
        sharpe = mean_ret / vol if vol > 0 else 0.0

        downside_returns = returns[returns < 0]
        downside_vol = downside_returns.std() * np.sqrt(252)
        sortino = mean_ret / downside_vol if downside_vol > 0 else 0.0

        # Max Drawdown
        roll_max = capital_curve.cummax()
        drawdown = (capital_curve - roll_max) / roll_max
        max_dd = abs(drawdown.min())

        # CAGR
        days = (equity_curve.index[-1] - equity_curve.index[0]).days
        if days > 0:
            total_ret = (capital_curve.iloc[-1] / initial_capital) - 1
            cagr = (1 + total_ret) ** (365/days) - 1
        else:
            cagr = 0.0

    # Calmar
    calmar = cagr / max_dd if max_dd > 0 else 0.0

    return {
        "total_trades": total_trades,
        "win_rate": win_rate,
        "net_profit": net_profit,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": max_dd,
        "calmar": calmar,
        "profit_factor": profit_factor,
        "cagr": cagr
    }
