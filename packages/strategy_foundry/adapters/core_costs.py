"""
Cost assumptions adapter.
"""
from dataclasses import dataclass

@dataclass
class CostModel:
    slippage_bps: float = 5.0
    brokerage_per_order: float = 20.0
    stt_pct: float = 0.1  # Securities Transaction Tax (Delivery)
    gst_pct: float = 18.0 # GST on brokerage
    sebi_charges_pct: float = 0.0001
    stamp_duty_pct: float = 0.015

    def estimate_transaction_cost(self, price: float, quantity: int, side: str) -> float:
        """
        Estimate cost for a single transaction (one leg).
        Simple all-in approximation can be used if exact tax calculation is too complex for backtest loop.
        """
        turnover = price * quantity

        # Slippage
        slippage = turnover * (self.slippage_bps / 10000.0)

        # Brokerage (Flat 20 or 0.03% whichever is lower usually, but simplified to flat 20 for F&O or similar)
        # Using flat 20 as conservative estimate for intraday/F&O
        brokerage = 20.0

        # Taxes
        # STT (0.1% for equity delivery, 0.025% for intraday equity selling, 0.125% for options selling, 0.0125% for futures selling)
        # We'll assume a blended rate or conservative rate.
        # Let's use a simplified "all-in" BPS for backtesting speed if desired, or detailed.
        # Instructions say "all_in_cost_bps" as a simple default.

        return slippage + brokerage # Simplified, backtest engine might use bps

def get_default_cost_model() -> CostModel:
    return CostModel()
