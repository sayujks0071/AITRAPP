"""
Cost model for backtesting.
"""
from packages.strategy_foundry.adapters.core_costs import CostAdapter

class BacktestCostModel:
    def __init__(self, slippage_bps: int = 5, all_in_cost_bps: int = None):
        """
        If all_in_cost_bps is provided, it overrides granular fee calculation.
        Otherwise uses CostAdapter.
        """
        self.slippage_bps = slippage_bps
        self.all_in_cost_bps = all_in_cost_bps

    def estimate_cost(self, price: float, quantity: int, side: str, instrument_type: str = "EQUITY") -> float:
        """
        Returns total cost in currency units (e.g. INR) for this transaction leg.
        Includes Slippage + Fees.
        """
        turnover = price * quantity

        # Slippage cost
        slippage_cost = turnover * (self.slippage_bps / 10000.0)

        # Fee cost
        if self.all_in_cost_bps is not None:
            fee_cost = turnover * (self.all_in_cost_bps / 10000.0)
        else:
            fee_cost = CostAdapter.estimate_costs(instrument_type, price, quantity, turnover)
            # Add STT if Sell side
            stt_rate = CostAdapter.get_stt_rate(instrument_type, side)
            fee_cost += turnover * stt_rate

        return slippage_cost + fee_cost
