from packages.core.risk import RiskManager, RiskConfig

class CostEstimator:
    """
    Adapter for cost estimation.
    """
    def __init__(self):
        # Default risk config for cost estimation
        self.risk_config = RiskConfig(
             max_capital_per_strategy=100000,
             max_drawdown_per_strategy=0.2,
             max_risk_per_trade=0.01
        )
        self.rm = RiskManager(self.risk_config)

    def estimate_fees(self, instrument, quantity, entry, exit):
        return self.rm.estimate_fees(instrument, quantity, entry, exit)
