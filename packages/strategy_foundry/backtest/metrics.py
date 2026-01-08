"""
Backtest Metrics
"""
import pandas as pd
import numpy as np
from typing import Dict

class BacktestMetrics:
    @staticmethod
    def calculate(trades: pd.DataFrame, equity_curve: pd.Series) -> Dict[str, float]:
        if trades.empty:
            return {
                "sharpe": 0.0,
                "calmar": 0.0,
                "cagr": 0.0,
                "max_drawdown": 0.0,
                "total_trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "net_profit": 0.0,
                "avg_trade": 0.0
            }

        # Returns
        returns = equity_curve.pct_change().dropna()

        # Sharpe (Annualized)
        # Assuming intraday data, we need to annualize correctly.
        # If returns are per bar (e.g. 5m), we have many bars.
        # But `equity_curve` is per bar.
        # Better to resample to daily for Sharpe/CAGR standard?
        # Or multiply by sqrt(bars_per_year).
        # 5m bars: ~75 per day * 252 days = 18900
        # Let's resample equity to daily for standard metrics.

        daily_equity = equity_curve.resample('D').last().dropna()
        daily_returns = daily_equity.pct_change().dropna()

        if daily_returns.empty:
             sharpe = 0.0
             cagr = 0.0
             max_dd = 0.0
        else:
            sharpe = daily_returns.mean() / daily_returns.std() * np.sqrt(252) if daily_returns.std() != 0 else 0

            # CAGR
            total_ret = (daily_equity.iloc[-1] / daily_equity.iloc[0]) - 1
            days = (daily_equity.index[-1] - daily_equity.index[0]).days
            if days > 0:
                cagr = (1 + total_ret) ** (365/days) - 1
            else:
                cagr = 0.0

            # Max DD
            roll_max = daily_equity.cummax()
            drawdown = (daily_equity - roll_max) / roll_max
            max_dd = abs(drawdown.min())

        # Calmar
        calmar = cagr / max_dd if max_dd > 0 else 0.0

        # Trade Metrics
        wins = trades[trades['pnl'] > 0]
        losses = trades[trades['pnl'] <= 0]

        win_rate = len(wins) / len(trades)

        gross_profit = wins['pnl'].sum()
        gross_loss = abs(losses['pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        return {
            "sharpe": float(sharpe),
            "calmar": float(calmar),
            "cagr": float(cagr),
            "max_drawdown": float(max_dd),
            "total_trades": len(trades),
            "win_rate": float(win_rate),
            "profit_factor": float(profit_factor),
            "net_profit": float(trades['pnl'].sum()),
            "avg_trade": float(trades['pnl'].mean())
        }
