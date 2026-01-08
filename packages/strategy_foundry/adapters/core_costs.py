"""
Cost adapter.
Simple cost model for backtesting.
"""
from typing import NamedTuple

class CostModel(NamedTuple):
    slippage_bps: float
    brokerage_per_order: float
    tax_bps: float  # blended STT + other taxes

    def estimate_cost(self, price: float, quantity: int, side: str) -> float:
        """
        Estimate total cost for a trade leg.
        """
        value = price * quantity

        # Slippage
        slippage = value * (self.slippage_bps / 10000.0)

        # Brokerage (simplified flat fee)
        brokerage = self.brokerage_per_order

        # Taxes
        taxes = value * (self.tax_bps / 10000.0)

        return slippage + brokerage + taxes

DEFAULT_COST_MODEL = CostModel(
    slippage_bps=5.0,        # 5 bps slippage
    brokerage_per_order=20.0, # Rs 20 flat
    tax_bps=3.0              # Approx taxes
)
