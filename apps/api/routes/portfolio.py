"""
Portfolio API Routes - Level 13 Broker-Grade Command Center
===========================================================

Broker-grade portfolio snapshot endpoints with real-time reconciliation.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

import structlog

from packages.core.broker.portfolio_snapshot import PortfolioSnapshotEngine

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("/snapshot")
async def get_portfolio_snapshot() -> Dict[str, Any]:
    """
    Get comprehensive portfolio snapshot from Kite broker.
    
    Level 13: Real-time reconciliation between Algo's view and Broker's ledger.
    
    Returns:
        PortfolioSnapshot with funds, positions, and reconciliation data
    """
    try:
        # Import here to avoid circular dependency
        from apps.api.main import app_state
        
        if not app_state.kite:
            raise HTTPException(status_code=503, detail="Kite client not initialized")
        
        # Use the new PortfolioSnapshotEngine
        engine = PortfolioSnapshotEngine(
            kite=app_state.kite,
            position_store=app_state.position_store
        )
        
        snapshot = await engine.build_snapshot()
        
        return snapshot
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get portfolio snapshot", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get portfolio snapshot: {str(e)}")

