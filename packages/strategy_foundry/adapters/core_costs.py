"""
Core Costs Adapter
Defines cost models for backtesting.
"""
from dataclasses import dataclass

@dataclass
class CostModel:
    slippage_bps: float
    commission_bps: float
    flat_fee: float

# Conservative defaults for Intraday Equity/F&O
DEFAULT_COSTS = CostModel(
    slippage_bps=5.0,     # 0.05% slippage per side
    commission_bps=3.0,   # ~0.03% taxes/charges
    flat_fee=20.0         # Brokerage
)
