"""
Portfolio Snapshot Engine - Level 13 Broker-Grade Command Center
================================================================

Real-time reconciliation between Algo's view and Broker's (Kite) actual ledger.
Provides fund management capabilities beyond basic bot monitoring.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

import structlog

from packages.core.position_store import PositionStore
from packages.core.models import Position, PositionStatus

logger = structlog.get_logger(__name__)


@dataclass
class BrokerFunds:
    net: float
    available_cash: float
    withdrawable: float
    used_margin: float
    utilisation_pct: float
    collateral: float


@dataclass
class BrokerPosition:
    instrument: str
    segment: str
    qty: int
    avg_price: float
    last_price: float
    pnl: float
    delta: float
    strategy: str


@dataclass
class PortfolioSnapshot:
    funds: BrokerFunds
    positions: List[BrokerPosition]
    broker_positions_count: int
    algo_positions_count: int
    drift_count: int
    drift_details: List[str]
    indices: Dict[str, Any]  # NIFTY 50 and BANKNIFTY prices


class PortfolioSnapshotEngine:
    """
    Level 13: Broker-Grade Portfolio Snapshot Engine
    
    Reconciles Algo's view with Broker's actual ledger in real-time.
    """

    def __init__(self, kite, position_store: Optional[PositionStore] = None):
        self.kite = kite
        self.position_store = position_store

    async def build_snapshot(self) -> Dict[str, Any]:
        """
        Build comprehensive portfolio snapshot from Kite broker data.
        
        Returns:
            PortfolioSnapshot as dict
        """
        # 1. Fetch Funds (Margins)
        try:
            m = self.kite.margins()
            eq = m.get("equity", {})
            avail = eq.get("available", {})
            util = eq.get("utilised", {})
            coll = eq.get("collateral", {})

            available_cash = float(avail.get("cash", 0.0))
            used_margin = float(util.get("debits", 0.0) + util.get("premium", 0.0))
            net = float(eq.get("net", available_cash))  # Fallback
            withdrawable = float(avail.get("withdrawable", 0.0))
            collateral = float(coll.get("collateral", 0.0))
            
            total_capital = used_margin + available_cash
            util_pct = (used_margin / total_capital * 100) if total_capital else 0.0

            funds = BrokerFunds(
                net=net,
                available_cash=available_cash,
                withdrawable=withdrawable,
                used_margin=used_margin,
                utilisation_pct=util_pct,
                collateral=collateral
            )
        except Exception as e:
            logger.error("Failed to fetch margins", error=str(e), exc_info=True)
            # Fallback for mock/offline
            funds = BrokerFunds(0, 0, 0, 0, 0, 0)

        # 2. Fetch Positions
        try:
            raw_pos = self.kite.positions().get("net", [])
        except Exception as e:
            logger.error("Failed to fetch positions", error=str(e), exc_info=True)
            raw_pos = []

        # Build strategy mapping from PositionStore
        strategy_map = {}
        if self.position_store:
            for pos_id, pos in self.position_store.positions.items():
                if pos.status == PositionStatus.OPEN and pos.instrument:
                    symbol = pos.instrument.symbol
                    strategy_map[symbol] = pos.strategy_name

        positions = []
        for p in raw_pos:
            qty = int(p.get("quantity", 0))
            if qty == 0:
                continue
            
            inst = p.get("tradingsymbol", "UNKNOWN")
            ltp = float(p.get("last_price", p.get("close_price", 0)))
            avg = float(p.get("average_price", 0))
            pnl = (ltp - avg) * qty if avg > 0 else 0.0
            
            # Strategy Tag Mapping (from PositionStore if available)
            # Improved reconciliation: Check PositionStore first, then fallback
            strategy_tag = strategy_map.get(inst, None)
            
            if strategy_tag is None:
                # Better heuristic: Check if instrument matches any algo strategy pattern
                # This improves Manual vs Algo tag accuracy
                if "NIFTY" in inst or "BANKNIFTY" in inst:
                    if "CE" in inst or "PE" in inst:
                        # Options - likely from OptionsRanker or short strangle strategies
                        strategy_tag = "OptionsRanker"  # Default, but could be refined
                    elif "FUT" in inst:
                        strategy_tag = "Futures"
                    else:
                        strategy_tag = "Manual"
                else:
                    strategy_tag = "Manual"
            
            # Greek Approximation (Delta)
            delta = 0.0
            if "CE" in inst:
                delta = 0.5  # Call option approximation
            elif "PE" in inst:
                delta = -0.5  # Put option approximation
            elif "FUT" in inst:
                delta = 1.0 if qty > 0 else -1.0  # Futures delta

            positions.append(BrokerPosition(
                instrument=inst,
                segment=p.get("product", "NRML"),
                qty=qty,
                avg_price=avg,
                last_price=ltp,
                pnl=pnl,
                delta=delta,
                strategy=strategy_tag
            ))

        # 3. Reconciliation (Drift Detection)
        algo_positions = []
        if self.position_store:
            algo_positions = self.position_store.get_open_positions()
        
        broker_syms = {p.instrument for p in positions}
        algo_syms = {
            pos.instrument.symbol for pos in algo_positions
            if pos.instrument
        }
        drift = broker_syms.symmetric_difference(algo_syms)
        drift_details = list(drift)

        # 4. Fetch Live Indices (NIFTY 50 and BANKNIFTY)
        indices = {}
        try:
            index_instruments = ["NSE:NIFTY 50", "NSE:NIFTY BANK"]
            ltp_data = self.kite.ltp(index_instruments)
            
            # Parse NIFTY 50
            nifty_key = "NSE:NIFTY 50"
            if nifty_key in ltp_data:
                nifty_data = ltp_data[nifty_key]
                nifty_ltp = float(nifty_data.get("last_price", 0))
                nifty_net_change = float(nifty_data.get("net_change", 0))
                nifty_change_pct = (nifty_net_change / (nifty_ltp - nifty_net_change) * 100) if (nifty_ltp - nifty_net_change) > 0 else 0
                indices["nifty"] = {
                    "ltp": nifty_ltp,
                    "change": nifty_net_change,
                    "change_pct": nifty_change_pct
                }
            
            # Parse BANKNIFTY
            bank_key = "NSE:NIFTY BANK"
            if bank_key in ltp_data:
                bank_data = ltp_data[bank_key]
                bank_ltp = float(bank_data.get("last_price", 0))
                bank_net_change = float(bank_data.get("net_change", 0))
                bank_change_pct = (bank_net_change / (bank_ltp - bank_net_change) * 100) if (bank_ltp - bank_net_change) > 0 else 0
                indices["banknifty"] = {
                    "ltp": bank_ltp,
                    "change": bank_net_change,
                    "change_pct": bank_change_pct
                }
        except Exception as e:
            logger.warning("Failed to fetch indices LTP", error=str(e))
            indices = {
                "nifty": {"ltp": 0, "change": 0, "change_pct": 0},
                "banknifty": {"ltp": 0, "change": 0, "change_pct": 0}
            }

        snap = PortfolioSnapshot(
            funds=funds,
            positions=sorted(positions, key=lambda x: abs(x.pnl), reverse=True),  # Top risk first
            broker_positions_count=len(positions),
            algo_positions_count=len(algo_positions),
            drift_count=len(drift),
            drift_details=drift_details,
            indices=indices
        )
        
        return asdict(snap)

    def build_snapshot_sync(self) -> Dict[str, Any]:
        """
        Synchronous version for non-async contexts.
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, we can't use run()
                # Return a task or use a different approach
                raise RuntimeError("Cannot use sync method in async context. Use build_snapshot() instead.")
        except RuntimeError:
            pass
        
        return asyncio.run(self.build_snapshot())


# Backward compatibility function
def build_portfolio_snapshot(
    kite: Any,
    position_store: Optional[PositionStore] = None,
) -> Dict[str, Any]:
    """
    Backward compatibility wrapper for the new PortfolioSnapshotEngine.
    """
    engine = PortfolioSnapshotEngine(kite, position_store)
    try:
        return engine.build_snapshot_sync()
    except Exception as e:
        logger.error("Failed to build snapshot", error=str(e), exc_info=True)
        # Return empty snapshot on error
        return {
            "funds": asdict(BrokerFunds(0, 0, 0, 0, 0, 0)),
            "positions": [],
            "broker_positions_count": 0,
            "algo_positions_count": 0,
            "drift_count": 0,
            "drift_details": [],
            "indices": {
                "nifty": {"ltp": 0, "change": 0, "change_pct": 0},
                "banknifty": {"ltp": 0, "change": 0, "change_pct": 0}
            }
        }
