"""Periodic reconciliation of orders with broker source of truth."""
import asyncio
import structlog
from typing import Optional

from packages.storage.database import get_db_session
from packages.storage.models import Order as DBOrder, OrderStatusEnum

logger = structlog.get_logger(__name__)


async def reconcile_orders(kite_client, interval_seconds: int = 60, stop: Optional[asyncio.Event] = None):
    """Background task to reconcile local DB order statuses with broker."""
    logger.info("Reconciliation loop started", interval_seconds=interval_seconds)
    async def _sleep_or_stop() -> bool:
        """Sleep for the interval; return True if stop event was set during wait."""
        if stop is None:
            await asyncio.sleep(interval_seconds)
            return False
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval_seconds)
            return True
        except asyncio.TimeoutError:
            return False

    while True:
        if stop and stop.is_set():
            logger.info("Reconciliation loop stopping on signal")
            break
        try:
            # Fetch remote orders
            if hasattr(kite_client, "orders"):
                orders_fn = kite_client.orders
                remote_orders = await orders_fn() if asyncio.iscoroutinefunction(orders_fn) else orders_fn()
            else:
                remote_orders = []
            
            if not remote_orders:
                should_stop = await _sleep_or_stop()
                if should_stop:
                    break
                continue
            
            with get_db_session() as db:
                for r in remote_orders:
                    oid = r.get("order_id")
                    if not oid:
                        continue
                    status = (r.get("status") or "").upper()
                    local: Optional[DBOrder] = db.query(DBOrder).filter_by(broker_order_id=oid).first()
                    if local and status and status != local.status.value:
                        logger.warning("Order status drift detected", order_id=oid, local=local.status.value, remote=status)
                        try:
                            local.status = OrderStatusEnum(status)
                        except Exception:
                            local.status = status  # fallback raw
                        db.add(local)
                        db.commit()
        except Exception as e:
            logger.warning("Reconciliation loop error", error=str(e))
        
        should_stop = await _sleep_or_stop()
        if should_stop:
            logger.info("Reconciliation loop stopped")
            break
