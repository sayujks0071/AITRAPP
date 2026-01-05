"""
Core Costs Adapter
Defines trading costs using packages/core/risk.py if available or defaults.
"""
from typing import NamedTuple

class CostModel(NamedTuple):
    slippage_bps: float
    commission_bps: float
    fixed_per_order: float

# Default conservative costs for Indian Equity/Derivatives
DEFAULT_COSTS = CostModel(
    slippage_bps=5.0,     # 0.05% slippage
    commission_bps=3.0,   # 0.03% approx blended taxes/charges
    fixed_per_order=0.0   # Simplified, use bps mostly
)
