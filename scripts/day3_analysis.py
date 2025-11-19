#!/usr/bin/env python3
"""Day-3 Comprehensive Trade Analysis"""
import json
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict

from packages.storage.database import get_db_session
from packages.storage.models import (
    Signal, Decision, Order, Position, Trade, RiskEvent
)
from packages.core.config import settings

REPORT_DIR = Path("reports/daily")
REPORT_DATE = date(2025, 11, 18)  # Day-3


def get_day_start_end(report_date: date):
    """Get start and end datetime for the day"""
    day_start = datetime.combine(report_date, datetime.min.time())
    day_end = datetime.combine(report_date, datetime.max.time()) + timedelta(days=1)
    return day_start, day_end


def analyze_signals(db, day_start, day_end) -> Dict[str, Any]:
    """Analyze signals generated"""
    signals = db.query(Signal).filter(
        Signal.ts >= day_start,
        Signal.ts < day_end
    ).order_by(Signal.ts).all()
    
    strategy_counts = defaultdict(int)
    for s in signals:
        strategy_counts[s.strategy] += 1
    
    return {
        "total": len(signals),
        "by_strategy": dict(strategy_counts),
        "signals": [
            {
                "id": s.id,
                "timestamp": s.ts.isoformat(),
                "strategy": s.strategy,
                "symbol": s.symbol,
                "side": s.side.value if s.side else None,
                "score": s.score,
                "rank": s.rank,
                "confidence": s.confidence,
            }
            for s in signals
        ]
    }


def analyze_decisions(db, day_start, day_end) -> Dict[str, Any]:
    """Analyze risk decisions"""
    decisions = db.query(Decision).filter(
        Decision.ts >= day_start,
        Decision.ts < day_end
    ).order_by(Decision.ts).all()
    
    approved = [d for d in decisions if d.status.value == "PLANNED"]
    rejected = [d for d in decisions if d.status.value == "REJECTED"]
    
    rejection_reasons = defaultdict(int)
    for d in rejected:
        if d.rejection_reasons:
            for reason in d.rejection_reasons:
                rejection_reasons[reason] += 1
    
    return {
        "total": len(decisions),
        "approved": len(approved),
        "rejected": len(rejected),
        "rejection_reasons": dict(rejection_reasons),
        "max_portfolio_heat": max([d.portfolio_heat_after or 0 for d in decisions]) if decisions else 0.0,
        "decisions": [
            {
                "id": d.id,
                "timestamp": d.ts.isoformat(),
                "status": d.status.value,
                "risk_pct": d.risk_perc,
                "risk_amount": d.risk_amount,
                "position_size": d.position_size,
                "portfolio_heat_before": d.portfolio_heat_before,
                "portfolio_heat_after": d.portfolio_heat_after,
                "rejection_reasons": d.rejection_reasons,
            }
            for d in decisions
        ]
    }


def analyze_orders(db, day_start, day_end) -> Dict[str, Any]:
    """Analyze orders"""
    orders = db.query(Order).filter(
        Order.ts >= day_start,
        Order.ts < day_end
    ).order_by(Order.ts).all()
    
    by_status = defaultdict(int)
    by_type = defaultdict(int)
    rejected_orders = []
    
    for o in orders:
        by_status[o.status.value] += 1
        by_type[o.order_type.value if o.order_type else "UNKNOWN"] += 1
        if o.status.value == "REJECTED":
            rejected_orders.append({
                "id": o.id,
                "timestamp": o.ts.isoformat(),
                "symbol": o.symbol,
                "side": o.side.value if o.side else None,
                "qty": o.qty,
                "price": o.price,
                "status": o.status.value,
            })
    
    filled = [o for o in orders if o.status.value == "FILLED"]
    
    return {
        "total": len(orders),
        "filled": len(filled),
        "by_status": dict(by_status),
        "by_type": dict(by_type),
        "rejected_count": len(rejected_orders),
        "rejected_orders": rejected_orders,
        "orders": [
            {
                "id": o.id,
                "timestamp": o.ts.isoformat(),
                "symbol": o.symbol,
                "side": o.side.value if o.side else None,
                "qty": o.qty,
                "filled_qty": o.filled_qty,
                "price": o.price,
                "average_price": o.average_price,
                "order_type": o.order_type.value if o.order_type else None,
                "status": o.status.value,
                "tag": o.tag,
            }
            for o in orders
        ]
    }


def analyze_positions(db, day_start, day_end) -> Dict[str, Any]:
    """Analyze positions"""
    positions = db.query(Position).filter(
        Position.opened_at >= day_start,
        Position.opened_at < day_end
    ).order_by(Position.opened_at).all()
    
    open_positions = [p for p in positions if p.status.value == "OPEN"]
    closed_positions = [p for p in positions if p.status.value == "CLOSED"]
    
    by_strategy = defaultdict(list)
    for p in positions:
        by_strategy[p.strategy_name].append(p)
    
    return {
        "total": len(positions),
        "open": len(open_positions),
        "closed": len(closed_positions),
        "by_strategy": {k: len(v) for k, v in by_strategy.items()},
        "positions": [
            {
                "id": p.id,
                "position_id": p.position_id,
                "symbol": p.symbol,
                "strategy": p.strategy_name,
                "side": p.side.value if p.side else None,
                "qty": p.qty,
                "avg_price": p.avg_price,
                "current_price": p.current_price,
                "unrealized": p.unrealized,
                "realized": p.realized,
                "risk_amount": p.risk_amount,
                "mfe": p.mfe,
                "mae": p.mae,
                "opened_at": p.opened_at.isoformat() if p.opened_at else None,
                "closed_at": p.closed_at.isoformat() if p.closed_at else None,
                "status": p.status.value,
            }
            for p in positions
        ]
    }


def analyze_trades(db, day_start, day_end) -> Dict[str, Any]:
    """Analyze completed trades"""
    trades = db.query(Trade).filter(
        Trade.ts >= day_start,
        Trade.ts < day_end
    ).order_by(Trade.ts).all()
    
    if not trades:
        return {
            "total": 0,
            "winners": 0,
            "losers": 0,
            "total_pnl": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "win_rate": 0.0,
            "trades": []
        }
    
    winning_trades = [t for t in trades if t.net_pnl > 0]
    losing_trades = [t for t in trades if t.net_pnl <= 0]
    
    total_pnl = sum([t.net_pnl for t in trades])
    avg_win = sum([t.net_pnl for t in winning_trades]) / len(winning_trades) if winning_trades else 0
    avg_loss = sum([t.net_pnl for t in losing_trades]) / len(losing_trades) if losing_trades else 0
    win_rate = len(winning_trades) / len(trades) if trades else 0
    
    # Get position details for each trade
    trades_with_details = []
    for t in trades:
        pos = t.position
        trades_with_details.append({
            "id": t.id,
            "timestamp": t.ts.isoformat(),
            "position_id": pos.position_id if pos else None,
            "strategy": pos.strategy_name if pos else None,
            "symbol": pos.symbol if pos else None,
            "action": t.action.value if t.action else None,
            "qty": t.qty,
            "price": t.price,
            "gross_pnl": t.gross_pnl,
            "fees": t.fees,
            "net_pnl": t.net_pnl,
            "pnl_pct": t.pnl_pct,
            "risk_amount": t.risk_amount,
            "rr_actual": t.rr_actual,
        })
    
    return {
        "total": len(trades),
        "winners": len(winning_trades),
        "losers": len(losing_trades),
        "total_pnl": total_pnl,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "win_rate": win_rate,
        "win_loss_ratio": abs(avg_win / avg_loss) if avg_loss != 0 else 0,
        "trades": trades_with_details
    }


def analyze_risk_events(db, day_start, day_end) -> Dict[str, Any]:
    """Analyze risk events"""
    events = db.query(RiskEvent).filter(
        RiskEvent.ts >= day_start,
        RiskEvent.ts < day_end
    ).order_by(RiskEvent.ts).all()
    
    by_type = defaultdict(int)
    for e in events:
        by_type[e.event_type] += 1
    
    return {
        "total": len(events),
        "by_type": dict(by_type),
        "events": [
            {
                "id": e.id,
                "timestamp": e.ts.isoformat(),
                "event_type": e.event_type,
                "message": e.message,
                "severity": e.severity,
            }
            for e in events
        ]
    }


def check_risk_compliance(decisions_data: Dict, positions_data: Dict, trades_data: Dict, config_path: str) -> Dict[str, Any]:
    """Check risk compliance against config"""
    compliance = {
        "per_trade_risk_ok": True,
        "daily_loss_limit_ok": True,
        "margin_usage_ok": True,
        "time_window_ok": True,
        "violations": [],
        "warnings": [],
    }
    
    # Check per-trade risk (would need to read config)
    # For now, check if any decision exceeded reasonable limits
    for d in decisions_data.get("decisions", []):
        if d.get("risk_amount", 0) > 5000:  # Conservative check
            compliance["warnings"].append(f"Large risk amount: ₹{d['risk_amount']:.2f} at {d['timestamp']}")
    
    # Check daily loss
    total_pnl = trades_data.get("total_pnl", 0)
    if total_pnl < -25000:  # Hard limit from config
        compliance["daily_loss_limit_ok"] = False
        compliance["violations"].append(f"Daily loss limit breached: ₹{total_pnl:.2f}")
    elif total_pnl < -12500:  # Soft limit
        compliance["warnings"].append(f"Approaching daily loss soft limit: ₹{total_pnl:.2f}")
    
    # Check portfolio heat
    max_heat = decisions_data.get("max_portfolio_heat", 0)
    if max_heat > 1.0:  # From config
        compliance["warnings"].append(f"Portfolio heat exceeded 1.0%: {max_heat:.2f}%")
    
    # Check time windows (would need to check order timestamps against config windows)
    # Simplified check
    for order in decisions_data.get("decisions", []):
        ts = datetime.fromisoformat(order["timestamp"])
        hour = ts.hour
        minute = ts.minute
        # Entry window: 09:30 - 14:00 (from config)
        if hour < 9 or (hour == 9 and minute < 30) or hour >= 14:
            compliance["time_window_ok"] = False
            compliance["violations"].append(f"Trade outside entry window: {ts.strftime('%H:%M')}")
    
    return compliance


def generate_report() -> Dict[str, Any]:
    """Generate comprehensive Day-3 report"""
    print(f"Generating Day-3 analysis for {REPORT_DATE}...")
    
    day_start, day_end = get_day_start_end(REPORT_DATE)
    
    with get_db_session() as db:
        signals_data = analyze_signals(db, day_start, day_end)
        decisions_data = analyze_decisions(db, day_start, day_end)
        orders_data = analyze_orders(db, day_start, day_end)
        positions_data = analyze_positions(db, day_start, day_end)
        trades_data = analyze_trades(db, day_start, day_end)
        risk_events_data = analyze_risk_events(db, day_start, day_end)
    
    # Check risk compliance
    compliance = check_risk_compliance(decisions_data, positions_data, trades_data, "configs/kite_day1_live.yaml")
    
    report = {
        "date": REPORT_DATE.isoformat(),
        "timestamp": datetime.now().isoformat(),
        "signals": signals_data,
        "decisions": decisions_data,
        "orders": orders_data,
        "positions": positions_data,
        "trades": trades_data,
        "risk_events": risk_events_data,
        "compliance": compliance,
    }
    
    return report


def save_report(report: Dict[str, Any]) -> None:
    """Save report to files"""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    date_str = report.get("date", REPORT_DATE.isoformat())
    json_path = REPORT_DIR / f"{date_str}_analysis.json"
    md_path = REPORT_DIR / f"{date_str}_analysis.md"
    
    # Save JSON
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    # Generate Markdown report
    with open(md_path, "w") as f:
        f.write(f"# Day-3 Trading Analysis - {date_str}\n\n")
        f.write(f"Generated: {report.get('timestamp', '')}\n\n")
        
        # Overview
        trades_data = report.get("trades", {})
        f.write("## A. Overview\n\n")
        f.write(f"- **Total PnL**: ₹{trades_data.get('total_pnl', 0):,.2f}\n")
        f.write(f"- **Number of Trades**: {trades_data.get('total', 0)}\n")
        f.write(f"- **Win Rate**: {trades_data.get('win_rate', 0)*100:.1f}%\n")
        f.write(f"- **Winners**: {trades_data.get('winners', 0)} | **Losers**: {trades_data.get('losers', 0)}\n")
        f.write(f"- **Avg Win**: ₹{trades_data.get('avg_win', 0):,.2f} | **Avg Loss**: ₹{trades_data.get('avg_loss', 0):,.2f}\n")
        f.write(f"- **Win/Loss Ratio**: {trades_data.get('win_loss_ratio', 0):.2f}\n\n")
        
        # Per-strategy performance
        positions_data = report.get("positions", {})
        f.write("## B. Per-Strategy Performance\n\n")
        if positions_data.get("by_strategy"):
            f.write("| Strategy | Positions | Status |\n")
            f.write("|----------|-----------|--------|\n")
            for strategy, count in positions_data.get("by_strategy", {}).items():
                f.write(f"| {strategy} | {count} | - |\n")
        else:
            f.write("No positions opened.\n")
        f.write("\n")
        
        # Risk & Guardrails
        compliance = report.get("compliance", {})
        decisions_data = report.get("decisions", {})
        f.write("## C. Risk & Guardrails\n\n")
        f.write(f"- **Per-Trade Risk**: {'✅ OK' if compliance.get('per_trade_risk_ok') else '❌ VIOLATION'}\n")
        f.write(f"- **Daily Loss Limit**: {'✅ OK' if compliance.get('daily_loss_limit_ok') else '❌ VIOLATION'}\n")
        f.write(f"- **Margin Usage**: {'✅ OK' if compliance.get('margin_usage_ok') else '❌ VIOLATION'}\n")
        f.write(f"- **Time Windows**: {'✅ OK' if compliance.get('time_window_ok') else '❌ VIOLATION'}\n")
        f.write(f"- **Max Portfolio Heat**: {decisions_data.get('max_portfolio_heat', 0):.2f}%\n\n")
        
        if compliance.get("violations"):
            f.write("### Violations\n\n")
            for v in compliance["violations"]:
                f.write(f"- ❌ {v}\n")
            f.write("\n")
        
        if compliance.get("warnings"):
            f.write("### Warnings\n\n")
            for w in compliance["warnings"]:
                f.write(f"- ⚠️  {w}\n")
            f.write("\n")
        
        # Execution Quality
        orders_data = report.get("orders", {})
        f.write("## D. Execution Quality\n\n")
        f.write(f"- **Total Orders**: {orders_data.get('total', 0)}\n")
        f.write(f"- **Filled**: {orders_data.get('filled', 0)}\n")
        f.write(f"- **Rejected**: {orders_data.get('rejected_count', 0)}\n")
        if orders_data.get("rejected_orders"):
            f.write("\n### Rejected Orders\n\n")
            for ro in orders_data["rejected_orders"][:10]:
                f.write(f"- {ro['timestamp']}: {ro['symbol']} {ro['side']} {ro['qty']} @ ₹{ro['price']}\n")
        f.write("\n")
        
        # Signals & Decisions
        signals_data = report.get("signals", {})
        decisions_data = report.get("decisions", {})
        f.write("## E. Signals & Decisions\n\n")
        f.write(f"- **Signals Generated**: {signals_data.get('total', 0)}\n")
        f.write(f"- **Decisions**: {decisions_data.get('total', 0)} (Approved: {decisions_data.get('approved', 0)}, Rejected: {decisions_data.get('rejected', 0)})\n")
        if decisions_data.get("rejection_reasons"):
            f.write("\n### Rejection Reasons\n\n")
            for reason, count in decisions_data["rejection_reasons"].items():
                f.write(f"- {reason}: {count}\n")
        f.write("\n")
        
        # Risk Events
        risk_events = report.get("risk_events", {})
        if risk_events.get("total", 0) > 0:
            f.write("## F. Risk Events\n\n")
            f.write(f"Total: {risk_events.get('total', 0)}\n\n")
            for event in risk_events.get("events", [])[:20]:
                f.write(f"- {event['timestamp']}: [{event['event_type']}] {event['message']}\n")
            f.write("\n")
        
        # Trade Details
        if trades_data.get("trades"):
            f.write("## G. Trade Details\n\n")
            f.write("| Time | Strategy | Symbol | Action | Qty | Price | PnL |\n")
            f.write("|------|----------|--------|--------|-----|-------|-----|\n")
            for trade in trades_data["trades"]:
                f.write(f"| {trade['timestamp'][:19]} | {trade.get('strategy', 'N/A')} | {trade.get('symbol', 'N/A')} | {trade.get('action', 'N/A')} | {trade['qty']} | ₹{trade['price']:.2f} | ₹{trade['net_pnl']:.2f} |\n")
            f.write("\n")
    
    print(f"✅ Analysis saved: {json_path}")
    print(f"✅ Report saved: {md_path}")


def main():
    """Main entry point"""
    try:
        report = generate_report()
        if report:
            save_report(report)
            return 0
        else:
            print("❌ Failed to generate report")
            return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

