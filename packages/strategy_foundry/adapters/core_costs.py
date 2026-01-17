class CostAdapter:
    """
    Provides cost assumptions for backtesting.
    Defaults if core config is missing or too complex.
    """
    # Default assumptions for NIFTY/SENSEX
    SLIPPAGE_BPS = 2.0  # 0.02% per side
    COMMISSION_BPS = 1.0  # ~0.01% per side (STT is higher on delivery, but this is index/derivatives proxy)

    # STT on Sell for Futures: 0.0125%
    # STT on Sell for Options: 0.0625% (on premium)
    # Since we are simulating "Strategy" on Index, we'll model it as Futures-like exposure.
    # Total round trip cost ~ 3-4 bps.

    ALL_IN_COST_BPS = 3.5

    @staticmethod
    def get_costs():
        return {
            "slippage_bps": CostAdapter.SLIPPAGE_BPS,
            "all_in_cost_bps": CostAdapter.ALL_IN_COST_BPS
        }
