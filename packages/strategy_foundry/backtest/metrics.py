import numpy as np
import pandas as pd
from typing import Dict, Any

def calculate_cagr(start_value, end_value, years):
    if start_value <= 0 or years <= 0:
        return 0.0
    return (end_value / start_value) ** (1 / years) - 1

def calculate_metrics(trades_df: pd.DataFrame, daily_returns: pd.Series, initial_capital: float = 100000.0) -> Dict[str, Any]:
    """
    Calculate performance metrics from trades and daily returns.
    """
    metrics = {}

    # 1. Trade Metrics
    total_trades = len(trades_df)
    metrics["total_trades"] = total_trades

    if total_trades > 0:
        winners = trades_df[trades_df["pnl"] > 0]
        losers = trades_df[trades_df["pnl"] <= 0]

        metrics["win_rate"] = len(winners) / total_trades
        metrics["avg_trade"] = trades_df["pnl"].mean()
        metrics["avg_return"] = trades_df["return_pct"].mean()

        gross_profit = winners["pnl"].sum()
        gross_loss = abs(losers["pnl"].sum())

        metrics["profit_factor"] = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    else:
        metrics["win_rate"] = 0.0
        metrics["avg_trade"] = 0.0
        metrics["avg_return"] = 0.0
        metrics["profit_factor"] = 0.0

    # 2. Return/Risk Metrics (from Daily Returns)
    if not daily_returns.empty:
        total_days = len(daily_returns)
        # Annualization factor for daily data (crypto 365, stocks 252)
        # We assume 252 for NIFTY/SENSEX
        ann_factor = 252

        cumulative_return = (1 + daily_returns).prod() - 1
        metrics["total_return"] = cumulative_return

        # CAGR
        years = total_days / ann_factor
        metrics["cagr"] = calculate_cagr(initial_capital, initial_capital * (1 + cumulative_return), years)

        # Volatility
        vol = daily_returns.std() * np.sqrt(ann_factor)
        metrics["annual_volatility"] = vol

        # Sharpe (Rf=0)
        if vol > 0:
            metrics["sharpe"] = (metrics["cagr"] / vol) # Using CAGR for Sharpe numerator is common in some contexts, or mean return * 252.
            # Standard Sharpe: mean(daily_ret) * 252 / (std(daily_ret) * sqrt(252)) = mean/std * sqrt(252)
            metrics["sharpe"] = (daily_returns.mean() / daily_returns.std()) * np.sqrt(ann_factor)
        else:
            metrics["sharpe"] = 0.0

        # Sortino
        downside_returns = daily_returns[daily_returns < 0]
        downside_vol = downside_returns.std() * np.sqrt(ann_factor)
        if downside_vol > 0:
            metrics["sortino"] = (daily_returns.mean() * ann_factor) / downside_vol
        else:
            metrics["sortino"] = 0.0 # Infinite if no downside
            if metrics["sharpe"] > 0: metrics["sortino"] = 100.0 # Cap

        # Max Drawdown
        cum_returns = (1 + daily_returns).cumprod()
        peak = cum_returns.cummax()
        drawdown = (cum_returns - peak) / peak
        metrics["max_dd"] = abs(drawdown.min())

        # Calmar
        if metrics["max_dd"] > 0:
            metrics["calmar"] = metrics["cagr"] / metrics["max_dd"]
        else:
            metrics["calmar"] = 0.0 # Or infinite

        # Stability (R2 of equity curve)
        # Simplified: variance of rolling sharpe or just use total return linearity
        # Let's use standard deviation of rolling 252d returns?
        # Plan asked for "rolling 252D Sharpe dispersion".
        if len(daily_returns) > 300:
             rolling_sharpe = daily_returns.rolling(252).apply(lambda x: x.mean()/x.std()*np.sqrt(252) if x.std()>0 else 0)
             metrics["stability"] = 1.0 / (rolling_sharpe.std() + 0.01) # Higher is better
        else:
             metrics["stability"] = 1.0

    else:
        metrics["total_return"] = 0.0
        metrics["cagr"] = 0.0
        metrics["sharpe"] = 0.0
        metrics["max_dd"] = 0.0
        metrics["calmar"] = 0.0
        metrics["stability"] = 0.0

    return metrics
