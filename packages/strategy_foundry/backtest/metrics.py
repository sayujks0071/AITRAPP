"""
Backtest Metrics
Calculates performance metrics for backtest results.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any

class BacktestMetrics:
    @staticmethod
    def calculate(trades: pd.DataFrame, equity_curve: pd.Series, risk_free_rate: float = 0.05) -> Dict[str, Any]:
        if trades.empty:
            return {
                "total_trades": 0,
                "net_profit": 0.0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "sharpe": 0.0,
                "sortino": 0.0,
                "max_drawdown": 0.0,
                "calmar": 0.0,
                "cagr": 0.0,
                "avg_trade": 0.0
            }

        # Basic Trade Metrics
        total_trades = len(trades)
        winning_trades = trades[trades['pnl'] > 0]
        losing_trades = trades[trades['pnl'] <= 0]

        gross_profit = winning_trades['pnl'].sum()
        gross_loss = abs(losing_trades['pnl'].sum())
        net_profit = trades['pnl'].sum()

        win_rate = len(winning_trades) / total_trades
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        avg_trade = trades['pnl'].mean()

        # Time Series Metrics (Equity Curve)
        # Assume equity_curve is indexed by time
        if equity_curve.empty:
             return {
                "total_trades": total_trades,
                "net_profit": net_profit,
                "win_rate": win_rate,
                "profit_factor": profit_factor
            }

        returns = equity_curve.pct_change().dropna()

        # Sharpe
        if returns.std() > 0:
            sharpe = np.sqrt(252 * 75) * (returns.mean() / returns.std()) # approx 75 5m bars/day
            # Adjust scaling later based on exact timeframe, but for comparison this is ok-ish
            # Better: use actual time delta
            bars_per_year = 252 * 75 # rough guess for 5m
            # Let's standardize on daily returns for Sharpe/Sortino/CAGR
            daily_equity = equity_curve.resample('D').last().dropna()
            daily_returns = daily_equity.pct_change().dropna()

            if len(daily_returns) > 1:
                sharpe = np.sqrt(252) * (daily_returns.mean() / daily_returns.std()) if daily_returns.std() > 0 else 0

                # Sortino
                downside_returns = daily_returns[daily_returns < 0]
                downside_std = downside_returns.std()
                sortino = np.sqrt(252) * (daily_returns.mean() / downside_std) if downside_std > 0 else 0

                # CAGR
                days = (daily_equity.index[-1] - daily_equity.index[0]).days
                if days > 0:
                    total_return = (daily_equity.iloc[-1] / daily_equity.iloc[0]) - 1
                    cagr = (1 + total_return) ** (365 / days) - 1
                else:
                    cagr = 0
            else:
                sharpe = 0
                sortino = 0
                cagr = 0
        else:
            sharpe = 0
            sortino = 0
            cagr = 0

        # Drawdown
        rolling_max = equity_curve.cummax()
        drawdown = (equity_curve - rolling_max) / rolling_max
        max_drawdown = abs(drawdown.min())

        # Calmar
        calmar = cagr / max_drawdown if max_drawdown > 0 else 0

        return {
            "total_trades": int(total_trades),
            "net_profit": float(net_profit),
            "win_rate": float(win_rate),
            "profit_factor": float(profit_factor),
            "sharpe": float(sharpe),
            "sortino": float(sortino),
            "max_drawdown": float(max_drawdown),
            "calmar": float(calmar),
            "cagr": float(cagr),
            "avg_trade": float(avg_trade)
        }
