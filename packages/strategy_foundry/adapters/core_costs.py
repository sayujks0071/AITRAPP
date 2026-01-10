"""Adapter for Core Costs"""
from typing import NamedTuple

class CostModel(NamedTuple):
    slippage_bps: float
    brokerage_per_order: float
    tax_pct: float

# Default simplified costs
DEFAULT_COSTS = CostModel(
    slippage_bps=5.0,        # 5 bps slippage
    brokerage_per_order=20.0, # Rs 20 flat
    tax_pct=0.1              # ~0.1% taxes/charges rough estimate
)

def estimate_total_transaction_cost(price: float, quantity: int, side: str = "BUY") -> float:
    """
    Simple all-in cost estimator for backtesting.

    Args:
        price: Execution price
        quantity: Number of shares/lots
        side: BUY or SELL

    Returns:
        Total cost in currency units
    """
    # 1. Slippage
    slippage = (price * quantity) * (DEFAULT_COSTS.slippage_bps / 10000)

    # 2. Brokerage (Flat)
    brokerage = DEFAULT_COSTS.brokerage_per_order

    # 3. Taxes/Charges (Percent of turnover)
    turnover = price * quantity
    taxes = turnover * (DEFAULT_COSTS.tax_pct / 100)

    return slippage + brokerage + taxes
