import numpy as np
import pandas as pd
from typing import Dict, List

def compute_metrics(trades: List[Dict]) -> Dict:
    if not trades:
        return {
            "sharpe": 0.0,
            "max_dd": 0.0,
            "net_return": 0.0,
            "trades": 0
        }

    pnls = [t['pnl'] for t in trades]
    df_trades = pd.DataFrame(trades)

    # Simple Equity Curve
    equity = np.cumsum(pnls)
    if len(equity) == 0:
        peak = 0
        max_dd = 0
    else:
        peak = np.maximum.accumulate(equity)
        dd = (peak - equity) # Since equity is log returns approximation
        max_dd = np.max(dd) if len(dd) > 0 else 0

    avg_return = np.mean(pnls)
    std_return = np.std(pnls)

    sharpe = 0.0
    if std_return > 0:
        sharpe = (avg_return / std_return) * np.sqrt(252 * 4) # Approx assuming 4 trades a day or similar.
        # Actually sharpe should be based on daily returns or per-trade.
        # Let's standardize on per-trade sharpe * sqrt(trades_per_year)
        # Assuming ~1000 bars per year for 1d, but for 15m ~6000 bars.
        # This is a rough approximation.
        sharpe = (avg_return / std_return) * np.sqrt(len(trades)) # Just per trade sharpe scaled

    return {
        "sharpe": float(sharpe),
        "max_dd": float(max_dd),
        "net_return": float(sum(pnls)),
        "trades": len(trades),
        "win_rate": len([p for p in pnls if p > 0]) / len(pnls)
    }
