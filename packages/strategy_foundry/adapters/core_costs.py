from typing import Dict, Any
from pydantic import BaseModel

# Adapter for core costs/risk if needed
# We are not using core risk models heavily in Foundry yet (simple slip/fee).
# But just to satisfy structure.

class RiskConfig(BaseModel):
    slippage_bps: float = 5.0
    fees_per_order: float = 20.0
