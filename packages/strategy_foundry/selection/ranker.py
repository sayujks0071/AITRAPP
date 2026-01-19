from typing import Dict


class Ranker:
    def __init__(self):
        # Weights
        self.w_sharpe = 0.25
        self.w_calmar = 0.25
        self.w_cagr = 0.20
        self.w_stability = 0.15
        self.w_turnover = 0.10
        self.w_sanity = 0.05

    def score_candidate(self, metrics: Dict[str, float], sanity: Dict[str, bool]) -> float:
        """
        Computes a raw score 0-100 for a single run.
        """
        # 1. Normalize Metrics (Approximate boundaries for normalization)
        # Sharpe: Target 2.0+
        sharpe_score = min(max(metrics["sharpe"] / 2.0, 0), 1) * 100

        # Calmar: Target 3.0+
        calmar_score = min(max(metrics["calmar"] / 3.0, 0), 1) * 100

        # CAGR: Target 50%+
        cagr_score = min(max(metrics["cagr"] / 0.50, 0), 1) * 100

        # Stability (Profit Factor as proxy here, or win rate consistency)
        # Target PF 2.0
        pf_score = min(max((metrics["profit_factor"] - 1.0) / 1.0, 0), 1) * 100

        # Turnover (Low is better? Or just "Healthy")
        # If too low (0), bad. If too high (>20/day), bad.
        # Let's use avg_trade_pct. Higher avg trade return is more robust to slippage.
        # Target 0.5% avg trade
        trade_qual_score = min(max(metrics["avg_trade_pct"] / 0.005, 0), 1) * 100

        # Sanity Penalty
        sanity_score = 100
        if not sanity["late_day_dependence"]: sanity_score -= 50
        if not sanity["overtrade"]: sanity_score -= 50
        sanity_score = max(sanity_score, 0)

        total_score = (
            sharpe_score * self.w_sharpe +
            calmar_score * self.w_calmar +
            cagr_score * self.w_cagr +
            pf_score * self.w_stability +
            trade_qual_score * self.w_turnover +
            sanity_score * self.w_sanity
        )

        return total_score

    def blend_scores(self, score_15m: float, score_5m: float) -> float:
        # 60% 15m, 40% 5m
        if score_15m is not None and score_5m is not None:
            return 0.6 * score_15m + 0.4 * score_5m
        elif score_15m is not None:
            return score_15m
        elif score_5m is not None:
            return score_5m
        return 0.0

    def is_eligible(self, metrics_15m: Dict, metrics_5m: Dict, sanity_15m: Dict, sanity_5m: Dict) -> bool:
        """
        Gates for Live Eligibility.
        """
        # Must have at least one valid timeframe
        if not metrics_15m and not metrics_5m:
            return False

        valid_15 = False
        if metrics_15m:
            valid_15 = (
                metrics_15m["sharpe"] >= 1.2 and
                metrics_15m["max_dd"] <= 0.25 and
                sanity_15m["late_day_dependence"] and
                sanity_15m["min_trades"]
            )

        valid_5 = False
        if metrics_5m:
            valid_5 = (
                metrics_5m["sharpe"] >= 1.2 and
                metrics_5m["max_dd"] <= 0.25 and
                sanity_5m["late_day_dependence"] and
                sanity_5m["min_trades"]
            )

        # If both exist, both must be "Okayish" but we really care about the blended result.
        # Requirement: "blended OOS Sharpe >= 1.2"
        # Let's simplify: if 15m exists, it must pass. If 5m exists, it must pass.

        if metrics_15m and not valid_15: return False
        if metrics_5m and not valid_5: return False

        return True
