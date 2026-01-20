"""Wrapper for Core Costs"""
# Simple cost model, in future link to packages.core.execution cost models

class CostModel:
    def __init__(self, bps_per_side: float = 5.0, slippage_bps: float = 5.0):
        self.bps = bps_per_side
        self.slippage = slippage_bps

    def get_total_cost_bps(self) -> float:
        return self.bps + self.slippage
