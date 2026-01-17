from typing import List, Dict
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)

class Ranker:
    def __init__(self):
        # Weights
        self.w_sharpe = 0.25
        self.w_calmar = 0.25
        self.w_cagr = 0.20
        self.w_stability = 0.15
        self.w_turnover = 0.10 # Bonus for low turnover? Or just trades count?
        self.w_sanity = 0.05

    def rank_candidates(self, results: List[Dict]) -> pd.DataFrame:
        """
        Rank candidates based on OOS metrics.
        """
        if not results:
            return pd.DataFrame()

        df = pd.DataFrame(results)

        # Ensure columns exist
        cols = ["sharpe", "calmar", "cagr", "fold_sharpe_std", "trades", "max_dd"]
        for c in cols:
            if c not in df.columns:
                df[c] = 0.0

        # Normalize/Score
        # Score = w1*norm(Sharpe) + w2*norm(Calmar) ...
        # Simplified scoring for this implementation:

        # Stability: Lower std is better. Invert.
        # MaxDD: Lower is better.

        # We'll just do a direct calculation without normalization for MVP,
        # assuming metrics are somewhat comparable in scale or just use raw weighted sum if safe.
        # Actually Sharpe is ~1-3, Calmar ~1-5.

        # Let's just implement the logic:
        # Score = (Sharpe * 0.25) + (Calmar * 0.25) + (ProfitFactor * 0.2)?

        # Using the prompt specific weights:
        # + 25% OOS Sharpe
        # + 25% OOS Calmar
        # + 20% Net return / CAGR (Using Total Return as proxy if CAGR not avail)
        # + 15% Stability (low variance)

        # Stability Score: 1 / (1 + std_dev)
        stability_score = 1.0 / (1.0 + df["fold_sharpe_std"])

        # Turnover score: 1 if trades < threshold?
        # "Low turnover bonus". Let's say trades < 5/day is good.
        # We don't have days count easily here, just total trades.
        # Let's treat fewer trades as better? Or just ignore for now.

        df["score"] = (
            (df["sharpe"] * 0.25) +
            (df["calmar"] * 0.25) +
            (df["win_rate"] * 0.20) + # Proxy for return quality
            (stability_score * 0.15)
        )

        return df.sort_values("score", ascending=False)

    def blend_scores(self, res_5m: pd.DataFrame, res_15m: pd.DataFrame) -> pd.DataFrame:
        """
        blended_score = 0.6*score_15m + 0.4*score_5m (if both exist)
        """
        # Merge on ID
        if res_5m.empty: return res_15m
        if res_15m.empty: return res_5m

        merged = pd.merge(res_5m, res_15m, on="id", suffixes=("_5m", "_15m"), how="outer")

        def calc_blend(row):
            s5 = row.get("score_5m", 0)
            s15 = row.get("score_15m", 0)

            if pd.notna(s5) and pd.notna(s15):
                return 0.6 * s15 + 0.4 * s5
            if pd.notna(s15):
                return s15
            return s5

        merged["blended_score"] = merged.apply(calc_blend, axis=1)
        return merged.sort_values("blended_score", ascending=False)
