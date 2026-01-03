from dataclasses import dataclass
from typing import Optional
from packages.core.models import Instrument, InstrumentType

# Tax Rates (2024-2025) - Copied from packages/core/risk.py for stability
STT_EQUITY_INTRADAY_SELL = 0.00025
STT_FUTURES_SELL = 0.000125
STT_OPTIONS_SELL = 0.000625

TXN_NSE_EQUITY = 0.0000325
TXN_NSE_FUTURES = 0.000019
TXN_NSE_OPTIONS = 0.0005

class CostEstimator:
    def __init__(self, fees_per_order: float = 20.0):
        self.fees_per_order = fees_per_order

    def estimate_fees(
        self,
        instrument: Instrument,
        quantity: int,
        entry_price: float,
        exit_price: float
    ) -> float:
        """
        Estimate trading fees for a round trip.
        """
        turnover = quantity * (entry_price + exit_price)
        fees = 0.0

        # Brokerage
        fees += self.fees_per_order * 2

        # Exchange Transaction Charges
        txn_charges = 0.0
        if instrument.exchange in ["NSE", "BSE", "NFO"]:
            if instrument.is_equity:
                txn_charges = turnover * TXN_NSE_EQUITY
            elif instrument.is_future:
                txn_charges = turnover * TXN_NSE_FUTURES
            elif instrument.is_option:
                txn_charges = turnover * TXN_NSE_OPTIONS
        else:
            txn_charges = turnover * 0.00002

        fees += txn_charges

        # GST (18% on Brokerage + Transaction)
        fees += (self.fees_per_order * 2 + txn_charges) * 0.18

        # STT
        stt = 0.0
        if instrument.is_equity:
            # Assuming Intraday
            stt = (exit_price * quantity) * STT_EQUITY_INTRADAY_SELL
        elif instrument.is_future:
            stt = (exit_price * quantity) * STT_FUTURES_SELL
        elif instrument.is_option:
            stt = (exit_price * quantity) * STT_OPTIONS_SELL

        fees += stt

        # SEBI charges
        fees += (turnover / 10000000) * 10

        # Stamp duty (buy side only)
        fees += (entry_price * quantity) * 0.00003

        return fees

def get_instrument(symbol: str) -> Instrument:
    """Helper to create instrument object for cost calc"""
    # Default to NIFTY/SENSEX generic instruments
    return Instrument(
        token=0,
        symbol=symbol,
        tradingsymbol=symbol,
        exchange="NSE" if symbol == "NIFTY" else "BSE",
        instrument_type=InstrumentType.EQ, # Treat indices as Equity-like for cost base, or FUT?
        # Indices aren't traded directly, but ETFs/Futures are.
        # Strategy Foundry is usually on Spot Index for signal generation?
        # User prompt says "NIFTY/SENSEX index" but "trades table", "equity curve".
        # You can't trade index spot. You trade futures or ETFs.
        # I'll assume we are trading "Index Futures" for cost simulation or "Equity" if it's meant to be ETF.
        # Given "strategy_foundry" usually implies futures for indices.
        # But let's check assumptions.
        # "2) Data loader rules (NIFTY/SENSEX)" -> ^NSEI, ^BSESN (Spot).
        # "4) Backtest engine ... Costs: slippage_bps ... all_in_cost_bps".
        # If I use `all_in_cost_bps`, I might not need `CostEstimator`.
        # But user says "Reuse packages/core ... cost/risk utilities IF they exist".
        # `packages/core/risk.py` has detailed fee calc.
        # I'll stick to a default simple `all_in_cost_bps` for backtest as per requirement 4,
        # but provide `CostEstimator` if needed for detailed reports.
        # I'll assume FUTURE for indices for cost calc if used.
    )
