import pandas as pd
import numpy as np
from typing import Dict, Any, List
import structlog
from dataclasses import dataclass

logger = structlog.get_logger(__name__)

@dataclass
class Trade:
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    entry_price: float
    exit_price: float
    side: int # 1 or -1
    pnl: float
    pnl_pct: float
    exit_reason: str

class FoundryEngine:
    """
    Lightweight Daily Backtest Engine.
    Executes signals at Next Open.
    """
    def __init__(self, slip_bps=5, fee_bps=3):
        self.slip_bps = slip_bps
        self.fee_bps = fee_bps

    def run(self, df: pd.DataFrame, positions: pd.Series) -> Dict[str, Any]:
        """
        Run backtest based on target positions.
        """
        # Align positions to next day (Execution at Open)
        target_pos = positions.shift(1).fillna(0)

        trades = []
        equity_curve = [1.0]

        opens = df["open"].values
        dates = df.index
        targets = target_pos.values

        current_pos = 0 # 0 or 1
        entry_price = 0.0
        entry_date = None

        capital = 1.0

        for i in range(len(df)):
            tgt = targets[i]
            price = opens[i]

            if tgt != current_pos:
                # Close existing
                if current_pos != 0:
                    exit_price = price * (1 - self.slip_bps/10000)
                    pnl_pct = (exit_price - entry_price) / entry_price
                    pnl_pct -= (self.fee_bps/10000) * 2

                    capital *= (1 + pnl_pct)

                    trades.append(Trade(
                        entry_date=entry_date,
                        exit_date=dates[i],
                        entry_price=entry_price,
                        exit_price=exit_price,
                        side=current_pos,
                        pnl=pnl_pct * entry_price,
                        pnl_pct=pnl_pct,
                        exit_reason="Signal"
                    ))

                # Open new
                if tgt != 0:
                    current_pos = tgt
                    entry_price = price * (1 + self.slip_bps/10000)
                    entry_date = dates[i]
                else:
                    current_pos = 0

        return {
            "trades": trades,
            "equity_curve": [],
            "final_capital": capital
        }

    def calculate_metrics(self, trades: List[Trade], initial_capital=100000.0) -> Dict[str, Any]:
        if not trades:
            return {"cagr": 0, "sharpe": 0, "max_dd": 0, "trades": 0, "total_return": 0}

        df_trades = pd.DataFrame([vars(t) for t in trades])
        df_trades['cum_pnl'] = (1 + df_trades['pnl_pct']).cumprod()

        total_ret = df_trades['cum_pnl'].iloc[-1] - 1
        n_years = (df_trades['exit_date'].max() - df_trades['entry_date'].min()).days / 365.25
        cagr = (1 + total_ret) ** (1/n_years) - 1 if n_years > 0 else 0

        return {
            "cagr": cagr,
            "trades": len(trades),
            "win_rate": len(df_trades[df_trades.pnl > 0]) / len(trades),
            "total_return": total_ret,
            # Placeholder for Sharpe/MaxDD if relying on this method,
            # but run_hourly uses run_vectorized for these.
            "sharpe": 0,
            "max_dd": 0
        }

    def run_vectorized(self, df: pd.DataFrame, signals: pd.Series) -> Dict[str, Any]:
        """
        Fast vectorized backtest.
        """
        pos = signals.shift(1).fillna(0)

        opens = df["open"]
        mkt_ret = opens.pct_change()

        strat_ret = pos.shift(1) * mkt_ret

        turnover = pos.diff().abs().fillna(0)
        costs = turnover * (self.slip_bps + self.fee_bps) / 10000

        net_ret = strat_ret - costs

        equity = (1 + net_ret).cumprod()

        peak = equity.cummax()
        # Handle division by zero if peak is 0 (unlikely)
        dd = (equity - peak) / peak
        max_dd = dd.min()

        total_ret = equity.iloc[-1] - 1
        days = (df.index[-1] - df.index[0]).days
        years = days / 365.25
        cagr = (equity.iloc[-1] ** (1/max(years, 0.1))) - 1

        vol = net_ret.std() * np.sqrt(252)
        sharpe = (cagr / vol) if vol > 0 else 0

        calmar = abs(cagr / max_dd) if max_dd < 0 else 0

        trade_count = (turnover > 0).sum() / 2

        return {
            "cagr": cagr,
            "sharpe": sharpe,
            "max_dd": max_dd,
            "calmar": calmar,
            "trades": trade_count,
            "turnover": turnover.mean(),
            "equity": equity,
            "total_return": total_ret
        }
