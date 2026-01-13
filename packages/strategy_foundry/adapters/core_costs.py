"""Adapter for core costs"""
from packages.core.config import RiskConfig
from packages.core.risk import RiskManager

# Simplified cost model for backtesting if full RiskManager is overkill
# But we can reuse RiskManager.estimate_fees logic

class CostAdapter:
    def __init__(self, slippage_bps=5.0):
        # Default config for estimation
        self.config = RiskConfig(
            max_capital=100000,
            per_trade_risk_pct=1.0,
            daily_loss_stop_pct=2.0
        )
        self.risk_manager = RiskManager(self.config)
        self.slippage_bps = slippage_bps

    def estimate_cost_bps(self, instrument_type="equity") -> float:
        """Return estimated total cost in BPS per side (slippage + fees)"""
        # Very rough estimation based on recent tax laws
        # STT + Exchange + Brokerage ~ 3-4bps per side for equity intraday
        # Plus slippage
        base_fees = 4.0 # 0.04%
        return self.slippage_bps + base_fees
