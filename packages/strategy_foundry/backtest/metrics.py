import numpy as np
import pandas as pd
from typing import Dict, Any, List

def calculate_metrics(
    equity_curve: pd.Series,
    trades: List[Dict],
    initial_capital: float = 100000.0,
    risk_free_rate: float = 0.0
) -> Dict[str, Any]:
    """
    Calculate performance metrics from equity curve and trade list.

    Args:
        equity_curve: Series of equity values indexed by datetime
        trades: List of trade dictionaries
        initial_capital: Starting capital
        risk_free_rate: Annual risk free rate (decimal)

    Returns:
        Dictionary of metrics
    """
    if equity_curve.empty:
        return {}

    # 1. Returns based metrics
    # Resample to daily for standard annualization if intraday
    daily_equity = equity_curve.resample('D').last().dropna()
    if daily_equity.empty:
         # Fallback for very short tests
         daily_equity = equity_curve

    returns = daily_equity.pct_change().dropna()

    total_return = (equity_curve.iloc[-1] / initial_capital) - 1.0

    days = (equity_curve.index[-1] - equity_curve.index[0]).days
    years = max(days / 365.0, 0.001) # Avoid div by zero

    cagr = (equity_curve.iloc[-1] / initial_capital) ** (1/years) - 1.0

    # Volatility (Annualized)
    # Assuming daily returns
    volatility = returns.std() * np.sqrt(252)

    # Sharpe
    sharpe = 0.0
    if volatility > 0:
        sharpe = (cagr - risk_free_rate) / volatility

    # Sortino
    downside_returns = returns[returns < 0]
    downside_vol = downside_returns.std() * np.sqrt(252)
    sortino = 0.0
    if downside_vol > 0:
        sortino = (cagr - risk_free_rate) / downside_vol

    # Drawdown
    rolling_max = daily_equity.cummax()
    drawdown = (daily_equity - rolling_max) / rolling_max
    max_dd = drawdown.min() # Negative value

    calmar = 0.0
    if max_dd < 0:
        calmar = cagr / abs(max_dd)

    # 2. Trade metrics
    total_trades = len(trades)
    winning_trades = [t for t in trades if t['pnl'] > 0]
    losing_trades = [t for t in trades if t['pnl'] <= 0]

    win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0

    gross_profit = sum(t['pnl'] for t in winning_trades)
    gross_loss = abs(sum(t['pnl'] for t in losing_trades))

    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    if gross_loss == 0 and gross_profit == 0:
        profit_factor = 0.0

    avg_trade = sum(t['pnl'] for t in trades) / total_trades if total_trades > 0 else 0.0

    return {
        "cagr": round(cagr, 4),
        "volatility": round(volatility, 4),
        "sharpe": round(sharpe, 4),
        "sortino": round(sortino, 4),
        "max_dd": round(max_dd, 4),
        "calmar": round(calmar, 4),
        "total_trades": total_trades,
        "win_rate": round(win_rate, 4),
        "profit_factor": round(profit_factor, 4),
        "avg_trade": round(avg_trade, 2),
        "total_return": round(total_return, 4),
        "pnl_net": round(equity_curve.iloc[-1] - initial_capital, 2)
    }
