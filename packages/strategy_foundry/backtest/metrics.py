import pandas as pd
import numpy as np
from typing import List, Dict, Any

def calculate_metrics(trades: List[Dict[str, Any]], initial_capital: float) -> Dict[str, Any]:
    """
    Calculate performance metrics from a list of trades.

    Args:
        trades: List of dicts with keys: entry_time, exit_time, entry_price, exit_price, pnl, return_pct
        initial_capital: Starting capital

    Returns:
        Dict of metrics
    """
    if not trades:
        return {
            "total_trades": 0,
            "net_profit": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "cagr": 0.0
        }

    df_trades = pd.DataFrame(trades)

    # Basic
    total_trades = len(df_trades)
    wins = len(df_trades[df_trades["pnl"] > 0])
    win_rate = wins / total_trades if total_trades > 0 else 0

    gross_profit = df_trades[df_trades["pnl"] > 0]["pnl"].sum()
    gross_loss = abs(df_trades[df_trades["pnl"] < 0]["pnl"].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    net_profit = df_trades["pnl"].sum()
    final_equity = initial_capital + net_profit

    # Returns for Sharpe (using trade returns, strictly simpler than daily equity for now, or we reconstruct equity)
    # Reconstructing equity curve is better for MaxDD and Sharpe

    # We assume sequential trades for simplicity in equity curve reconstruction from trade list,
    # but strictly we should map to time.
    # For robust Sharpe, we need daily returns.
    # We will approximate by creating a series of PnL at exit_time.

    df_trades["exit_time"] = pd.to_datetime(df_trades["exit_time"])
    df_trades = df_trades.sort_values("exit_time")

    # Create equity curve
    # Use grouped sum to handle multiple trades at same timestamp
    daily_pnl = df_trades.groupby("exit_time")["pnl"].sum()
    equity = daily_pnl.cumsum() + initial_capital

    # Resample to daily for standard metrics
    # This assumes we have at least one trade.
    # To do this correctly, we need the full date range.
    # We will use the trade list range.
    if not df_trades.empty:
        idx = pd.date_range(df_trades["entry_time"].min(), df_trades["exit_time"].max(), freq='D')
        equity_daily = equity.resample('D').last().reindex(idx).ffill()
        # Handle NaN at start if first trade ends later
        equity_daily = equity_daily.fillna(initial_capital)

        returns = equity_daily.pct_change().dropna()

        mean_ret = returns.mean()
        std_ret = returns.std()

        if std_ret > 0:
            sharpe_ratio = (mean_ret / std_ret) * np.sqrt(252)
        else:
            sharpe_ratio = 0.0

        # Drawdown
        rolling_max = equity_daily.cummax()
        drawdown = (equity_daily - rolling_max) / rolling_max
        max_drawdown = abs(drawdown.min())

        # CAGR
        days = (df_trades["exit_time"].max() - df_trades["entry_time"].min()).days
        if days > 0:
            cagr = ((final_equity / initial_capital) ** (365 / days)) - 1
        else:
            cagr = 0.0

    else:
        sharpe_ratio = 0.0
        max_drawdown = 0.0
        cagr = 0.0

    return {
        "total_trades": int(total_trades),
        "net_profit": float(net_profit),
        "win_rate": float(win_rate),
        "profit_factor": float(profit_factor),
        "sharpe_ratio": float(sharpe_ratio),
        "max_drawdown": float(max_drawdown),
        "cagr": float(cagr),
        "avg_trade_pnl": float(df_trades["pnl"].mean()) if not df_trades.empty else 0.0
    }
