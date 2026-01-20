from dataclasses import dataclass

@dataclass
class TransactionCosts:
    slippage_bps_per_side: float = 5.0
    brokerage_per_order: float = 0.0 # Can be set to 20 or similar
    tax_bps: float = 0.0 # STT, etc. if we want simple bps model

    # Simplified "All-in" cost
    all_in_cost_bps_per_side: float = 10.0

class CostAdapter:
    """
    Adapter for cost calculations.
    """
    def __init__(self, slippage_bps: float = 5.0, all_in_cost_bps: float = 10.0):
        self.costs = TransactionCosts(
            slippage_bps_per_side=slippage_bps,
            all_in_cost_bps_per_side=all_in_cost_bps
        )

    def estimate_total_cost_bps(self) -> float:
        """Total round-trip cost in bps (slippage + fees)"""
        # 2 sides
        return (self.costs.slippage_bps_per_side + self.costs.all_in_cost_bps_per_side) * 2
