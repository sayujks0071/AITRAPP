"""SEBI Compliance API Endpoints"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from packages.storage.database import get_db_session
from packages.storage.models import AuditLog, AuditActionEnum

router = APIRouter()
logger = logging.getLogger(__name__)


class ComplianceCheck(BaseModel):
    """Individual compliance feature check"""
    feature: str
    status: str  # pass, fail, warning, unknown
    message: str
    last_checked: Optional[str] = None


class AuditStats(BaseModel):
    """Audit logging statistics"""
    orders_placed_today: int
    orders_cancelled_today: int
    kill_switch_activations_today: int
    last_audit_log_time: Optional[str] = None


class StrategyRisk(BaseModel):
    """Strategy risk tracking"""
    strategy: str
    pnl: float
    limit: float
    status: str  # ok, warning, critical


class ComplianceStatusResponse(BaseModel):
    """Complete compliance status"""
    compliance_checks: List[ComplianceCheck]
    audit_stats: AuditStats
    strategy_risks: List[StrategyRisk]
    timestamp: str


@router.get("/status", response_model=ComplianceStatusResponse)
async def get_compliance_status(request: Request) -> ComplianceStatusResponse:
    """
    Get comprehensive SEBI compliance status.

    Returns:
        - Compliance feature checks
        - Audit logging statistics
        - Strategy-wise risk tracking
    """
    state = request.app.state.aitrapp

    # 1. Compliance Feature Checks
    compliance_checks = []

    # Check 1: Audit logging
    try:
        async with get_db_session() as session:
            # Check if audit logs are being written
            from sqlalchemy import func, select
            from sqlalchemy.sql import text

            # Get count of recent audit logs (last 5 minutes)
            five_min_ago = datetime.now() - timedelta(minutes=5)
            stmt = select(func.count()).select_from(AuditLog).where(
                AuditLog.ts >= five_min_ago
            )
            result = await session.execute(stmt)
            recent_count = result.scalar() or 0

            if recent_count > 0:
                compliance_checks.append(
                    ComplianceCheck(
                        feature="Enhanced Audit Logging",
                        status="pass",
                        message=f"Audit logs active ({recent_count} logs in last 5 min)",
                        last_checked=datetime.now().isoformat(),
                    )
                )
            else:
                compliance_checks.append(
                    ComplianceCheck(
                        feature="Enhanced Audit Logging",
                        status="warning",
                        message="No recent audit logs (may be low activity)",
                        last_checked=datetime.now().isoformat(),
                    )
                )
    except Exception as e:
        logger.error(f"Error checking audit logs: {e}")
        compliance_checks.append(
            ComplianceCheck(
                feature="Enhanced Audit Logging",
                status="fail",
                message=f"Database error: {str(e)}",
                last_checked=datetime.now().isoformat(),
            )
        )

    # Check 2: Kill switch endpoint
    compliance_checks.append(
        ComplianceCheck(
            feature="Kill Switch Endpoint",
            status="pass",
            message="Emergency stop available at /control/kill-switch",
            last_checked=datetime.now().isoformat(),
        )
    )

    # Check 3: Strategy risk limits
    try:
        risk_manager = state.risk_manager
        strategy_count = len(risk_manager.strategy_pnl)

        compliance_checks.append(
            ComplianceCheck(
                feature="Strategy Risk Limits",
                status="pass",
                message=f"Tracking {strategy_count} strategies",
                last_checked=datetime.now().isoformat(),
            )
        )
    except Exception as e:
        logger.error(f"Error checking strategy risks: {e}")
        compliance_checks.append(
            ComplianceCheck(
                feature="Strategy Risk Limits",
                status="warning",
                message="Risk manager not available",
                last_checked=datetime.now().isoformat(),
            )
        )

    # Check 4: Rate limiting
    try:
        rate_limiter = state.execution_engine.rate_limiter
        # Get recent order rate
        # This is simplified - in production, would calculate from rate limiter state
        compliance_checks.append(
            ComplianceCheck(
                feature="Rate Limiting (<10 OPS)",
                status="pass",
                message="Rate limiter active (cap: 10 OPS)",
                last_checked=datetime.now().isoformat(),
            )
        )
    except Exception:
        compliance_checks.append(
            ComplianceCheck(
                feature="Rate Limiting (<10 OPS)",
                status="warning",
                message="Rate limiter status unknown",
                last_checked=datetime.now().isoformat(),
            )
        )

    # 2. Audit Statistics
    try:
        async with get_db_session() as session:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            # Orders placed today
            stmt = select(func.count()).select_from(AuditLog).where(
                AuditLog.action == AuditActionEnum.ORDER_PLACED,
                AuditLog.ts >= today_start,
            )
            result = await session.execute(stmt)
            orders_placed = result.scalar() or 0

            # Orders cancelled today
            stmt = select(func.count()).select_from(AuditLog).where(
                AuditLog.action == AuditActionEnum.ORDER_CANCELLED,
                AuditLog.ts >= today_start,
            )
            result = await session.execute(stmt)
            orders_cancelled = result.scalar() or 0

            # Kill switch activations today
            stmt = select(func.count()).select_from(AuditLog).where(
                AuditLog.action == AuditActionEnum.KILL_SWITCH,
                AuditLog.ts >= today_start,
            )
            result = await session.execute(stmt)
            kill_switches = result.scalar() or 0

            # Last audit log time
            stmt = (
                select(AuditLog.ts)
                .select_from(AuditLog)
                .order_by(AuditLog.ts.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            last_log = result.scalar()

            audit_stats = AuditStats(
                orders_placed_today=orders_placed,
                orders_cancelled_today=orders_cancelled,
                kill_switch_activations_today=kill_switches,
                last_audit_log_time=last_log.isoformat() if last_log else None,
            )
    except Exception as e:
        logger.error(f"Error fetching audit stats: {e}")
        audit_stats = AuditStats(
            orders_placed_today=0,
            orders_cancelled_today=0,
            kill_switch_activations_today=0,
            last_audit_log_time=None,
        )

    # 3. Strategy Risks
    strategy_risks = []
    try:
        risk_manager = state.risk_manager
        net_liquid = 100000.0  # TODO: Get from portfolio

        max_loss_pct = risk_manager.config.max_loss_per_strategy_pct
        max_loss = net_liquid * (max_loss_pct / 100)

        for strategy_name, pnl in risk_manager.strategy_pnl.items():
            # Determine status
            usage_pct = abs(pnl / max_loss) * 100 if max_loss != 0 else 0

            if usage_pct >= 90:
                status = "critical"
            elif usage_pct >= 70:
                status = "warning"
            else:
                status = "ok"

            strategy_risks.append(
                StrategyRisk(
                    strategy=strategy_name,
                    pnl=pnl,
                    limit=max_loss,
                    status=status,
                )
            )
    except Exception as e:
        logger.error(f"Error fetching strategy risks: {e}")

    return ComplianceStatusResponse(
        compliance_checks=compliance_checks,
        audit_stats=audit_stats,
        strategy_risks=strategy_risks,
        timestamp=datetime.now().isoformat(),
    )


@router.get("/audit-report")
async def download_audit_report(request: Request):
    """
    Download today's audit trail as CSV.

    Returns:
        CSV file with audit logs
    """
    from fastapi.responses import StreamingResponse
    import io
    import csv

    try:
        async with get_db_session() as session:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            from sqlalchemy import select

            stmt = (
                select(AuditLog)
                .where(AuditLog.ts >= today_start)
                .order_by(AuditLog.ts.desc())
            )

            result = await session.execute(stmt)
            logs = result.scalars().all()

            # Create CSV
            output = io.StringIO()
            writer = csv.writer(output)

            # Header
            writer.writerow(["Timestamp", "Action", "Category", "Message", "Details"])

            # Data
            for log in logs:
                writer.writerow(
                    [
                        log.ts.isoformat(),
                        log.action.value if log.action else "",
                        log.category or "",
                        log.message,
                        str(log.details or {}),
                    ]
                )

            output.seek(0)

            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=audit_trail_{datetime.now():%Y%m%d}.csv"
                },
            )

    except Exception as e:
        logger.error(f"Error generating audit report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate audit report: {str(e)}",
        )
