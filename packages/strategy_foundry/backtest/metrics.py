import numpy as np
import pandas as pd

def calculate_metrics(equity_curve: pd.Series, trades: pd.DataFrame) -> dict:
    """
    Calculate performance metrics from equity curve and trades.
    equity_curve: Series of account equity (daily)
    trades: DataFrame of closed trades
    """
    if equity_curve.empty:
        return {}

    initial_capital = equity_curve.iloc[0]
    final_capital = equity_curve.iloc[-1]

    # Returns
    returns = equity_curve.pct_change().dropna()
    total_return = (final_capital - initial_capital) / initial_capital

    days = (equity_curve.index[-1] - equity_curve.index[0]).days
    years = days / 365.25
    if years > 0:
        cagr = (final_capital / initial_capital) ** (1 / years) - 1
    else:
        cagr = 0.0

    # Risk
    volatility = returns.std() * np.sqrt(252)

    sharpe = 0.0
    if volatility > 0:
        sharpe = (returns.mean() * 252) / (returns.std() * np.sqrt(252))

    # Drawdown
    running_max = equity_curve.cummax()
    drawdown = (equity_curve - running_max) / running_max
    max_drawdown = drawdown.min()

    calmar = 0.0
    if max_drawdown < 0:
        calmar = cagr / abs(max_drawdown)

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

        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        else:
            profit_factor = float('inf') if gross_profit > 0 else 0.0

        avg_trade = trades['pnl_pct'].mean()

    return {
        "cagr": cagr,
        "total_return": total_return,
        "volatility": volatility,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown, # Negative number
        "calmar": calmar,
        "trades": num_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_trade": avg_trade
    }
