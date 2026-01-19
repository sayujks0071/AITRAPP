"""
Performance metrics calculation.
"""
import pandas as pd
import numpy as np

def calculate_metrics(equity_curve: pd.Series, trades: pd.DataFrame) -> dict:
    """
    Calculate full suite of metrics from equity curve and trades.
    equity_curve: Series of daily equity values.
    trades: DataFrame of trades.
    """
    if equity_curve.empty:
        return {}

    # Returns
    initial_equity = equity_curve.iloc[0]
    final_equity = equity_curve.iloc[-1]
    total_return = (final_equity - initial_equity) / initial_equity

    # CAGR
    n_days = (equity_curve.index[-1] - equity_curve.index[0]).days
    if n_days > 0 and initial_equity > 0 and final_equity > 0:
        cagr = (final_equity / initial_equity) ** (365 / n_days) - 1
    else:
        cagr = 0.0

    # Volatility (Annualized)
    daily_returns = equity_curve.pct_change().dropna()
    ann_vol = daily_returns.std() * np.sqrt(252)

    # Sharpe (Rf=0)
    if ann_vol > 0:
        sharpe = (cagr) / ann_vol # Simplified Sharpe using CAGR as return proxy or mean daily return?
        # Standard: mean(daily_ret) / std(daily_ret) * sqrt(252)
        sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
    else:
        sharpe = 0.0

    # Sortino
    downside_returns = daily_returns[daily_returns < 0]
    downside_std = downside_returns.std() * np.sqrt(252)
    if downside_std > 0:
        sortino = (daily_returns.mean() * 252) / downside_std
    else:
        sortino = 0.0

    # Drawdown
    running_max = equity_curve.cummax()
    drawdown = (equity_curve - running_max) / running_max
    max_dd = drawdown.min() # Negative value

    # Calmar
    if max_dd < 0:
        calmar = cagr / abs(max_dd)
    else:
        calmar = 0.0

    # Stability (R2 of equity log curve)
    # Or Rolling Sharpe dispersion as requested in prompt: "rolling 252D Sharpe dispersion"
    # But for single metric summary, R2 is good for stability.
    # Prompt asks for "Stability (low dispersion)" -> rolling Sharpe dispersion.

    rolling_sharpe = daily_returns.rolling(252).apply(lambda x: x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0)
    stability_score = 1.0 / (rolling_sharpe.std() + 0.01) # Inverse of dispersion?
    # Or just return the std dev of rolling sharpe.
    sharpe_volatility = rolling_sharpe.std()

    # Trade Stats
    num_trades = len(trades)
    win_rate = len(trades[trades['pnl'] > 0]) / num_trades if num_trades > 0 else 0.0
    profit_factor = abs(trades[trades['pnl'] > 0]['pnl'].sum() / trades[trades['pnl'] < 0]['pnl'].sum()) if num_trades > 0 and trades[trades['pnl'] < 0]['pnl'].sum() != 0 else 0.0
    avg_trade_ret = trades['return_pct'].mean() if num_trades > 0 else 0.0

    return {
        "total_return": total_return,
        "cagr": cagr,
        "annualized_vol": ann_vol,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": max_dd,
        "calmar": calmar,
        "sharpe_stability": sharpe_volatility,
        "trades": num_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_trade_return": avg_trade_ret
    }
