from typing import Dict
from pydantic import BaseModel

class RiskConfig(BaseModel):
    slippage_bps: float = 2.0
    brokerage_per_order: float = 20.0
    tax_bps: float = 3.0
    spread_guard_bps: float = 1.0

def get_default_costs() -> RiskConfig:
    return RiskConfig()
