import pandas as pd
import numpy as np

class MetricsCalculator:
    @staticmethod
    def calculate(equity_curve: pd.Series, trades: pd.DataFrame) -> dict:
        """
        Calculates performance metrics.
        """
        if equity_curve.empty or len(equity_curve) < 2:
            return {}

        returns = equity_curve.pct_change().dropna()

        # CAGR
        days = (equity_curve.index[-1] - equity_curve.index[0]).days
        years = days / 365.25
        total_ret = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
        cagr = (1 + total_ret) ** (1 / years) - 1 if years > 0 else 0

        # Volatility (Annualized)
        vol = returns.std() * np.sqrt(252)

        # Sharpe
        sharpe = (cagr / vol) if vol > 0 else 0

        # Max Drawdown
        peak = equity_curve.cummax()
        dd = (equity_curve - peak) / peak
        max_dd = dd.min()

        # Calmar
        calmar = (cagr / abs(max_dd)) if max_dd != 0 else 0

        # Trade Stats
        num_trades = len(trades)
        win_rate = 0.0
        profit_factor = 0.0
        avg_trade = 0.0

        if num_trades > 0:
            wins = trades[trades['pnl'] > 0]
            losses = trades[trades['pnl'] <= 0]
            win_rate = len(wins) / num_trades

            gross_profit = wins['pnl'].sum()
            gross_loss = abs(losses['pnl'].sum())
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

            avg_trade = trades['pnl'].mean()

        return {
            "cagr": cagr,
            "volatility": vol,
            "sharpe": sharpe,
            "max_dd": max_dd,
            "calmar": calmar,
            "trades": num_trades,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "avg_trade_pnl": avg_trade,
            "total_return": total_ret
        }

