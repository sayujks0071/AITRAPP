"""
Ranking and Selection Logic.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any

class Ranker:
    @staticmethod
    def calculate_metrics(trades: List[Dict]) -> Dict[str, float]:
        if not trades:
            return {
                "sharpe": 0.0,
                "calmar": 0.0,
                "cagr": 0.0,
                "max_dd": 0.0,
                "trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "stability": 0.0
            }

        df = pd.DataFrame(trades)
        df["ret"] = df["pnl"] / df["entry_price"]

        # Win Rate
        win_rate = len(df[df["pnl"] > 0]) / len(df)

        # Profit Factor
        gross_profit = df[df["pnl"] > 0]["pnl"].sum()
        gross_loss = abs(df[df["pnl"] < 0]["pnl"].sum())
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else 999.0

        # Equity Curve for DD
        df["cum_pnl"] = df["pnl"].cumsum()
        peak = df["cum_pnl"].cummax()
        dd = (df["cum_pnl"] - peak) # Absolute DD
        # Relative DD requires base capital. Assuming fixed size logic, better use % DD of underlying price?
        # Or just use max absolute DD / avg price?
        # Using % returns for Sharpe/DD is standard.

        # Returns Series
        # Reconstruct daily returns? Or trade returns.
        # Trade returns series

        # Sharpe (Trade based, annualized approx)
        avg_ret = df["ret"].mean()
        std_ret = df["ret"].std()
        sharpe = (avg_ret / std_ret) * np.sqrt(252 * (len(df)/60)) if std_ret != 0 else 0 # Approximation

        # Max Drawdown (on returns)
        cum_ret = (1 + df["ret"]).cumprod()
        peak_ret = cum_ret.cummax()
        dd_pct = (cum_ret - peak_ret) / peak_ret
        max_dd = abs(dd_pct.min())

        # Calmar
        cagr = df["ret"].sum() # Simple sum for now, should be annualized
        calmar = cagr / max_dd if max_dd != 0 else 0

        # Helper for WFA
        pnl_positive = gross_profit > gross_loss

        return {
            "sharpe": sharpe,
            "calmar": calmar,
            "cagr": cagr,
            "max_dd": max_dd,
            "trades": len(trades),
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "stability": 1.0, # Placeholder, updated by WFA
            "pnl_positive": pnl_positive
        }

    @staticmethod
    def score(metrics: Dict[str, float], weights: Dict[str, float] = None) -> float:
        if weights is None:
            weights = {
                "sharpe": 0.25,
                "calmar": 0.25,
                "cagr": 0.20,
                "stability": 0.15,
                "turnover_bonus": 0.10,
                "intraday_sanity": 0.05
            }

        score = (
            weights["sharpe"] * min(metrics["sharpe"], 3.0) + # Cap sharpe
            weights["calmar"] * min(metrics["calmar"], 3.0) +
            weights["cagr"] * metrics["cagr"] * 10 + # Scale up
            weights["stability"] * metrics["stability"]
        )
        return score

    @staticmethod
    def filter_candidates(results: List[Dict], config: Dict) -> List[Dict]:
        """Apply hard gates."""
        passing = []
        for r in results:
            m = r["metrics"]
            if m["trades"] < config["risk"]["min_trades"]:
                continue
            if m["max_dd"] > (config["risk"]["max_dd_percent"] / 100.0):
                continue
            if m["sharpe"] < config["risk"].get("min_sharpe", 0.5):
                continue
            passing.append(r)
        return passing
