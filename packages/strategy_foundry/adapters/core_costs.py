"""
Adapter for costs and taxes.
"""
from packages.core.config import TaxConfig

class CostAdapter:
    @staticmethod
    def estimate_costs(instrument_type: str, price: float, quantity: int, turnover: float) -> float:
        """
        Estimate costs for a single side of a trade (buy or sell).
        This is a simplified version of `RiskManager.estimate_fees` adapted for backtesting use.
        """
        fees = 0.0

        # Base brokerage (simplified assumption: 20 Rs flat or 0.03%)
        # For backtesting, we often care about bps impact.
        # But let's try to be precise if we can.

        # Exchange Txn Charges
        txn_charges = 0.0
        stt = 0.0

        if instrument_type == "EQUITY":
            txn_charges = turnover * TaxConfig.TXN_NSE_EQUITY
            # STT is only on Sell for Intraday Equity
            # We will assume this is called per side, so the caller needs to handle STT application (usually on sell)
            # But wait, TaxConfig defines STT rates.
            pass
        elif instrument_type == "FUTURES":
            txn_charges = turnover * TaxConfig.TXN_NSE_FUTURES
        elif instrument_type == "OPTIONS":
            txn_charges = turnover * TaxConfig.TXN_NSE_OPTIONS

        fees += txn_charges

        # GST
        fees *= (1 + TaxConfig.GST_RATE)

        # SEBI
        fees += turnover * TaxConfig.SEBI_CHARGES

        return fees

    @staticmethod
    def get_stt_rate(instrument_type: str, side: str) -> float:
        """
        Return STT rate as a fraction of turnover.
        """
        if side != "SELL":
            return 0.0

        if instrument_type == "EQUITY":
            return TaxConfig.STT_EQUITY_INTRADAY_SELL
        elif instrument_type == "FUTURES":
            return TaxConfig.STT_FUTURES_SELL
        elif instrument_type == "OPTIONS":
            return TaxConfig.STT_OPTIONS_SELL
        return 0.0
