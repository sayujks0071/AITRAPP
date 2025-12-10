"""Main trading orchestrator - connects all components"""
import asyncio
import os
import time as time_module
from datetime import datetime, time, timedelta
from typing import Any, Callable, Dict, List, Optional

import structlog
from kiteconnect import KiteConnect

from packages.core.config import app_config, settings
from packages.core.execution import ExecutionEngine, OrderResult
from packages.core.exits import ExitManager, ExitReason, ExitSignal
from packages.core.exit_enhancements import EnhancedExitManager
from packages.core.position_adjuster import PositionAdjuster, AdjustmentConfig, AdjustmentStrategy
from packages.core.position_reconciliation import PositionReconciler
from packages.core.instruments import InstrumentManager
from packages.core.market_data import MarketDataStream
from packages.core.models import Position, PositionStatus, Signal, SignalSide, SystemState
from packages.core.config import AppMode
from packages.core.paper_simulator import PaperSimulator
from packages.core.ranker import SignalRanker, RankedOpportunity
from packages.core.risk import PortfolioRisk, RiskManager
from packages.core.strategies.base import Strategy
from packages.core.persistence import persist_signal, persist_decision, persist_order, get_config_sha
from packages.core.redis_bus import RedisBus
from packages.core.metrics import (
    record_signal, record_signal_ranked, record_decision_approved,
    record_decision_rejected, record_order_placed, record_scan_cycle_duration,
    record_signals_per_cycle, update_portfolio_heat, update_daily_pnl
)
from packages.core.oco import OCOManager
from packages.core.leader_lock import LeaderLock
from packages.storage.database import SessionLocal

logger = structlog.get_logger(__name__)


class TradingOrchestrator:
    """
    Main orchestrator that runs the complete trading pipeline:
    
    1. Market Data → WebSocket ticks → Bars → Indicators
    2. Strategies → Generate signals
    3. Ranker → Score and rank signals
    4. Risk Manager → Validate and size positions
    5. Execution Engine → Place orders
    6. Exit Manager → Monitor and close positions
    7. State Management → Track everything
    """
    
    def __init__(
        self,
        kite: KiteConnect,
        strategies: List[Strategy],
        instrument_manager: InstrumentManager,
        market_data_stream: MarketDataStream,
        risk_manager: RiskManager,
        execution_engine: ExecutionEngine,
        exit_manager: ExitManager,
        ranker: SignalRanker,
        position_store: Optional[Any] = None,
        redis_bus: Optional[RedisBus] = None,
        strategy_allocator: Optional[Any] = None,
        oco_manager: Optional[OCOManager] = None,
        crypto_router: Optional[Any] = None,
        delta_neutralizer: Optional[Any] = None,
        autonomous_capital_allocator: Optional[Any] = None,
        portfolio_manager: Optional[Any] = None,
        logic_heartbeat: Optional[Callable[[], None]] = None,
        notification_service: Optional[Any] = None
    ):
        self.kite = kite
        self.position_store = position_store
        self.strategies = strategies
        self.instrument_manager = instrument_manager
        self.market_data_stream = market_data_stream
        self.risk_manager = risk_manager
        self.execution_engine = execution_engine
        self.exit_manager = exit_manager
        self.ranker = ranker
        self.redis_bus = redis_bus
        self.strategy_allocator = strategy_allocator
        self.oco_manager = oco_manager
        self.crypto_router = crypto_router
        self.delta_neutralizer = delta_neutralizer
        self.autonomous_capital_allocator = autonomous_capital_allocator
        self.portfolio_manager = portfolio_manager
        self._logic_heartbeat = logic_heartbeat
        self.notification_service = notification_service
        self.leader_lock: Optional[LeaderLock] = None
        
        # State
        self.positions: List[Position] = []
        self.is_running = False
        self.is_paused = False
        self._mode = settings.app_mode.value
        
        # Paper simulator
        self.paper_sim = PaperSimulator(
            slippage_bps=app_config.risk.slippage_bps,
            fees_per_order=app_config.risk.fees_per_order
        )
        
        # Scan cycle timing
        from packages.core.metrics import scan_interval_seconds
        self.scan_interval_seconds = 5  # Scan every 5 seconds
        scan_interval_seconds.set(self.scan_interval_seconds)  # Expose in metrics
        self.last_scan_time: Optional[datetime] = None
        
        # Scan supervisor
        self._stop = asyncio.Event()
        self._scan_task: Optional[asyncio.Task] = None
        self._scan_ticks = 0  # Counter for periodic delta neutralizer checks
        
        # Configurable token limit per scan (Patch 1)
        self.max_tokens_per_scan = int(
            os.getenv("MAX_TOKENS_PER_SCAN", "80")  # Default 80 (was hardcoded 20)
        )
        logger.info(
            "Orchestrator token limit configured",
            max_tokens_per_scan=self.max_tokens_per_scan
        )
        
        # Performance tracking
        self.signals_generated_today = 0
        self.orders_placed_today = 0
        self.trades_completed_today = 0
        
        # NEW: Allocator refresh config (Patch: Periodic, Regime-Aware Allocator)
        allocator_cfg = getattr(strategy_allocator, "cfg", {}) if strategy_allocator else {}
        default_interval = 90  # seconds
        self.allocator_refresh_interval = int(
            allocator_cfg.get("refresh_interval_seconds", default_interval)
        )
        self._last_allocator_run_ts: Optional[float] = None
        
        logger.info(
            "Orchestrator allocator refresh configured",
            refresh_interval_seconds=self.allocator_refresh_interval,
            allocator_enabled=bool(strategy_allocator)
        )
        
        # NEW: Self-Healing integration
        self._self_healing_enabled = os.getenv("SELF_HEALING_ENABLED", "true").lower() == "true"
        self._self_diagnostics: Optional[Any] = None
        self._self_healing: Optional[Any] = None
        self._last_diagnostics_run: Optional[datetime] = None
        self._diagnostics_interval = 300  # 5 minutes
        self._blocking_anomalies: List[str] = []  # Anomalies that block trading
        
        if self._self_healing_enabled:
            try:
                from packages.core.self_healing import SelfDiagnostics, SelfHealing
                from packages.core.rag_memory import RAGMemory
                from pathlib import Path
                
                # Initialize diagnostics
                self._self_diagnostics = SelfDiagnostics()
                
                # Initialize healing (if config path available)
                config_path = Path(app_config.config_path) if hasattr(app_config, 'config_path') else Path("configs/kite_day1_live.yaml")
                if config_path.exists():
                    memory = RAGMemory()
                    self._self_healing = SelfHealing(
                        config_path=str(config_path),
                        memory=memory,
                        healing_enabled=True
                    )
                    logger.info("Self-healing system initialized", config_path=str(config_path))
                else:
                    logger.warning(f"Self-healing disabled: config file not found at {config_path}")
                    self._self_healing_enabled = False
            except Exception as e:
                logger.warning(f"Self-healing initialization failed: {e}", exc_info=True)
                self._self_healing_enabled = False

        # NEW: Position Adjuster for partial fills
        adjuster_config = AdjustmentConfig(
            default_strategy=AdjustmentStrategy.RETRY_FAILED,
            max_retry_attempts=3,
            retry_delay_seconds=1.0,
            allow_partial_positions=True,
            hedge_partial_fills=False,
            notify_on_partial=True
        )
        self.position_adjuster = PositionAdjuster(self.execution_engine, adjuster_config)
        logger.info("Position adjuster initialized", strategy="RETRY_FAILED", max_retries=3)

        # NEW: Enhanced Exit Manager (replaces standard exit manager for spreads)
        # If exit_manager is already EnhancedExitManager, keep it; otherwise wrap it
        if not isinstance(exit_manager, EnhancedExitManager):
            logger.info("Upgrading exit manager to EnhancedExitManager")
            self.enhanced_exit_manager = EnhancedExitManager(app_config.exits)
        else:
            self.enhanced_exit_manager = exit_manager

        # NEW: Position Reconciler for Kite API sync
        # Note: database will be set up in start() method
        self.position_reconciler: Optional[PositionReconciler] = None
        logger.info("Position reconciler will be initialized on start")

    async def start(self) -> None:
        """Start the trading orchestrator"""
        logger.info("Starting Trading Orchestrator", mode=settings.app_mode.value)
        
        # Acquire leader lock if Redis available
        from packages.core.metrics import is_leader
        if self.redis_bus and hasattr(self.redis_bus, 'redis') and self.redis_bus.redis:
            self.leader_lock = LeaderLock(self.redis_bus.redis)
            acquired = await self.leader_lock.acquire()
            if not acquired:
                if settings.app_mode.value == "PAPER":
                    # In paper mode, proceed without a hard leader lock to avoid local deadlocks
                    instance_id = "paper-local"
                    is_leader.labels(instance_id=instance_id).set(1)
                    logger.warning("Leader lock not acquired in PAPER mode - proceeding as leader for local testing")
                else:
                    logger.critical("Failed to acquire leader lock - another instance may be running")
                    raise RuntimeError("Cannot start: leader lock not acquired")
            else:
                # Set leader metric immediately
                instance_id = getattr(self.leader_lock, 'instance_id', 'default')
                is_leader.labels(instance_id=instance_id).set(1)
                logger.info("Leader lock acquired and metric set", instance_id=instance_id)
                
                # Start refresh task
                asyncio.create_task(self._refresh_leader_lock())
        
        # Re-arm OCO watchers for open positions (crash-safe recovery)
        await self._recover_open_positions()

        # NEW: Initialize position reconciler and run startup reconciliation
        if self.position_reconciler is None:
            try:
                self.position_reconciler = PositionReconciler(self.kite, db_session=None)
                logger.info("Position reconciler initialized")

                # Run startup reconciliation with auto-sync
                logger.info("Running position reconciliation on startup...")
                result = await self.position_reconciler.reconcile_and_sync(auto_sync=False)
                logger.info(result.summary())

                if not result.is_clean():
                    logger.warning(
                        "Position discrepancies found on startup",
                        discrepancies=result.total_discrepancies,
                        missing_in_system=len(result.missing_in_system)
                    )
                    # Log the missing positions for visibility
                    for pos in result.missing_in_system:
                        logger.info(
                            "Position in Kite not in system",
                            symbol=pos["symbol"],
                            quantity=pos["kite_qty"],
                            pnl=pos.get("kite_pnl", 0)
                        )
            except Exception as e:
                logger.error(f"Position reconciliation failed: {e}", exc_info=True)
                logger.warning("Continuing without position reconciliation")

        self.is_running = True
        self.is_paused = False

        # Run initial allocation cycle if allocator is available
        if self.strategy_allocator:
            try:
                # Get current regime from R1 if available (best effort)
                current_regime = None
                r1_strategy = next((s for s in self.strategies if s.name == "RegimeVolEngine"), None)
                if r1_strategy and hasattr(r1_strategy, 'last_classified_regime'):
                    current_regime = r1_strategy.last_classified_regime
                
                # Get event context - we'll need to pass event_engine to orchestrator or get it another way
                # For now, pass None and we can enhance later
                event_ctx = None
                
                allocations = self.strategy_allocator.run_allocation_cycle(
                    current_regime=current_regime,
                    event_ctx=event_ctx
                )
                logger.info("Initial allocation cycle completed", num_allocations=len(allocations))
            except Exception as e:
                logger.warning("Allocation cycle failed at startup", error=str(e))
        
        # Initialize crypto venue if in crypto mode
        if settings.app_mode.value in ("CRYPTO_PAPER", "CRYPTO_LIVE") and self.crypto_router:
            try:
                await self.crypto_router.connect_ws()
                venue_config = app_config.venue if hasattr(app_config, "venue") else {}
                allowed_symbols = venue_config.get("allowed_symbols", [])
                for symbol in allowed_symbols:
                    await self.crypto_router.subscribe_symbol(symbol)
                logger.info(f"Subscribed to {len(allowed_symbols)} crypto symbols")
            except Exception as e:
                logger.warning("Crypto WebSocket connection failed (continuing in paper mode)", error=str(e))
                # In paper mode, we can continue without WebSocket
                if settings.app_mode.value == "CRYPTO_PAPER":
                    logger.info("Continuing in CRYPTO_PAPER mode without WebSocket")
                else:
                    raise
        
        # Start periodic diagnostics task (every 5 minutes)
        if self._self_healing_enabled:
            asyncio.create_task(self._periodic_diagnostics())
            logger.info("Periodic diagnostics task started", interval_seconds=self._diagnostics_interval)
        
        # Start market data stream for equity mode
        if settings.app_mode.value not in ("CRYPTO_PAPER", "CRYPTO_LIVE"):
            if not self.market_data_stream.is_connected:
                self.market_data_stream.start()
                await asyncio.sleep(2)  # Wait for connection
            
            # Subscribe to universe
            universe_tokens = self.instrument_manager.get_universe_tokens()
            if universe_tokens:
                self.market_data_stream.subscribe(universe_tokens[:50])  # Limit for demo
                logger.info(f"Subscribed to {len(universe_tokens[:50])} instruments")
        
        # Start scan supervisor (never silently dies)
        from packages.core.metrics import scan_supervisor_state
        if self._scan_task and not self._scan_task.done():
            scan_supervisor_state.set(1)  # running
            logger.info("Scan supervisor already running")
        else:
            self._stop.clear()
            scan_supervisor_state.set(1)  # running
            self._scan_task = asyncio.create_task(self._scan_supervisor(), name="scan-supervisor")
            logger.info("Scan supervisor scheduled", interval=self.scan_interval_seconds)
    
    async def stop(self) -> None:
        """Stop the trading orchestrator"""
        logger.info("Stopping Trading Orchestrator")
        
        self.is_running = False
        self.is_paused = True
        
        # Stop scan supervisor
        from packages.core.metrics import scan_supervisor_state
        if self._scan_task:
            scan_supervisor_state.set(4)  # stopping
            self._stop.set()
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass
            scan_supervisor_state.set(0)  # stopped
            logger.info("Scan supervisor stopped")
        
        # Release leader lock
        if self.leader_lock:
            await self.leader_lock.release()
        
        # Stop market data stream
        if self.market_data_stream:
            self.market_data_stream.stop()
        
        # Close all positions if in live mode
        if settings.app_mode.value == "LIVE" and self.positions:
            logger.warning("Closing all positions before shutdown")
            await self._close_all_positions("SHUTDOWN")
    
    async def _refresh_leader_lock(self) -> None:
        """
        Periodically refresh the lock. If lost:
          • set metrics
          • pause trading
          • try auto-reacquire with exponential backoff (jitter)
          • resume trading when lock is re-acquired
        """
        import random
        from packages.core.metrics import is_leader, kill_switch_total
        
        backoff = [1, 2, 4, 8, 15, 30]  # seconds; cap at 30s
        ttl_fraction = 10  # refresh cadence (10 seconds)
        
        while self.is_running:
            try:
                if not self.leader_lock:
                    await asyncio.sleep(ttl_fraction)
                    continue
                
                ok = await self.leader_lock.refresh()
                instance_id = getattr(self.leader_lock, 'instance_id', 'default')
                
                if ok:
                    is_leader.labels(instance_id=instance_id).set(1)
                    await asyncio.sleep(ttl_fraction)
                    continue
                
                # LOST leadership
                is_leader.labels(instance_id=instance_id).set(0)
                logger.warning("Leader lock lost — pausing orchestrator")
                await self.pause()
                
                # Optional: count the event for alerting
                kill_switch_total.labels(reason="leader_lock_lost").inc()
                
                # Log audit event
                from packages.storage.database import get_db_session
                from packages.storage.models import AuditLog, AuditActionEnum
                try:
                    with get_db_session() as db:
                        audit_log = AuditLog(
                            action=AuditActionEnum.LEADER_LOCK,
                            message="Leader lock lost - orchestrator paused",
                            details={
                                "event": "LEADER_LOCK_LOST",
                                "instance_id": instance_id,
                                "config_sha": get_config_sha()
                            }
                        )
                        db.add(audit_log)
                        db.commit()
                except Exception as e:
                    logger.warning("Failed to log leader lock loss", error=str(e))
                
                # Try to reacquire with backoff+jitter
                reacquired = False
                for delay in backoff:
                    if not self.is_running:
                        return
                    await asyncio.sleep(delay + random.uniform(0, 0.5))
                    try:
                        if await self.leader_lock.acquire():
                            is_leader.labels(instance_id=instance_id).set(1)
                            logger.info("Leader lock re-acquired — resuming orchestrator")
                            
                            # Track leader change
                            from packages.core.metrics import leader_changes_total
                            leader_changes_total.inc()
                            
                            # Resume orchestrator
                            self.is_paused = False
                            logger.info("Orchestrator resumed after leader lock re-acquisition")
                            
                            # Log audit event
                            from packages.storage.database import get_db_session
                            from packages.storage.models import AuditLog, AuditActionEnum
                            try:
                                with get_db_session() as db:
                                    audit_log = AuditLog(
                                        action=AuditActionEnum.LEADER_LOCK,
                                        message="Leader lock re-acquired - orchestrator resumed",
                                        details={
                                            "event": "LEADER_LOCK_ACQUIRED",
                                            "instance_id": instance_id,
                                            "config_sha": get_config_sha()
                                        }
                                    )
                                    db.add(audit_log)
                                    db.commit()
                            except Exception as e:
                                logger.warning("Failed to log leader lock re-acquisition", error=str(e))
                            
                            reacquired = True
                            break
                    except Exception as e:
                        logger.exception("Leader re-acquire attempt failed", error=str(e))
                
                if not reacquired:
                    # Don't kill the process; just wait and try again on next loop
                    logger.error("Unable to re-acquire leader lock after retries; staying paused")
                    await asyncio.sleep(backoff[-1])
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.exception("Unexpected error in leader lock refresh loop", error=str(e))
                await asyncio.sleep(1)
    
    async def _recover_open_positions(self) -> None:
        """Recover open positions and re-arm OCO watchers (crash-safe)"""
        from packages.storage.models import Position as DBPosition, PositionStatusEnum, Order, OrderStatusEnum
        from packages.storage.database import get_db_session
        
        with get_db_session() as db:
            open_positions = db.query(DBPosition).filter_by(
                status=PositionStatusEnum.OPEN
            ).all()
            
            if not open_positions:
                return
            
            logger.info(f"Recovering {len(open_positions)} open positions")
            
            for pos in open_positions:
                if not pos.oco_group:
                    continue
                
                # Find PLACED children orders
                children = db.query(Order).filter_by(
                    parent_group=pos.oco_group,
                    status=OrderStatusEnum.PLACED
                ).all()
                
                if children:
                    logger.info(
                        "Re-arming OCO watcher for position",
                        position_id=pos.position_id,
                        oco_group=pos.oco_group,
                        children_count=len(children)
                    )
                    # OrderWatcher will pick these up automatically
                    # This ensures sibling cancel logic is armed after restart
    
    async def pause(self) -> None:
        """Pause trading (stop new entries, keep positions)"""
        logger.warning("🛑 Trading PAUSED")
        self.is_paused = True
    
    async def resume(self) -> None:
        """Resume trading"""
        logger.info("▶️  Trading RESUMED")
        self.is_paused = False
    
    def set_mode(self, mode: str) -> None:
        """Set trading mode (PAPER/LIVE)"""
        self._mode = mode
        logger.info(f"Mode set to {mode}")
    
    async def on_entry_filled(self, fill_event: dict) -> None:
        """Called by OrderWatcher when an ENTRY order is filled"""
        client_order_id = fill_event.get("client_order_id")
        if not client_order_id:
            return
        
        logger.info("Entry order filled", client_order_id=client_order_id)
        
        # Update order status in DB
        from packages.core.persistence import update_order_status
        from packages.storage.models import OrderStatusEnum, OrderSideEnum, SideEnum
        order_model = update_order_status(
            client_order_id=client_order_id,
            broker_order_id=fill_event.get("broker_order_id"),
            status=OrderStatusEnum.FILLED,
            filled_qty=fill_event.get("filled_qty"),
            average_price=fill_event.get("average_price")
        )
        
        if not order_model or not order_model.decision_id:
            return
        
        # Get decision to find signal
        from packages.storage.database import get_db_session
        from sqlalchemy.orm import selectinload
        from packages.storage.models import Decision, Position as DBPosition, PositionStatusEnum
        with get_db_session() as db:
            decision = db.query(Decision).options(selectinload(Decision.signal)).filter_by(id=order_model.decision_id).first()
            if not decision or not decision.signal:
                return
            
            # Create position in DB
            position = DBPosition(
                position_id=f"POS_{order_model.id}",
                symbol=order_model.symbol,
                instrument_token=order_model.instrument_token,
                side=SideEnum.LONG if order_model.side == OrderSideEnum.BUY else SideEnum.SHORT,
                qty=order_model.filled_qty or order_model.qty,
                avg_price=order_model.average_price or order_model.price or 0.0,
                current_price=order_model.average_price or order_model.price or 0.0,
                stop_loss=decision.signal.stop_loss,
                take_profit_1=decision.signal.take_profit_1,
                take_profit_2=decision.signal.take_profit_2,
                risk_amount=decision.risk_amount,
                oco_group=None,  # Will be set by OCO manager
                strategy_name=order_model.strategy_name,
                entry_order_id=client_order_id,
                status=PositionStatusEnum.OPEN
            )
            db.add(position)
            db.commit()
            db.refresh(position)
            
            # Place stop/TP via OCO manager
            if self.oco_manager and decision.signal.stop_loss:
                oco_group_id = self.oco_manager.create_oco_group(
                    entry_order=order_model,
                    stop_price=decision.signal.stop_loss,
                    tp1_price=decision.signal.take_profit_1,
                    tp2_price=decision.signal.take_profit_2,
                    instrument_token=order_model.instrument_token,
                    qty=order_model.filled_qty or order_model.qty
                )
                position.oco_group = oco_group_id
                db.commit()
                
                # Publish OCO children created
                if self.redis_bus:
                    asyncio.create_task(self.redis_bus.publish_order({
                        "event": "OCO_CHILDREN",
                        "group": oco_group_id,
                        "position_id": position.position_id
                    }))
    
    async def on_child_filled(self, child_event: dict) -> None:
        """Called by OrderWatcher when a STOP or TP order is filled"""
        client_order_id = child_event.get("client_order_id")
        parent_group = child_event.get("parent_group")
        
        logger.info("Child order filled", client_order_id=client_order_id, group=parent_group)
        
        # Cancel siblings via OCO manager
        if self.oco_manager and parent_group:
            from packages.storage.models import Order
            order_model = None
            with get_db_session() as db:
                order_model = db.query(Order).filter_by(client_order_id=client_order_id).first()
            if order_model:
                await self.oco_manager.on_child_fill(parent_group, order_model)
        
        # Update position and create trade
        from packages.storage.database import get_db_session
        from packages.storage.models import Position as DBPosition, Trade, TradeActionEnum, PositionStatusEnum
        from packages.core.persistence import update_order_status
        from packages.storage.models import OrderStatusEnum
        
        update_order_status(
            client_order_id=client_order_id,
            status=OrderStatusEnum.FILLED,
            filled_qty=child_event.get("filled_qty"),
            average_price=child_event.get("average_price")
        )
        
        with get_db_session() as db:
            position = db.query(DBPosition).filter_by(oco_group=parent_group).first()
            if position:
                tag = child_event.get("tag", "")
                if tag == "STOP":
                    position.status = PositionStatusEnum.CLOSED
                    position.exit_reason = "STOP_LOSS"
                elif tag in ["TP1", "TP2"]:
                    if tag == "TP1":
                        position.qty -= child_event.get("filled_qty", 0)
                        position.exit_reason = "TP1_PARTIAL"
                    else:
                        position.status = PositionStatusEnum.CLOSED
                        position.exit_reason = "TP2_FULL"
                
                # Create trade record
                trade = Trade(
                    position_id=position.id,
                    action=TradeActionEnum.PARTIAL_EXIT if tag == "TP1" else TradeActionEnum.FULL_EXIT,
                    qty=child_event.get("filled_qty", 0),
                    price=child_event.get("average_price", 0.0),
                    fees=0.0,
                    risk_amount=position.risk_amount
                )
                db.add(trade)
                db.commit()
        
        # Publish OCO close
        if self.redis_bus:
            asyncio.create_task(self.redis_bus.publish_order({
                "event": "OCO_CLOSE",
                "group": parent_group,
                "client_order_id": client_order_id
            }))
    
    async def flatten_all(self, reason: str = "manual") -> None:
        """Kill switch - close all positions immediately"""
        from packages.core.metrics import kill_switch_total
        from packages.storage.models import AuditLog, AuditActionEnum
        from packages.core.alerts import alert_manager
        
        logger.critical("🚨 KILL SWITCH ACTIVATED - FLATTENING ALL POSITIONS", reason=reason)
        
        # Calculate open risk before flattening
        from packages.core.models import PositionStatus
        open_risk = sum(
            getattr(p, 'risk_amount', 0) 
            for p in self.positions 
            if getattr(p, 'status', None) == PositionStatus.OPEN
        ) if self.positions else 0.0
        
        positions_count = len([p for p in self.positions if getattr(p, 'status', None) == PositionStatus.OPEN]) if self.positions else 0
        
        # Record metric
        kill_switch_total.labels(reason=reason).inc()

        # Send alert (Telegram/Slack) without blocking control flow
        if self.notification_service and getattr(self.notification_service, "is_configured", lambda: False)():
            msg = (
                f"Kill switch activated ({reason}) | "
                f"open risk rupees: {open_risk:.2f} | positions: {positions_count}"
            )
            try:
                loop = asyncio.get_running_loop()
                loop.run_in_executor(None, self.notification_service.send, msg, "CRITICAL")
            except Exception as notify_err:
                logger.warning("Kill switch notification failed", error=str(notify_err))
        
        # Send alert
        alert_manager.alert_kill_switch(
            reason=reason,
            details={
                "open_risk_rupees": open_risk,
                "positions_count": positions_count
            }
        )
        
        # Audit log (backward-compatible: handles both details and data columns)
        from packages.storage.database import get_db_session
        from sqlalchemy import inspect
        
        with get_db_session() as db:
            # Check if details column exists
            try:
                columns = inspect(db.bind).get_columns("audit_logs")
                has_details = any(
                    c.get("name") == "details" or getattr(c, "name", None) == "details"
                    for c in columns
                )
            except Exception:
                # Fallback: assume details exists if we can't check
                has_details = True
            
            # Prepare action value (handle both Enum and string)
            action_value = AuditActionEnum.KILL_SWITCH
            # AuditActionEnum values are already strings, so use directly
            if isinstance(action_value, str):
                pass  # Already a string
            elif hasattr(action_value, 'value'):
                action_value = action_value.value
            else:
                action_value = str(action_value)
            
            # Create audit log with backward compatibility
            if has_details:
                audit_log = AuditLog(
                    action=action_value,
                    message=f"Kill switch activated: {reason}",
                    details={
                        "reason": reason,
                        "open_risk_rupees": open_risk,
                        "positions_count": positions_count
                    }
                )
            else:
                # Fallback to data column if details doesn't exist
                audit_log = AuditLog(
                    action=str(action_value),
                    message=f"Kill switch activated: {reason}",
                    data={
                        "reason": reason,
                        "open_risk_rupees": open_risk,
                        "positions_count": positions_count
                    }
                )
            db.add(audit_log)
            db.commit()
        
        self.is_paused = True
        
        await self._close_all_positions("KILL_SWITCH")
        
        logger.info("All positions flattened", reason=reason, open_risk_rupees=open_risk)
    
    async def _scan_supervisor(self) -> None:
        """Scan supervisor - never silently dies, always calls touch_scan()"""
        import time
        from packages.core.heartbeats import touch_scan
        from packages.core.metrics import scan_ticks_total, scan_supervisor_state
        
        logger.info("Main trading loop started (scan supervisor)", interval=self.scan_interval_seconds)
        
        try:
            while not self._stop.is_set():
                t0 = time.perf_counter()
                try:
                    # Always mark a "tick" even if we early-return (market closed / paused)
                    try:
                        await self._scan_cycle()
                    finally:
                        scan_ticks_total.inc()  # Increment tick counter
                        touch_scan()
                        if self._logic_heartbeat:
                            try:
                                self._logic_heartbeat()
                            except Exception:
                                logger.warning("Sidecar heartbeat update failed", exc_info=True)
                except asyncio.CancelledError:
                    scan_supervisor_state.set(4)  # stopping
                    raise
                except Exception as e:
                    logger.exception("Scan cycle crashed; will retry in 1s", error=str(e))
                    await asyncio.sleep(1.0)
                    continue
                
                # Bounded sleep so config mistakes don't stall the loop
                dt = max(0.25, float(self.scan_interval_seconds))
                elapsed = time.perf_counter() - t0
                sleep_time = max(0.0, dt - elapsed)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
        except asyncio.CancelledError:
            scan_supervisor_state.set(4)  # stopping
            raise
        except Exception as e:
            scan_supervisor_state.set(3)  # exception
            logger.exception("Scan supervisor crashed; will restart", error=str(e))
            await asyncio.sleep(1.0)
            # Restart supervisor
            if self.is_running:
                self._stop.clear()
                scan_supervisor_state.set(1)  # running
                self._scan_task = asyncio.create_task(self._scan_supervisor(), name="scan-supervisor")
                logger.info("Scan supervisor restarted after exception")
        else:
            scan_supervisor_state.set(2)  # done
        
        logger.info("Main trading loop exiting (scan supervisor)")
    
    def _sorted_strategies(self) -> List[Strategy]:
        """
        Returns strategies sorted by priority (lower number = higher priority).
        
        If a strategy doesn't define .priority, default = 100.
        This ensures premium strategies (OptionsRanker, IntradayStrangle, etc.) run first.
        """
        return sorted(
            self.strategies,
            key=lambda s: getattr(s, "priority", 100),
        )
    
    async def _run_strategy_on_tokens(
        self,
        strategy: Strategy,
        tokens: List[int],
        current_time: datetime,
        regime_snapshot: Optional[Dict[str, Any]],
        event_snapshot: Optional[Dict[str, Any]],
        all_signals: List[Signal]
    ) -> None:
        """
        Run a strategy on a list of tokens, building StrategyContext with regime/event data.
        
        Enhanced with bulk LTP fetching and async execute() support.
        
        This is the core loop that:
        1. Bulk fetches LTP for all tokens (efficiency)
        2. Iterates through tokens
        3. Builds StrategyContext with market data + regime/event snapshots
        4. Calls strategy.execute() (async) or generate_signals() (sync)
        5. Collects signals
        """
        # Bulk fetch LTP for all tokens (efficiency improvement)
        ltp_map = await self._bulk_fetch_ltp(tokens)
        
        # Build shared context data (once per strategy, not per token)
        net_liquid = self._get_net_liquid()
        available_margin = self._get_available_margin()
        open_positions_list = [p for p in self.positions if p.is_open]
        
        # Extract simplified regime string from snapshot
        regime_string = None
        if regime_snapshot:
            # Try to extract regime for first available symbol
            for symbol, data in regime_snapshot.items():
                if isinstance(data, dict) and "regime" in data:
                    regime_string = data["regime"]
                    break
        
        # Build margins dict (shared across all tokens)
        margins_dict = {
            "net_liquid": net_liquid,
            "available_margin": available_margin,
            "used_margin": net_liquid - available_margin,
            "margin_usage_pct": ((net_liquid - available_margin) / net_liquid * 100) if net_liquid > 0 else 0.0
        }
        
        # Import StrategyContext (needed for both paths)
        from packages.core.strategies.base import StrategyContext, Strategy
        
        # Check if strategy has overridden execute() (not just the base class default)
        # The base class has a default execute() that calls generate_signals(),
        # which expects context.instrument to exist. We only want to use bulk context
        # for strategies that have actually overridden execute() to handle bulk contexts.
        base_execute = Strategy.execute
        strategy_execute = getattr(strategy.__class__, 'execute', None)
        has_overridden_execute = (
            strategy_execute is not None 
            and strategy_execute is not base_execute
            and callable(strategy_execute)
        )
        
        if has_overridden_execute:
            # New strategy: Use async execute() with bulk context
            try:
                # Build multi-instrument context (StatGeist-style)
                bulk_context = StrategyContext(
                    timestamp=current_time,
                    instrument=None,  # Multi-instrument context
                    # Legacy fields (minimal for bulk context)
                    latest_tick=None,
                    bars_1s=[],
                    bars_5s=[],
                    net_liquid=net_liquid,
                    available_margin=available_margin,
                    open_positions=len(open_positions_list),
                    # New fields (StatGeist-style) - bulk data
                    ltp=ltp_map,  # Bulk LTP map
                    ohlc={},  # Can be bulk-fetched if needed
                    positions=open_positions_list,
                    margins=margins_dict,
                    # Patch 3: Regime and event snapshots
                    regime_snapshot=regime_snapshot,
                    regime=regime_string,
                    event_snapshot=event_snapshot,
                    universe_size=len(tokens),
                    token_count=len(tokens)
                )
                
                # Call async execute()
                signals = await strategy.execute(bulk_context)
                if signals:
                    all_signals.extend(signals)
            except Exception as e:
                logger.error(
                    f"Error in async execute() for strategy {strategy.name}: {e}",
                    exc_info=True
                )
        else:
            # Legacy strategy: Per-instrument generate_signals() (backward compatible)
            for token in tokens:
                instrument = self.instrument_manager.get_instrument(token)
                if not instrument:
                    continue
                
                # Get market data
                tick = self.market_data_stream.get_latest_tick(token)
                bars_1s = self.market_data_stream.get_bars(token, 1, n=60)
                bars_5s = self.market_data_stream.get_bars(token, 5, n=100)
                
                if not tick or not bars_5s:
                    continue
                
                # Build per-instrument context (legacy format)
                # StrategyContext already imported above
                
                # Extract regime for this instrument's underlying
                instrument_regime = regime_string
                if regime_snapshot and instrument.symbol in regime_snapshot:
                    regime_data = regime_snapshot[instrument.symbol]
                    if isinstance(regime_data, dict) and "regime" in regime_data:
                        instrument_regime = regime_data["regime"]
                
                # Build LTP dict (add current instrument to bulk map)
                ltp_dict = ltp_map.copy()
                if tick:
                    ltp_dict[instrument.tradingsymbol] = tick.last_price
                    ltp_dict[instrument.symbol] = tick.last_price
                
                # Build OHLC dict (add current instrument)
                ohlc_dict = {}
                if bars_5s and len(bars_5s) > 0:
                    latest_bar = bars_5s[-1]
                    ohlc_dict[instrument.tradingsymbol] = {
                        "open": latest_bar.open,
                        "high": latest_bar.high,
                        "low": latest_bar.low,
                        "close": latest_bar.close,
                        "volume": latest_bar.volume,
                        "timestamp": latest_bar.timestamp
                    }
                
                context = StrategyContext(
                    # Legacy fields (backward compatible)
                    timestamp=current_time,
                    instrument=instrument,
                    latest_tick=tick,
                    bars_1s=bars_1s,
                    bars_5s=bars_5s,
                    net_liquid=net_liquid,
                    available_margin=available_margin,
                    open_positions=len(open_positions_list),
                    # New fields (StatGeist-style)
                    ltp=ltp_dict,
                    ohlc=ohlc_dict,
                    positions=open_positions_list,
                    margins=margins_dict,
                    # Patch 3: Regime and event snapshots
                    regime_snapshot=regime_snapshot,
                    regime=instrument_regime,
                    event_snapshot=event_snapshot,
                    universe_size=len(tokens),
                    token_count=len(tokens)
                )
                
                # Generate signals (sync, per-instrument)
                try:
                    signals = strategy.generate_signals(context)
                    all_signals.extend(signals)
                except Exception as e:
                    logger.error(
                        f"Error in generate_signals() for strategy {strategy.name} on {instrument.tradingsymbol}: {e}",
                        exc_info=True
                    )
    
    async def _bulk_fetch_ltp(self, tokens: List[int]) -> Dict[str, float]:
        """
        Bulk fetch LTP for all tokens (efficiency improvement).
        
        Returns dict mapping tradingsymbol -> last_price.
        Falls back to market_data_stream if Kite API not available.
        """
        ltp_map = {}
        
        try:
            # Try to use Kite API for bulk LTP (if available)
            if self.kite and hasattr(self.kite, 'ltp'):
                # Build instrument keys for bulk fetch
                instrument_keys = []
                symbol_map = {}  # Map instrument_key -> tradingsymbol
                
                for token in tokens:
                    instrument = self.instrument_manager.get_instrument(token)
                    if not instrument:
                        continue
                    
                    # Build Kite instrument key (e.g., "NFO:NIFTY24NOV24000CE")
                    exchange = instrument.exchange
                    tradingsymbol = instrument.tradingsymbol
                    instrument_key = f"{exchange}:{tradingsymbol}"
                    
                    instrument_keys.append(instrument_key)
                    symbol_map[instrument_key] = tradingsymbol
                    symbol_map[instrument_key] = instrument.symbol  # Also map by symbol
                
                if instrument_keys:
                    try:
                        # Bulk fetch LTP from Kite
                        bulk_ltp = self.kite.ltp(instrument_keys)
                        
                        # Convert to our format
                        for key, price_data in bulk_ltp.items():
                            if isinstance(price_data, dict):
                                price = price_data.get("last_price", 0.0)
                            else:
                                price = float(price_data) if price_data else 0.0
                            
                            # Map to both tradingsymbol and symbol
                            if key in symbol_map:
                                tradingsymbol = symbol_map[key]
                                ltp_map[tradingsymbol] = price
                                # Also add by symbol (find instrument by tradingsymbol)
                                for token, inst in self.instrument_manager._instruments.items():
                                    if inst.tradingsymbol == tradingsymbol:
                                        ltp_map[inst.symbol] = price
                                        break
                    except Exception as e:
                        logger.debug(f"Bulk LTP fetch failed, falling back to market data stream: {e}")
            
            # Fallback: Use market_data_stream (per-token)
            if not ltp_map:
                for token in tokens:
                    instrument = self.instrument_manager.get_instrument(token)
                    if not instrument:
                        continue
                    
                    tick = self.market_data_stream.get_latest_tick(token)
                    if tick:
                        ltp_map[instrument.tradingsymbol] = tick.last_price
                        ltp_map[instrument.symbol] = tick.last_price
        
        except Exception as e:
            logger.warning(f"Error in bulk LTP fetch: {e}, using market data stream fallback")
            # Fallback to per-token fetching
            for token in tokens:
                instrument = self.instrument_manager.get_instrument(token)
                if instrument:
                    tick = self.market_data_stream.get_latest_tick(token)
                    if tick:
                        ltp_map[instrument.tradingsymbol] = tick.last_price
                        ltp_map[instrument.symbol] = tick.last_price
        
        return ltp_map
    
    async def _maybe_run_allocator(
        self,
        regime_snapshot: Optional[Dict[str, Any]],
        event_snapshot: Optional[Dict[str, Any]]
    ) -> None:
        """
        Periodically recompute strategy caps based on realized PnL + regime/event.
        
        Runs at most once every allocator_refresh_interval seconds.
        This makes the allocator a "living organism" that adapts to:
        - Realized PnL changes
        - Regime shifts (R1)
        - Event changes (E1)
        
        Level 9 (ACA) takes precedence if enabled, otherwise falls back to StrategyAllocator.
        
        Args:
            regime_snapshot: Current regime snapshot from R1 (e.g., {"NIFTY": {"regime": "LOW_MEAN_REVERT", ...}})
            event_snapshot: Current event snapshot from E1 (e.g., {"today": {"is_event_day": False, ...}})
        """
        # Priority: Level 12 (PME) > Level 9 (ACA) > StrategyAllocator
        if self.portfolio_manager:
            await self._run_pme_allocation(regime_snapshot, event_snapshot)
            return
        
        if self.autonomous_capital_allocator:
            await self._run_aca_allocation(regime_snapshot, event_snapshot)
            return
        
        if not self.strategy_allocator:
            return
        
        now_ts = time_module.time()
        
        # Check if we should run (throttle by interval)
        if self._last_allocator_run_ts is None:
            should_run = True
        else:
            elapsed = now_ts - self._last_allocator_run_ts
            should_run = elapsed >= self.allocator_refresh_interval
        
        if not should_run:
            return
        
        self._last_allocator_run_ts = now_ts
        
        try:
            # Extract current regime from snapshot
            current_regime = None
            if regime_snapshot:
                # Try to extract regime for NIFTY (primary underlying)
                if "NIFTY" in regime_snapshot:
                    regime_data = regime_snapshot["NIFTY"]
                    if isinstance(regime_data, dict) and "regime" in regime_data:
                        current_regime = regime_data["regime"]
                # Fallback: try first available regime
                elif regime_snapshot:
                    for symbol, data in regime_snapshot.items():
                        if isinstance(data, dict) and "regime" in data:
                            current_regime = data["regime"]
                            break
            
            # Extract event context from snapshot
            event_ctx = event_snapshot
            
            # Run allocation cycle
            allocations = self.strategy_allocator.run_allocation_cycle(
                current_regime=current_regime,
                event_ctx=event_ctx,
            )
            
            # Apply new caps into risk engine
            if allocations and self.risk_manager:
                for name, alloc in allocations.items():
                    if not isinstance(alloc, dict):
                        # If alloc is StrategyAlloc dataclass, convert to dict
                        if hasattr(alloc, 'name') and hasattr(alloc, 'max_capital_pct'):
                            strategy_name = alloc.name
                            cap_pct = alloc.max_capital_pct
                        else:
                            continue
                    else:
                        strategy_name = alloc.get("name") or name
                        cap_pct = alloc.get("max_capital_pct") or alloc.get("capital_pct")
                    
                    if strategy_name and cap_pct is not None:
                        # Update risk engine caps
                        if hasattr(self.risk_manager, 'set_strategy_cap'):
                            self.risk_manager.set_strategy_cap(
                                strategy_name=strategy_name,
                                max_capital_pct=float(cap_pct),
                            )
                        elif hasattr(self.risk_manager, 'update_strategy_allocation'):
                            # Alternative method name
                            self.risk_manager.update_strategy_allocation(
                                strategy_name=strategy_name,
                                max_capital_pct=float(cap_pct),
                            )
            
            logger.info(
                "StrategyAllocator refresh completed",
                num_allocations=len(allocations),
                regime=current_regime,
                refresh_interval=self.allocator_refresh_interval
            )
        except Exception as e:
            logger.error(
                f"StrategyAllocator refresh failed: {e}",
                exc_info=True
            )
    
    async def _run_aca_allocation(
        self,
        regime_snapshot: Optional[Dict[str, Any]],
        event_snapshot: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Run Level 9 Autonomous Capital Allocator (ACA).
        
        Args:
            regime_snapshot: Current regime snapshot from R1
            event_snapshot: Current event snapshot from E1
        """
        if not self.autonomous_capital_allocator or not self.risk_manager:
            return
        
        try:
            # Extract current regime
            current_regime = None
            if regime_snapshot:
                if "NIFTY" in regime_snapshot:
                    regime_data = regime_snapshot["NIFTY"]
                    if isinstance(regime_data, dict) and "regime" in regime_data:
                        current_regime = regime_data["regime"]
                elif regime_snapshot:
                    for symbol, data in regime_snapshot.items():
                        if isinstance(data, dict) and "regime" in data:
                            current_regime = data["regime"]
                            break
            
            if not current_regime:
                logger.warning("⚠️  ACA: No regime detected, skipping allocation")
                return
            
            # Extract event context
            event_ctx = None
            if event_snapshot:
                # Try to extract event day flag from snapshot
                if isinstance(event_snapshot, dict):
                    if "today" in event_snapshot:
                        today_data = event_snapshot["today"]
                        if isinstance(today_data, dict):
                            event_ctx = {"is_event_day": today_data.get("is_event_day", False)}
                    elif "is_event_day" in event_snapshot:
                        event_ctx = {"is_event_day": event_snapshot["is_event_day"]}
            
            # Run ACA allocation cycle
            allocations = self.autonomous_capital_allocator.run_allocation_cycle(
                current_regime=current_regime,
                event_ctx=event_ctx
            )
            
            # Apply allocations to risk manager
            for alloc in allocations:
                strategy_name = alloc.get("strategy_name")
                cap_pct = alloc.get("capital_pct")
                
                if strategy_name and cap_pct is not None and cap_pct > 0:
                    self.risk_manager.set_strategy_cap(
                        strategy_name=strategy_name,
                        max_capital_pct=cap_pct
                    )
            
            logger.info(
                "✅ ACA: Allocation cycle completed",
                regime=current_regime,
                num_allocations=len(allocations),
                event_ctx=event_ctx
            )
        except Exception as e:
            logger.error(
                f"❌ ACA: Allocation cycle failed: {e}",
                exc_info=True
            )
    
    async def _run_pme_allocation(
        self,
        regime_snapshot: Optional[Dict[str, Any]],
        event_snapshot: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Run Level 12 Portfolio Management Engine (PME).
        
        Args:
            regime_snapshot: Current regime snapshot from R1
            event_snapshot: Current event snapshot from E1
        """
        if not self.portfolio_manager or not self.risk_manager:
            return
        
        try:
            # Extract current regime
            current_regime = None
            if regime_snapshot:
                if "NIFTY" in regime_snapshot:
                    regime_data = regime_snapshot["NIFTY"]
                    if isinstance(regime_data, dict) and "regime" in regime_data:
                        current_regime = regime_data["regime"]
                elif regime_snapshot:
                    for symbol, data in regime_snapshot.items():
                        if isinstance(data, dict) and "regime" in data:
                            current_regime = data["regime"]
                            break
            
            if not current_regime:
                logger.warning("⚠️  PME: No regime detected, skipping allocation")
                return
            
            # Get NAV (Net Asset Value) from risk manager
            portfolio_risk = self._get_portfolio_risk()
            nav = portfolio_risk.net_liquid
            
            if nav <= 0:
                logger.warning("⚠️  PME: Invalid NAV, skipping allocation")
                return
            
            # Extract event context
            event_ctx = None
            if event_snapshot:
                if isinstance(event_snapshot, dict):
                    if "today" in event_snapshot:
                        today_data = event_snapshot["today"]
                        if isinstance(today_data, dict):
                            event_ctx = {"is_event_day": today_data.get("is_event_day", False)}
                    elif "is_event_day" in event_snapshot:
                        event_ctx = {"is_event_day": event_snapshot["is_event_day"]}
            
            # Get daily returns history for volatility targeting
            # Calculate from portfolio risk (daily PnL / NAV)
            daily_returns_history = []
            if hasattr(portfolio_risk, 'daily_pnl') and portfolio_risk.daily_pnl is not None:
                # If we have daily PnL, calculate return
                if nav > 0:
                    daily_return = portfolio_risk.daily_pnl / nav
                    daily_returns_history = [daily_return]  # Single day for now
            # TODO: In production, maintain rolling history of daily returns
            
            # Run PME allocation cycle
            allocations = self.portfolio_manager.generate_allocation_vector(
                regime=current_regime,
                account_nav=nav,
                daily_returns_history=daily_returns_history
            )
            
            # Apply allocations to risk manager
            for alloc in allocations:
                strategy_name = alloc.get("strategy_name")
                cap_pct = alloc.get("capital_pct")
                
                if strategy_name and cap_pct is not None and cap_pct > 0:
                    self.risk_manager.set_strategy_cap(
                        strategy_name=strategy_name,
                        max_capital_pct=cap_pct
                    )
            
            logger.info(
                "✅ PME: Allocation cycle completed",
                regime=current_regime,
                nav=nav,
                num_allocations=len(allocations),
                event_ctx=event_ctx
            )
        except Exception as e:
            logger.error(
                f"❌ PME: Allocation cycle failed: {e}",
                exc_info=True
            )
    
    async def _main_loop(self) -> None:
        """Main trading loop (deprecated - use _scan_supervisor instead)"""
        logger.warning("_main_loop called - this should not happen, using _scan_supervisor instead")
        await self._scan_supervisor()
    
    async def _scan_cycle(self) -> None:
        """Execute one scan cycle: signals → rank → execute"""
        from packages.core.heartbeats import touch_scan
        touch_scan()
        if self.is_paused:
            return
        
        current_time = datetime.now()
        
        # Throttle scans
        if self.last_scan_time:
            elapsed = (current_time - self.last_scan_time).total_seconds()
            if elapsed < self.scan_interval_seconds:
                return
        
        self.last_scan_time = current_time
        
        logger.debug("Running scan cycle", timestamp=current_time.isoformat())
        
        # 1. Get universe tokens with configurable limit (Patch 1)
        universe_tokens = self.instrument_manager.get_universe_tokens()
        universe_size = len(universe_tokens) if universe_tokens else 0
        
        if universe_size == 0:
            logger.warning("[Orchestrator] Universe is empty in _scan_cycle")
            return
        
        # Apply token limit
        if universe_size > self.max_tokens_per_scan:
            tokens_to_scan = universe_tokens[:self.max_tokens_per_scan]
            logger.debug(
                f"[Orchestrator] Scan cycle at {current_time.isoformat()}, "
                f"universe={universe_size}, using={len(tokens_to_scan)} tokens"
            )
        else:
            tokens_to_scan = universe_tokens
            logger.debug(
                f"[Orchestrator] Scan cycle at {current_time.isoformat()}, "
                f"universe={universe_size}, using all tokens"
            )
        
        # 2. Get regime and event snapshots ONCE per scan (Patch 3)
        regime_snapshot = None
        event_snapshot = None
        
        # Get R1 regime snapshot
        r1_strategy = next((s for s in self.strategies if s.name == "RegimeVolEngine"), None)
        if r1_strategy and hasattr(r1_strategy, 'get_snapshot'):
            try:
                regime_snapshot = r1_strategy.get_snapshot()
            except Exception as e:
                logger.error(f"[Orchestrator] Error getting regime snapshot: {e}", exc_info=True)
        
        # Get E1 event snapshot
        e1_strategy = next((s for s in self.strategies if hasattr(s, 'get_today_classification')), None)
        if e1_strategy and hasattr(e1_strategy, 'get_today_classification'):
            try:
                event_snapshot = e1_strategy.get_today_classification()
            except Exception as e:
                logger.error(f"[Orchestrator] Error getting event snapshot: {e}", exc_info=True)
        
        # NEW: Run allocator periodically (Patch: Periodic, Regime-Aware Allocator)
        await self._maybe_run_allocator(regime_snapshot, event_snapshot)
        
        # Increment scan counter for periodic delta neutralizer checks
        self._scan_ticks += 1
        
        # NEW: Delta neutralizer every M scans (e.g., once/min if 5s scans)
        if self.delta_neutralizer and (self._scan_ticks % 12 == 0):  # 12 * 5s = 60s = 1 minute
            try:
                await self.delta_neutralizer.maybe_rebalance()
            except Exception as e:
                logger.error(f"[Orchestrator] Delta neutralizer error: {e}", exc_info=True)
        
        # 3. Generate signals from all strategies (sorted by priority - Patch 2)
        all_signals = []
        
        for strategy in self._sorted_strategies():
            if not strategy.enabled:
                continue
            
            try:
                # Run strategy on tokens
                await self._run_strategy_on_tokens(
                    strategy, tokens_to_scan, current_time,
                    regime_snapshot, event_snapshot, all_signals
                )
            except Exception as e:
                logger.error(
                    f"[Orchestrator] Error in strategy {getattr(strategy, 'name', str(strategy))}: {e}",
                    exc_info=True
                )
        
        if not all_signals:
            return
        
        self.signals_generated_today += len(all_signals)
        record_signals_per_cycle(len(all_signals))
        logger.info(f"Generated {len(all_signals)} signals from {len(self.strategies)} strategies")
        
        # Publish signals to Redis
        if self.redis_bus:
            for signal in all_signals:
                record_signal(signal.strategy_name, signal.instrument.symbol)
                asyncio.create_task(self.redis_bus.publish_signal({
                    "strategy": signal.strategy_name,
                    "symbol": signal.instrument.symbol,
                    "side": signal.side.value,
                    "entry_price": signal.entry_price,
                    "stop_loss": signal.stop_loss,
                    "confidence": signal.confidence
                }))
        
        # 2. Rank signals
        market_data_dict = {}
        for signal in all_signals:
            token = signal.instrument.token
            tick = self.market_data_stream.get_latest_tick(token)
            bars_5s = self.market_data_stream.get_bars(token, 5, n=100)
            if tick and bars_5s:
                market_data_dict[token] = (tick, bars_5s)
        
        ranked_opportunities = self.ranker.rank_signals(
            all_signals,
            market_data_dict
        )
        
        if not ranked_opportunities:
            logger.debug("No ranked opportunities after filtering")
            return
        
        logger.info(f"Top {len(ranked_opportunities)} ranked opportunities")
        
        # NEW: Pre-trade safety check (self-healing integration)
        if self._self_healing_enabled and self._self_diagnostics:
            blocking = await self._pre_trade_safety_check()
            if blocking:
                logger.warning(
                    "Trading blocked by self-healing diagnostics",
                    blocking_anomalies=self._blocking_anomalies
                )
                return  # Block entire scan cycle if critical anomalies detected
        
        # 3. Persist signals and execute top opportunities
        for rank, opportunity in enumerate(ranked_opportunities[:3], 1):  # Top 3 only
            if self.is_paused:
                break
            
            signal = opportunity.signal
            
            # Record signal in diagnostics
            if self._self_healing_enabled and self._self_diagnostics:
                self._self_diagnostics.record_signal(datetime.now())
            
            # Persist signal with features
            signal_id = persist_signal(
                signal=signal,
                score=opportunity.score,
                rank=rank,
                features=opportunity.features if hasattr(opportunity, 'features') else {},
                feature_scores=opportunity.feature_scores if hasattr(opportunity, 'feature_scores') else {},
                penalties=opportunity.penalties if hasattr(opportunity, 'penalties') else {}
            )
            record_signal_ranked(signal.strategy_name, signal.instrument.symbol, rank)

            # Risk check
            portfolio_risk = self._get_portfolio_risk()
            risk_check = self.risk_manager.check_signal(signal, portfolio_risk)

            # Persist decision
            decision_id = persist_decision(
                signal_id=signal_id,
                approved=risk_check.approved,
                risk_pct=risk_check.risk_pct,
                risk_amount=risk_check.risk_amount if hasattr(risk_check, 'risk_amount') else 0.0,
                position_size=risk_check.position_size,
                rr_expected=signal.expected_rr if hasattr(signal, 'expected_rr') else None,
                portfolio_heat_before=portfolio_risk.portfolio_heat_pct,
                portfolio_heat_after=portfolio_risk.portfolio_heat_pct,  # Will update after execution
                rejection_reasons=risk_check.reasons if not risk_check.approved else None
            )

            # Publish decision to Redis
            if self.redis_bus:
                asyncio.create_task(self.redis_bus.publish_decision({
                    "decision_id": decision_id,
                    "signal_id": signal_id,
                    "approved": risk_check.approved,
                    "position_size": risk_check.position_size,
                    "risk_pct": risk_check.risk_pct
                }))
            
            if not risk_check.approved:
                # Record rejection in diagnostics
                if self._self_healing_enabled and self._self_diagnostics:
                    rejection_reason = risk_check.reasons[0] if risk_check.reasons else "unknown"
                    self._self_diagnostics.record_rejection(rejection_reason, signal.strategy_name)
                
                record_decision_rejected(signal.strategy_name, signal.instrument.symbol, 
                                       risk_check.reasons[0] if risk_check.reasons else "unknown")
                logger.debug(
                    f"Signal rejected by risk manager",
                    instrument=signal.instrument.tradingsymbol,
                    reasons=risk_check.reasons
                )
                continue
            
            record_decision_approved(signal.strategy_name, signal.instrument.symbol)
            
            # Execute signal with decision context (skip if dry_run mode)
            if app_config.execution.dry_run:
                logger.info(
                    "DRY_RUN: Signal approved but not executing",
                    strategy=signal.strategy_name,
                    instrument=signal.instrument.tradingsymbol,
                    position_size=risk_check.position_size
                )
            else:
                await self._execute_signal(signal, risk_check.position_size, decision_id)

    async def _execute_signal(self, signal: Signal, quantity: int, decision_id: int) -> None:
        """Execute a trading signal with persistence"""
        try:
            logger.info(
                "Executing signal",
                strategy=signal.strategy_name,
                instrument=signal.instrument.tradingsymbol,
                side=signal.side.value,
                quantity=quantity
            )
            
            # Place entry order
            # Convert signal side (LONG/SHORT) to order side (BUY/SELL)
            order_side = "BUY" if signal.side == SignalSide.LONG else "SELL"
            order = await self.execution_engine.place_order(
                symbol=signal.instrument.tradingsymbol,
                side=order_side,
                quantity=quantity,
                product="NRML",
                order_type="MARKET",
                price=None,
                tag=f"{signal.strategy_name}_ENTRY",
                instrument=signal.instrument
            )

            if order.success:
                # Record fill in diagnostics (for latency and slippage tracking)
                if self._self_healing_enabled and self._self_diagnostics:
                    signal_time = signal.timestamp if hasattr(signal, 'timestamp') else datetime.now()
                    fill_time = datetime.now()
                    # Calculate slippage (simplified - would need actual expected price)
                    slippage_bps = 0.0  # Placeholder - would calculate from signal.entry_price vs order.avg_price
                    if hasattr(signal, 'entry_price') and order.avg_price:
                        price_diff = abs(order.avg_price - signal.entry_price)
                        slippage_bps = (price_diff / signal.entry_price) * 10000 if signal.entry_price > 0 else 0.0
                    self._self_diagnostics.record_fill(
                        signal_time=signal_time,
                        fill_time=fill_time,
                        slippage_bps=slippage_bps,
                        strategy=signal.strategy_name
                    )
                
                # Persist order
                order_model = persist_order(
                    decision_id=decision_id,
                    symbol=signal.instrument.symbol,
                    instrument_token=signal.instrument.token,
                    side="BUY" if signal.side == SignalSide.LONG else "SELL",
                    qty=quantity,
                    order_type="MARKET",
                    price=order.avg_price,
                    tag="ENTRY",
                    parent_group=None,  # Will be set by OCO manager
                    broker_order_id=order.order_id if hasattr(order, 'order_id') else None,
                    strategy_name=signal.strategy_name
                )
                record_order_placed("MARKET", "PLACED")
                
                # Publish order to Redis
                if self.redis_bus:
                    asyncio.create_task(self.redis_bus.publish_order({
                        "event": "ENTRY_PLACED",
                        "client_order_id": order_model.client_order_id,
                        "symbol": signal.instrument.symbol,
                        "qty": quantity
                    }))
                
                # Create position
                position = Position(
                    position_id=f"POS_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.positions)}",
                    instrument=signal.instrument,
                    entry_time=datetime.now(),
                    entry_price=order.avg_price,
                    quantity=order.filled_qty,
                    side=signal.side,
                    current_price=order.avg_price,
                    stop_loss=signal.stop_loss,
                    take_profit_1=signal.take_profit_1,
                    take_profit_2=signal.take_profit_2,
                    risk_amount=signal.risk_amount,
                    status=PositionStatus.OPEN,
                    entry_order_id=order.order_id,
                    strategy_name=signal.strategy_name
                )
                
                self.positions.append(position)
                
                # Sync to PositionStore (canonical source)
                if self.position_store:
                    self.position_store.add_position(position)
                
                self.orders_placed_today += 1
                
                # Notify strategy
                for strategy in self.strategies:
                    if strategy.name == signal.strategy_name:
                        strategy.on_position_opened()
                        break
                
                logger.info(
                    "Position opened",
                    position_id=position.position_id,
                    instrument=signal.instrument.tradingsymbol,
                    entry_price=order.avg_price
                )
        
        except Exception as e:
            logger.error("Signal execution failed", error=str(e), signal=signal)
    
    async def _check_exits(self) -> None:
        """Check all positions for exit conditions"""
        if not self.positions:
            return
        
        # Update position prices
        for position in self.positions:
            if not position.is_open:
                continue
            
            tick = self.market_data_stream.get_latest_tick(position.instrument.token)
            if tick:
                position.current_price = tick.last_price
                position.update_pnl()
                
                # Sync price updates to PositionStore
                if self.position_store and position.position_id:
                    self.position_store.update_position(position.position_id, position.current_price)
        
        # Get market data for exit manager
        market_data = {}
        for position in self.positions:
            if position.is_open:
                token = position.instrument.token
                tick = self.market_data_stream.get_latest_tick(token)
                bars_5s = self.market_data_stream.get_bars(token, 5, n=100)
                if tick and bars_5s:
                    market_data[token] = (tick, bars_5s)
        
        # Check exits (use enhanced exit manager for spread-specific logic)
        portfolio_risk = self._get_portfolio_risk()
        exit_signals = self.enhanced_exit_manager.check_exits(
            [p for p in self.positions if p.is_open],
            market_data,
            datetime.now(),
            portfolio_risk.daily_pnl_pct,
            portfolio_risk.net_liquid
        )
        
        # Execute exits
        for exit_signal in exit_signals:
            await self._close_position_by_id(exit_signal.position_id, exit_signal.reason.value)
    
    async def _close_position_by_id(self, position_id: str, reason: str) -> None:
        """Close a position by ID"""
        position = next((p for p in self.positions if p.position_id == position_id), None)
        
        if not position or not position.is_open:
            return
        
        try:
            # Close position
            exit_order = await self.execution_engine.close_position(position, reason)
            
            if exit_order:
                position.status = PositionStatus.CLOSED
                position.close_time = datetime.now()
                position.close_price = exit_order.avg_price
                position.exit_order_id = exit_order.order_id

                # Calculate P&L
                if position.side == SignalSide.LONG:
                    gross_pnl = (exit_order.avg_price - position.entry_price) * position.quantity
                else:
                    gross_pnl = (position.entry_price - exit_order.avg_price) * position.quantity

                fees = self.risk_manager.estimate_fees(
                    position.instrument,
                    position.quantity,
                    position.entry_price,
                    exit_order.avg_price
                )

                position.realized_pnl = gross_pnl - fees
                self.trades_completed_today += 1

                # Sync to PositionStore (canonical source)
                if self.position_store:
                    self.position_store.close_position(position.position_id, exit_order.avg_price, datetime.now())
                
                # Notify strategy
                for strategy in self.strategies:
                    if strategy.name == position.strategy_name:
                        strategy.on_position_closed(position.realized_pnl or 0.0)
                        break
                
                logger.info(
                    "Position closed",
                    position_id=position_id,
                    reason=reason,
                    pnl=position.realized_pnl
                )
        
        except Exception as e:
            logger.error(f"Failed to close position {position_id}", error=str(e))
    
    async def _close_all_positions(self, reason: str) -> None:
        """Close all open positions"""
        open_positions = [p for p in self.positions if p.is_open]
        
        for position in open_positions:
            await self._close_position_by_id(position.position_id, reason)
    
    async def _update_portfolio_state(self) -> None:
        """Update portfolio state and check limits"""
        portfolio_risk = self._get_portfolio_risk()
        
        # Check daily loss limit
        if portfolio_risk.is_daily_loss_breached:
            logger.critical("Daily loss limit breached - pausing trading")
            await self.pause()
        
        # Check portfolio heat
        if portfolio_risk.is_heat_limit_breached:
            logger.warning("Portfolio heat limit breached - pausing new entries")
            # Don't pause completely, just stop new entries
        
        # EOD square-off
        if self._should_square_off_eod():
            logger.info("EOD square-off time - closing all positions")
            await self._close_all_positions("EOD_SQUAREOFF")
    
    async def _periodic_diagnostics(self) -> None:
        """Run periodic diagnostics every 5 minutes and apply healing if needed"""
        while self.is_running:
            try:
                await asyncio.sleep(self._diagnostics_interval)
                
                if not self._self_healing_enabled or not self._self_diagnostics:
                    continue
                
                logger.debug("Running periodic diagnostics")
                
                # Get current metrics
                portfolio_risk = self._get_portfolio_risk()
                current_metrics = {
                    "win_rate": (self.wins_today / max(self.trades_completed_today, 1)) if self.trades_completed_today > 0 else 0.0,
                    "trades_today": self.trades_completed_today,
                    "daily_pnl": portfolio_risk.daily_pnl,
                    "margin_utilization": portfolio_risk.used_margin / max(portfolio_risk.net_liquid, 1) if portfolio_risk.net_liquid > 0 else 0.0,
                }
                
                # Get strategy performance (simplified - would need more detailed tracking)
                strategy_performance = {}
                for strategy in self.strategies:
                    # Placeholder - would track actual performance per strategy
                    strategy_performance[strategy.name] = {
                        "win_rate": 0.0,
                        "trades": 0
                    }
                
                # Run diagnostics
                diagnostic_results = self._self_diagnostics.run_diagnostics(
                    current_metrics,
                    strategy_performance
                )
                
                # Update blocking anomalies
                self._blocking_anomalies = [
                    r.anomaly_type.value for r in diagnostic_results
                    if r.severity in ["CRITICAL", "HIGH"] and r.detected
                ]
                
                # Apply healing for HIGH/CRITICAL anomalies
                if self._self_healing and diagnostic_results:
                    for diagnostic in diagnostic_results:
                        if diagnostic.severity in ["HIGH", "CRITICAL"]:
                            healing_result = self._self_healing.apply_healing(diagnostic)
                            if healing_result and healing_result.success:
                                logger.info(
                                    "Healing action applied",
                                    action=healing_result.action.value,
                                    message=healing_result.message,
                                    anomaly=diagnostic.anomaly_type.value
                                )
                
                self._last_diagnostics_run = datetime.now()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Periodic diagnostics error: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait 1 minute before retry
    
    async def _pre_trade_safety_check(self) -> bool:
        """
        Pre-trade safety check - returns True if trading should be blocked.
        
        Returns:
            True if trading should be blocked, False otherwise
        """
        if not self._self_healing_enabled or not self._self_diagnostics:
            return False
        
        # Quick check for blocking anomalies
        if self._blocking_anomalies:
            # Check if any blocking anomalies are still active
            portfolio_risk = self._get_portfolio_risk()
            current_metrics = {
                "win_rate": (self.wins_today / max(self.trades_completed_today, 1)) if self.trades_completed_today > 0 else 0.0,
                "trades_today": self.trades_completed_today,
                "daily_pnl": portfolio_risk.daily_pnl,
                "margin_utilization": portfolio_risk.used_margin / max(portfolio_risk.net_liquid, 1) if portfolio_risk.net_liquid > 0 else 0.0,
            }
            
            # Run quick diagnostics
            diagnostic_results = self._self_diagnostics.run_diagnostics(current_metrics)
            
            # Check for CRITICAL anomalies that should block trading
            critical_anomalies = [
                r for r in diagnostic_results
                if r.severity == "CRITICAL" and r.detected
            ]
            
            if critical_anomalies:
                self._blocking_anomalies = [r.anomaly_type.value for r in critical_anomalies]
                return True
        
        return False
    
    def _get_portfolio_risk(self) -> PortfolioRisk:
        """Get current portfolio risk state"""
        net_liquid = self._get_net_liquid()
        total_risk = sum([p.risk_amount for p in self.positions if p.is_open])
        unrealized_pnl = sum([p.unrealized_pnl for p in self.positions if p.is_open])
        realized_pnl_today = sum([p.realized_pnl or 0.0 for p in self.positions if not p.is_open])
        
        return self.risk_manager.update_portfolio_risk(
            net_liquid=net_liquid,
            positions=self.positions,
            realized_pnl_today=realized_pnl_today
        )
    
    def _get_net_liquid(self) -> float:
        """Get net liquid capital (simplified - would fetch from Kite in production)"""
        # In production, fetch from: self.kite.margins()['equity']['net']
        return 1000000.0  # Default 10 lakh for paper mode
    
    def _get_available_margin(self) -> float:
        """Get available margin"""
        portfolio_risk = self._get_portfolio_risk()
        return portfolio_risk.available_margin
    
    def _is_market_open(self) -> bool:
        """Check if market is currently open"""
        current_time = datetime.now().time()
        
        def _parse_time(time_str: str, fallback: time) -> time:
            try:
                return datetime.strptime(time_str, "%H:%M").time()
            except Exception:
                return fallback
        
        # Primary (NSE/BSE) window
        primary_open = _parse_time(app_config.market.open_time, time(9, 15))
        primary_close = _parse_time(app_config.market.close_time, time(15, 30))
        if primary_open <= current_time <= primary_close:
            return True
        
        # MCX extended window (if enabled in universe)
        if getattr(app_config.universe, "mcx_symbols", []):
            mcx_open = _parse_time(app_config.market.mcx_open_time, time(9, 0))
            mcx_close = _parse_time(app_config.market.mcx_close_time, time(23, 30))
            if mcx_open <= current_time <= mcx_close:
                return True
        
        return False
    
    def _should_square_off_eod(self) -> bool:
        """Check if EOD square-off should happen"""
        if not app_config.market.eod_squareoff_enabled:
            return False
        
        current_time = datetime.now().time()
        
        def _parse_time(time_str: str, fallback: time) -> time:
            try:
                return datetime.strptime(time_str, "%H:%M").time()
            except Exception:
                return fallback
        
        # Prefer MCX square-off if MCX is in play
        eod_str = app_config.market.eod_squareoff_time
        if getattr(app_config.universe, "mcx_symbols", []):
            eod_str = getattr(app_config.market, "mcx_eod_squareoff_time", eod_str)
        
        eod_time = _parse_time(eod_str, time(15, 25))
        return current_time >= eod_time
    
    def get_system_state(self) -> SystemState:
        """Get current system state"""
        from packages.core.models import SystemState, PortfolioState
        
        portfolio_risk = self._get_portfolio_risk()
        
        portfolio_state = PortfolioState(
            timestamp=datetime.now(),
            net_liquid=portfolio_risk.net_liquid,
            used_margin=portfolio_risk.used_margin,
            available_margin=portfolio_risk.available_margin,
            open_positions=[p for p in self.positions if p.is_open],
            total_positions=len([p for p in self.positions if p.is_open]),
            unrealized_pnl=portfolio_risk.unrealized_pnl,
            realized_pnl_today=portfolio_risk.realized_pnl_today,
            daily_pnl=portfolio_risk.daily_pnl,
            daily_pnl_pct=portfolio_risk.daily_pnl_pct,
            portfolio_heat=portfolio_risk.total_risk_amount,
            portfolio_heat_pct=portfolio_risk.portfolio_heat_pct,
            max_portfolio_heat_pct=app_config.risk.max_portfolio_heat_pct,
            daily_loss_limit=portfolio_risk.daily_loss_limit
        )
        
        wins = len([p for p in self.positions if not p.is_open and (p.realized_pnl or 0) > 0])
        losses = len([p for p in self.positions if not p.is_open and (p.realized_pnl or 0) <= 0])
        
        return SystemState(
            timestamp=datetime.now(),
            mode=settings.app_mode.value,
            is_paused=self.is_paused,
            is_market_open=self._is_market_open(),
            portfolio=portfolio_state,
            pending_signals=0,  # Would track pending signals
            active_orders=0,  # Would track from execution engine
            trades_today=self.trades_completed_today,
            wins_today=wins,
            losses_today=losses
        )
