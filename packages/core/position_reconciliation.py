"""Position reconciliation between system database and Kite API"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ReconciliationResult:
    """Result of position reconciliation"""
    matched_positions: int
    missing_in_system: List[Dict]  # Positions in Kite but not in system
    missing_in_kite: List[Dict]  # Positions in system but not in Kite
    quantity_mismatches: List[Dict]  # Positions with quantity differences
    price_mismatches: List[Dict]  # Positions with avg price differences
    total_discrepancies: int

    def is_clean(self) -> bool:
        """Check if reconciliation is clean (no discrepancies)"""
        return self.total_discrepancies == 0

    def summary(self) -> str:
        """Get a summary string"""
        if self.is_clean():
            return f"✓ Clean reconciliation: {self.matched_positions} positions matched"

        lines = [
            f"⚠ Reconciliation found {self.total_discrepancies} discrepancies:",
            f"  - Matched positions: {self.matched_positions}",
        ]

        if self.missing_in_system:
            lines.append(f"  - Missing in system: {len(self.missing_in_system)}")
        if self.missing_in_kite:
            lines.append(f"  - Missing in Kite: {len(self.missing_in_kite)}")
        if self.quantity_mismatches:
            lines.append(f"  - Quantity mismatches: {len(self.quantity_mismatches)}")
        if self.price_mismatches:
            lines.append(f"  - Price mismatches: {len(self.price_mismatches)}")

        return "\n".join(lines)


class PositionReconciler:
    """
    Reconcile positions between system database and Kite API.

    This helps identify discrepancies such as:
    - Positions filled in Kite but not tracked in system
    - Positions closed in Kite but still open in system
    - Quantity mismatches between system and Kite
    - Average price differences
    """

    def __init__(self, kite_client, db_session=None):
        self.kite = kite_client
        self.db_session = db_session

    async def reconcile(self) -> ReconciliationResult:
        """
        Perform full position reconciliation between system and Kite.

        Returns:
            ReconciliationResult with all discrepancies identified
        """
        logger.info("Starting position reconciliation")

        # Get positions from both sources
        kite_positions = await self._fetch_kite_positions()
        system_positions = await self._fetch_system_positions()

        # Build lookup dictionaries keyed by trading symbol
        kite_by_symbol = {p["tradingsymbol"]: p for p in kite_positions}
        system_by_symbol = {p["symbol"]: p for p in system_positions}

        # Track results
        matched = 0
        missing_in_system = []
        missing_in_kite = []
        quantity_mismatches = []
        price_mismatches = []

        # Check positions in Kite
        for symbol, kite_pos in kite_by_symbol.items():
            system_pos = system_by_symbol.get(symbol)

            if not system_pos:
                # Position exists in Kite but not in system
                missing_in_system.append({
                    "symbol": symbol,
                    "kite_qty": kite_pos["quantity"],
                    "kite_avg_price": kite_pos.get("average_price", 0),
                    "kite_pnl": kite_pos.get("pnl", 0),
                })
                logger.warning(
                    "Position missing in system",
                    symbol=symbol,
                    quantity=kite_pos["quantity"],
                )
            else:
                # Position exists in both, check for mismatches
                matched += 1

                # Check quantity
                kite_qty = kite_pos["quantity"]
                system_qty = system_pos["quantity"]

                if kite_qty != system_qty:
                    quantity_mismatches.append({
                        "symbol": symbol,
                        "kite_qty": kite_qty,
                        "system_qty": system_qty,
                        "difference": kite_qty - system_qty,
                    })
                    logger.warning(
                        "Quantity mismatch",
                        symbol=symbol,
                        kite_qty=kite_qty,
                        system_qty=system_qty,
                    )

                # Check average price (with tolerance for rounding)
                kite_price = kite_pos.get("average_price", 0)
                system_price = system_pos.get("entry_price", 0)
                price_tolerance = 0.01  # ±1 paisa tolerance

                if abs(kite_price - system_price) > price_tolerance:
                    price_mismatches.append({
                        "symbol": symbol,
                        "kite_price": kite_price,
                        "system_price": system_price,
                        "difference": kite_price - system_price,
                    })
                    logger.warning(
                        "Price mismatch",
                        symbol=symbol,
                        kite_price=kite_price,
                        system_price=system_price,
                    )

        # Check positions in system that are not in Kite
        for symbol, system_pos in system_by_symbol.items():
            if symbol not in kite_by_symbol:
                # Position exists in system but not in Kite (might be closed)
                missing_in_kite.append({
                    "symbol": symbol,
                    "system_qty": system_pos["quantity"],
                    "system_entry_price": system_pos.get("entry_price", 0),
                })
                logger.warning(
                    "Position missing in Kite",
                    symbol=symbol,
                    quantity=system_pos["quantity"],
                )

        # Calculate total discrepancies
        total_discrepancies = (
            len(missing_in_system)
            + len(missing_in_kite)
            + len(quantity_mismatches)
            + len(price_mismatches)
        )

        result = ReconciliationResult(
            matched_positions=matched,
            missing_in_system=missing_in_system,
            missing_in_kite=missing_in_kite,
            quantity_mismatches=quantity_mismatches,
            price_mismatches=price_mismatches,
            total_discrepancies=total_discrepancies,
        )

        logger.info(
            "Position reconciliation completed",
            matched=matched,
            discrepancies=total_discrepancies,
        )

        return result

    async def _fetch_kite_positions(self) -> List[Dict]:
        """
        Fetch current positions from Kite API.

        Returns:
            List of position dictionaries with keys:
            - tradingsymbol
            - quantity (net quantity)
            - average_price
            - pnl (unrealized P&L)
        """
        try:
            import inspect

            positions_fn = self.kite.positions
            positions = await positions_fn() if inspect.iscoroutinefunction(positions_fn) else positions_fn()

            if not positions:
                return []

            # Kite returns positions in "net" key
            net_positions = positions.get("net", [])

            # Filter out closed positions (quantity = 0)
            active_positions = [
                p for p in net_positions
                if p.get("quantity", 0) != 0
            ]

            logger.info(
                "Fetched Kite positions",
                total=len(net_positions),
                active=len(active_positions),
            )

            return active_positions

        except Exception as e:
            logger.error("Failed to fetch Kite positions", error=str(e), exc_info=True)
            return []

    async def _fetch_system_positions(self) -> List[Dict]:
        """
        Fetch current positions from system database.

        Returns:
            List of position dictionaries with keys:
            - symbol
            - quantity
            - entry_price
            - unrealized_pnl
        """
        try:
            # For now, return empty list as we don't have proper DB session
            # This will be enhanced when position_store is properly integrated
            logger.info("System positions fetch not implemented yet")
            return []

        except Exception as e:
            logger.error("Failed to fetch system positions", error=str(e), exc_info=True)
            return []

    async def auto_sync_missing_positions(self, result: ReconciliationResult) -> int:
        """
        Automatically sync missing positions from Kite to system.

        This is useful when orders were placed directly in Kite app/web
        or when system crashed and missed recording positions.

        Returns:
            Number of positions synced
        """
        synced = 0

        for missing in result.missing_in_system:
            symbol = missing["symbol"]
            quantity = missing["kite_qty"]
            avg_price = missing["kite_avg_price"]

            try:
                # Create position in system database
                await self.db.create_position_from_external(
                    symbol=symbol,
                    quantity=quantity,
                    entry_price=avg_price,
                    source="KITE_RECONCILIATION",
                    timestamp=datetime.now(),
                )

                synced += 1
                logger.info(
                    "Auto-synced position from Kite",
                    symbol=symbol,
                    quantity=quantity,
                )

            except Exception as e:
                logger.error(
                    "Failed to auto-sync position",
                    symbol=symbol,
                    error=str(e),
                    exc_info=True,
                )

        if synced > 0:
            logger.info(f"Auto-synced {synced} positions from Kite")

        return synced

    async def auto_close_missing_positions(self, result: ReconciliationResult) -> int:
        """
        Automatically close positions in system that don't exist in Kite.

        This handles cases where positions were closed directly in Kite
        but system still thinks they're open.

        Returns:
            Number of positions closed
        """
        closed = 0

        for missing in result.missing_in_kite:
            symbol = missing["symbol"]

            try:
                # Mark position as closed in system
                await self.db.close_position_by_symbol(
                    symbol=symbol,
                    reason="KITE_RECONCILIATION",
                    timestamp=datetime.now(),
                )

                closed += 1
                logger.info(
                    "Auto-closed position missing in Kite",
                    symbol=symbol,
                )

            except Exception as e:
                logger.error(
                    "Failed to auto-close position",
                    symbol=symbol,
                    error=str(e),
                    exc_info=True,
                )

        if closed > 0:
            logger.info(f"Auto-closed {closed} positions missing in Kite")

        return closed

    async def reconcile_and_sync(self, auto_sync: bool = False) -> ReconciliationResult:
        """
        Perform reconciliation and optionally auto-sync discrepancies.

        Args:
            auto_sync: If True, automatically sync missing positions and close
                       positions that don't exist in Kite

        Returns:
            ReconciliationResult after sync
        """
        result = await self.reconcile()

        if auto_sync and not result.is_clean():
            logger.info("Auto-syncing discrepancies")

            # Sync missing positions from Kite
            if result.missing_in_system:
                await self.auto_sync_missing_positions(result)

            # Close positions missing in Kite
            if result.missing_in_kite:
                await self.auto_close_missing_positions(result)

            # Re-run reconciliation to verify
            result = await self.reconcile()

        return result
