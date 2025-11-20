"""
MCP Analyst API endpoints

High-level endpoints designed for MCP trading-analyst server.
These return pre-digested views instead of raw data.
"""

from datetime import date, datetime
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api", tags=["mcp-analyst"])


@router.get("/risk/greeks")
async def get_portfolio_greeks():
    """
    Get portfolio-level greeks aggregation.

    Returns net delta, gamma, vega, theta across all positions.
    Used by MCP `get_live_risk_snapshot` tool.
    """
    from apps.api.main import app_state

    if not app_state.orchestrator:
        return {
            "net_delta": 0.0,
            "net_gamma": 0.0,
            "net_vega": 0.0,
            "net_theta": 0.0,
            "note": "Orchestrator not initialized"
        }

    try:
        # Calculate greeks from positions
        # If you have a dedicated greeks calculator, use it here
        # For now, return placeholder
        # TODO: Implement actual greeks calculation from positions

        positions = app_state.orchestrator.positions

        # Placeholder calculation (replace with real greeks engine)
        net_delta = sum(getattr(pos, 'delta', 0.0) for pos in positions if pos.is_open)
        net_gamma = sum(getattr(pos, 'gamma', 0.0) for pos in positions if pos.is_open)
        net_vega = sum(getattr(pos, 'vega', 0.0) for pos in positions if pos.is_open)
        net_theta = sum(getattr(pos, 'theta', 0.0) for pos in positions if pos.is_open)

        return {
            "net_delta": round(net_delta, 2),
            "net_gamma": round(net_gamma, 4),
            "net_vega": round(net_vega, 2),
            "net_theta": round(net_theta, 2),
        }
    except Exception as e:
        logger.error(f"Error calculating greeks: {e}")
        return {
            "net_delta": 0.0,
            "net_gamma": 0.0,
            "net_vega": 0.0,
            "net_theta": 0.0,
            "error": str(e)
        }


@router.get("/risk/short_premium")
async def get_short_premium():
    """
    Get short premium exposure by underlying.

    Returns notional value of short option premium.
    Used by MCP `get_live_risk_snapshot` tool.
    """
    from apps.api.main import app_state

    if not app_state.orchestrator:
        return {
            "total_notional": 0,
            "by_underlying": {},
            "note": "Orchestrator not initialized"
        }

    try:
        positions = app_state.orchestrator.positions

        # Calculate short premium by underlying
        by_underlying = {}
        total_notional = 0

        for pos in positions:
            if not pos.is_open:
                continue

            # Check if this is a short option position
            instrument = pos.instrument
            if not instrument:
                continue

            is_option = hasattr(instrument, 'instrument_type') and instrument.instrument_type in ('CE', 'PE')
            is_short = pos.quantity < 0

            if is_option and is_short:
                # Calculate notional (premium received * lot size * quantity)
                notional = abs(pos.entry_price * pos.quantity)
                total_notional += notional

                # Get underlying symbol
                underlying = getattr(instrument, 'name', 'UNKNOWN')
                by_underlying[underlying] = by_underlying.get(underlying, 0) + notional

        return {
            "total_notional": round(total_notional, 2),
            "by_underlying": {k: round(v, 2) for k, v in by_underlying.items()}
        }
    except Exception as e:
        logger.error(f"Error calculating short premium: {e}")
        return {
            "total_notional": 0,
            "by_underlying": {},
            "error": str(e)
        }


@router.get("/risk/tail_coverage")
async def get_tail_coverage():
    """
    Get tail coverage metrics.

    Returns percentage of short premium covered by long tail hedges.
    Used by MCP `get_live_risk_snapshot` tool.
    """
    from apps.api.main import app_state

    if not app_state.orchestrator:
        return {
            "overall_pct": 0.0,
            "by_underlying": {},
            "note": "Orchestrator not initialized"
        }

    try:
        # If H1 (TailShortVolOverlay) is active, get coverage from it
        h1_strategy = app_state.strategies.get("TailShortVolOverlay")

        if h1_strategy:
            # Get coverage metrics from H1
            coverage_data = getattr(h1_strategy, 'get_coverage_metrics', lambda: {})()
            return coverage_data

        # Fallback: calculate manually
        short_premium_data = await get_short_premium()
        total_short = short_premium_data['total_notional']

        if total_short == 0:
            return {
                "overall_pct": 0.0,
                "by_underlying": {},
                "note": "No short premium to hedge"
            }

        # Calculate long tail premium (OTM long options)
        positions = app_state.orchestrator.positions
        long_tail_premium = 0
        long_by_underlying = {}

        for pos in positions:
            if not pos.is_open:
                continue

            instrument = pos.instrument
            if not instrument:
                continue

            is_option = hasattr(instrument, 'instrument_type') and instrument.instrument_type in ('CE', 'PE')
            is_long = pos.quantity > 0

            if is_option and is_long:
                # Check if this is a tail hedge (far OTM)
                # Simple heuristic: strike > 2% away from spot
                # TODO: Implement proper OTM detection

                notional = abs(pos.entry_price * pos.quantity)
                long_tail_premium += notional

                underlying = getattr(instrument, 'name', 'UNKNOWN')
                long_by_underlying[underlying] = long_by_underlying.get(underlying, 0) + notional

        # Calculate coverage percentages
        overall_pct = (long_tail_premium / total_short * 100) if total_short > 0 else 0.0

        by_underlying = {}
        for underlying, short_val in short_premium_data['by_underlying'].items():
            long_val = long_by_underlying.get(underlying, 0)
            pct = (long_val / short_val * 100) if short_val > 0 else 0.0
            by_underlying[underlying] = round(pct, 1)

        return {
            "overall_pct": round(overall_pct, 1),
            "by_underlying": by_underlying,
        }
    except Exception as e:
        logger.error(f"Error calculating tail coverage: {e}")
        return {
            "overall_pct": 0.0,
            "by_underlying": {},
            "error": str(e)
        }


@router.get("/strategies/summary")
async def get_strategy_summary(lookback_days: int = 60):
    """
    Get per-strategy performance summary.

    Returns:
    - Realised/unrealised PnL
    - Hit rate over lookback window
    - Max drawdown
    - Current allocation
    - Regime usage (which regimes this strategy is active in)

    Used by MCP `get_strategy_summary` tool.
    """
    from apps.api.main import app_state
    from datetime import datetime, timedelta

    if not app_state.strategies:
        return {
            "date": date.today().isoformat(),
            "strategies": [],
            "note": "No strategies loaded"
        }

    try:
        strategies_data = []

        for name, strategy in app_state.strategies.items():
            # Get basic info
            strategy_info = {
                "name": name,
                "enabled": getattr(strategy, 'enabled', True),  # Strategy enabled status
                "role": getattr(strategy, 'role', 'unknown'),  # e.g., 'income_short_vol', 'long_gamma'
                "regime_usage": getattr(strategy, 'regime_usage', {}),  # Which regimes it's active in
                "realised_pnl": 0.0,
                "unrealised_pnl": 0.0,
                "hit_rate_20d": 0.0,
                "max_dd_60d": 0.0,
                "current_allocation_pct": 0.0,
            }

            # Get strategy positions
            positions = [p for p in app_state.orchestrator.positions if p.strategy == name] if app_state.orchestrator else []

            # Calculate PnL
            realised_pnl = sum(p.realized_pnl for p in positions)
            unrealised_pnl = sum(p.unrealized_pnl for p in positions if p.is_open)

            strategy_info['realised_pnl'] = round(realised_pnl, 2)
            strategy_info['unrealised_pnl'] = round(unrealised_pnl, 2)

            # Get metrics from strategy if available
            if hasattr(strategy, 'get_performance_metrics'):
                metrics = strategy.get_performance_metrics(lookback_days=lookback_days)
                strategy_info.update(metrics)

            # Get allocation from allocator if available
            allocator = None
            if 'StrategyAllocator' in app_state.strategies:
                allocator = app_state.strategies['StrategyAllocator']
            elif app_state.orchestrator and hasattr(app_state.orchestrator, 'strategy_allocator'):
                allocator = app_state.orchestrator.strategy_allocator

            if allocator and hasattr(allocator, 'get_current_allocations'):
                allocations = allocator.get_current_allocations()
                strategy_info['current_allocation_pct'] = allocations.get(name, 0.0)

            strategies_data.append(strategy_info)

        return {
            "date": date.today().isoformat(),
            "strategies": strategies_data,
        }
    except Exception as e:
        logger.error(f"Error getting strategy summary: {e}")
        return {
            "date": date.today().isoformat(),
            "strategies": [],
            "error": str(e)
        }


@router.get("/regime/current")
async def get_current_regime():
    """
    Get current R1 regime classification for each underlying.

    Returns regime (LOW/MEDIUM/HIGH), IV rank, ATR%, RV/IV ratio.
    Used by MCP `get_event_and_regime_context` tool.
    """
    from apps.api.main import app_state

    if not app_state.strategies:
        return {
            "underlyings": {},
            "note": "No strategies loaded"
        }

    try:
        # Get R1 regime engine
        r1_strategy = app_state.strategies.get("RegimeVolEngine")

        if not r1_strategy:
            return {
                "underlyings": {},
                "note": "R1 RegimeVolEngine not enabled"
            }

        # Get current regime for each underlying
        underlyings = {}

        if hasattr(r1_strategy, 'get_current_regimes'):
            regime_data = r1_strategy.get_current_regimes()

            for symbol, data in regime_data.items():
                underlyings[symbol] = {
                    "regime": data.get("regime", "UNKNOWN"),
                    "iv_rank": round(data.get("iv_rank", 0.0), 2),
                    "atr_pct": round(data.get("atr_pct", 0.0), 2),
                    "rv_iv": round(data.get("rv_iv", 0.0), 2),
                }

        return {
            "underlyings": underlyings
        }
    except Exception as e:
        logger.error(f"Error getting current regime: {e}")
        return {
            "underlyings": {},
            "error": str(e)
        }


@router.get("/events/today")
async def get_events_today():
    """
    Get E1 event classification for today.

    Returns event day type (NORMAL/PRE_EVENT/EVENT_DAY/POST_EVENT),
    event name, and severity score.

    Used by MCP `get_event_and_regime_context` tool.
    """
    from apps.api.main import app_state

    if not app_state.event_engine:
        return {
            "underlyings": {},
            "note": "E1 Event Vol Engine not enabled"
        }

    try:
        # Get today's event classification
        if hasattr(app_state.event_engine, 'get_today_classification'):
            event_data = app_state.event_engine.get_today_classification()

            underlyings = {}
            for symbol, data in event_data.items():
                underlyings[symbol] = {
                    "day_type": data.get("day_type", "NORMAL"),
                    "name": data.get("event_name"),
                    "severity": round(data.get("severity", 0.0), 2),
                }

            return {
                "underlyings": underlyings
            }

        return {
            "underlyings": {},
            "note": "Event engine does not support get_today_classification"
        }
    except Exception as e:
        logger.error(f"Error getting events today: {e}")
        return {
            "underlyings": {},
            "error": str(e)
        }


@router.get("/report/today")
async def get_today_report():
    """
    Get today's trading report (same format as generate_daily_report.py).

    This is a convenience endpoint that returns the same JSON
    that scripts/generate_daily_report.py would produce.

    Used by MCP for getting comprehensive daily context.
    """
    from pathlib import Path
    import json

    try:
        # Check if today's report exists
        today_str = date.today().strftime("%Y%m%d")
        report_path = Path(f"reports/daily/daily_report_{today_str}.json")

        if report_path.exists():
            with open(report_path) as f:
                return json.load(f)

        # If no file exists, generate on the fly
        # TODO: Import and call generate_daily_report logic

        return {
            "date": date.today().isoformat(),
            "note": "Daily report not yet generated",
            "strategies": [],
            "portfolio": {},
            "risk": {}
        }
    except Exception as e:
        logger.error(f"Error getting today's report: {e}")
        raise HTTPException(status_code=500, detail=str(e))
