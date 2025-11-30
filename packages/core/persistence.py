"""Persistence helpers for orchestrator"""
import hashlib
from datetime import datetime
from typing import Optional
import structlog

from packages.storage.models import (
    Signal, Decision, Order, OrderStatusEnum, OrderTypeEnum, OrderSideEnum,
    DecisionStatusEnum, SideEnum
)
from packages.storage.database import get_db_session
from packages.core.models import Signal as CoreSignal
from packages.core.config import app_config


def _to_float(val):
    """Safely convert numpy/pydantic/Decimal to built-in float where possible."""
    try:
        return float(val)
    except Exception:
        return val


def _clean_numeric_mapping(data: Optional[dict]) -> dict:
    """Convert mapping values to plain floats for JSON/DB compatibility."""
    if not data:
        return {}
    return {k: _to_float(v) for k, v in data.items()}

logger = structlog.get_logger(__name__)


def get_config_sha() -> str:
    """Get SHA256 hash of current config for reproducibility"""
    try:
        # Hash the raw YAML to avoid object serialization issues
        with open(app_config.config_path, "r") as f:
            config_str = f.read()
    except Exception:
        # Fallback to object repr if file unavailable
        config_str = repr(app_config.__dict__)
    return hashlib.sha256(config_str.encode()).hexdigest()[:16]


def persist_signal(
    signal: CoreSignal,
    score: Optional[float] = None,
    rank: Optional[int] = None,
    features: Optional[dict] = None,
    feature_scores: Optional[dict] = None,
    penalties: Optional[dict] = None
) -> int:
    """Persist a signal to database and return the signal ID"""
    with get_db_session() as db:
        signal_model = Signal(
            ts=datetime.utcnow(),
            symbol=signal.instrument.symbol,
            instrument_token=signal.instrument.token,
            side=SideEnum.LONG if signal.side.value == "LONG" else SideEnum.SHORT,
            strategy=signal.strategy_name,
            entry_price=_to_float(signal.entry_price),
            stop_loss=_to_float(signal.stop_loss),
            take_profit_1=_to_float(signal.take_profit_1),
            take_profit_2=_to_float(signal.take_profit_2),
            score=_to_float(score) if score is not None else None,
            rank=int(rank) if rank is not None else None,
            confidence=_to_float(signal.confidence),
            features=_clean_numeric_mapping(features),
            feature_scores=_clean_numeric_mapping(feature_scores),
            penalties=_clean_numeric_mapping(penalties),
            rationale=signal.rationale,
            config_sha=get_config_sha()
        )
        db.add(signal_model)
        db.flush()  # Flush to get ID without committing (commit handled by context manager)

        signal_id = signal_model.id  # Extract ID after flush
        logger.debug("Signal persisted", signal_id=signal_id, strategy=signal.strategy_name)
        return signal_id  # Return ID, not the ORM object


def persist_decision(
    signal_id: int,
    approved: bool,
    risk_pct: float,
    risk_amount: float,
    position_size: int,
    rr_expected: Optional[float] = None,
    portfolio_heat_before: Optional[float] = None,
    portfolio_heat_after: Optional[float] = None,
    rejection_reasons: Optional[list] = None
) -> int:
    """Persist a decision to database and return the decision ID"""
    with get_db_session() as db:
        # Generate deterministic client_plan_id
        client_plan_id = f"PLAN_{signal_id}_{datetime.utcnow().isoformat()}"

        decision_model = Decision(
            ts=datetime.utcnow(),
            signal_id=signal_id,
            client_plan_id=client_plan_id,
            mode=app_config.mode,
            status=DecisionStatusEnum.PLANNED if approved else DecisionStatusEnum.REJECTED,
            risk_perc=risk_pct,
            risk_amount=risk_amount,
            rr_expected=rr_expected,
            position_size=position_size,
            portfolio_heat_before=portfolio_heat_before,
            portfolio_heat_after=portfolio_heat_after,
            rejection_reasons=rejection_reasons or []
        )
        db.add(decision_model)
        db.flush()  # Flush to get ID without committing (commit handled by context manager)

        decision_id = decision_model.id  # Extract ID after flush
        logger.debug("Decision persisted",
                    decision_id=decision_id,
                    approved=approved,
                    client_plan_id=client_plan_id)
        return decision_id  # Return ID, not the ORM object


def persist_order(
    decision_id: int,
    symbol: str,
    instrument_token: int,
    side: str,  # "BUY" or "SELL"
    qty: int,
    order_type: str,  # "MARKET", "LIMIT", "SL", "SL-M"
    price: Optional[float] = None,
    trigger_price: Optional[float] = None,
    tag: str = "ENTRY",
    parent_group: Optional[str] = None,
    broker_order_id: Optional[str] = None,
    strategy_name: Optional[str] = None
) -> Order:
    """Persist an order to database"""
    with get_db_session() as db:
        # Query decision to get client_plan_id (within the session)
        from sqlalchemy.orm import selectinload
        decision = db.query(Decision).options(selectinload(Decision.signal)).filter_by(id=decision_id).first()
        if not decision:
            raise ValueError(f"Decision {decision_id} not found")

        # Generate deterministic client_order_id
        client_order_id = f"{decision.client_plan_id}_{tag}_{datetime.utcnow().timestamp()}"

        # Use provided strategy_name or query from decision's signal
        if not strategy_name and decision.signal:
            strategy_name = decision.signal.strategy

        order_model = Order(
            ts=datetime.utcnow(),
            decision_id=decision_id,
            client_order_id=client_order_id,
            broker_order_id=broker_order_id,
            symbol=symbol,
            instrument_token=instrument_token,
            side=OrderSideEnum.BUY if side == "BUY" else OrderSideEnum.SELL,
            qty=qty,
            order_type=OrderTypeEnum(order_type),
            price=price,
            trigger_price=trigger_price,
            tag=tag,
            parent_group=parent_group,
            is_stop_loss=(tag == "STOP"),
            is_take_profit=(tag in ["TP1", "TP2"]),
            strategy_name=strategy_name,
            status=OrderStatusEnum.PLACED if broker_order_id else OrderStatusEnum.PLACED
        )
        db.add(order_model)
        db.flush()  # Flush to get ID without committing (commit handled by context manager)

        logger.debug("Order persisted",
                    order_id=order_model.id,
                    client_order_id=client_order_id,
                    tag=tag)
        return order_model


def update_order_status(
    client_order_id: str,
    broker_order_id: Optional[str] = None,
    status: Optional[OrderStatusEnum] = None,
    filled_qty: Optional[int] = None,
    average_price: Optional[float] = None
) -> Optional[Order]:
    """Update order status"""
    with get_db_session() as db:
        order = db.query(Order).filter_by(client_order_id=client_order_id).first()
        if not order:
            logger.warning("Order not found for update", client_order_id=client_order_id)
            return None
        
        if broker_order_id:
            order.broker_order_id = broker_order_id
        if status:
            order.status = status
        if filled_qty is not None:
            order.filled_qty = filled_qty
        if average_price is not None:
            order.average_price = average_price
        
        db.commit()
        db.refresh(order)
        
        logger.debug("Order updated", 
                    client_order_id=client_order_id,
                    status=status.value if status else None)
        return order
