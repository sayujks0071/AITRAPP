#!/usr/bin/env python3
"""Generate daily trading report from metrics and logs"""
import sys
import requests
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

API_BASE = "http://localhost:8000"
REPORT_DIR = Path("reports/daily")


def fetch_metrics() -> str:
    """Fetch Prometheus metrics"""
    try:
        response = requests.get(f"{API_BASE}/metrics", timeout=5)
        if response.status_code == 200:
            return response.text
        return ""
    except Exception as e:
        print(f"Error fetching metrics: {e}")
        return ""


def parse_metric(metrics_text: str, metric_name: str, labels: Optional[Dict[str, str]] = None) -> float:
    """Parse a metric value from Prometheus text format"""
    lines = metrics_text.split('\n')
    for line in lines:
        if line.startswith(metric_name):
            # Simple parsing - would use proper Prometheus parser in production
            if ' ' in line:
                try:
                    value = float(line.split()[-1])
                    return value
                except:
                    pass
    return 0.0


def get_regime_timeline(metrics_text: str, underlying: str = "NIFTY") -> List[Dict[str, str]]:
    """Get regime timeline (simplified - would use proper time series in production)"""
    # In production, would query Prometheus for time series
    current_regime = parse_metric(metrics_text, f'algo_vol_regime_code{{underlying="{underlying}"}}')
    
    regime_map = {
        0: "UNKNOWN",
        1: "LOW_MEAN_REVERT",
        2: "MEDIUM_TREND",
        3: "HIGH_EVENT",
        4: "CHAOTIC"
    }
    
    return [{
        "time": datetime.now().strftime("%H:%M"),
        "regime": regime_map.get(int(current_regime), "UNKNOWN")
    }]


def generate_strategy_report(metrics_text: str, strategy_name: str) -> Dict[str, any]:
    """Generate report for a strategy"""
    books_opened = parse_metric(metrics_text, f'{strategy_name}_books_opened')
    books_closed = parse_metric(metrics_text, f'{strategy_name}_books_closed')
    pnl_pct = parse_metric(metrics_text, f'{strategy_name}_pnl_pct')
    
    # In production, would get from position store
    return {
        "trades": int(books_opened),
        "wins": 0,  # Would calculate from position store
        "losses": 0,  # Would calculate from position store
        "pnl": 0.0,  # Would get from position store
        "pnl_pct": pnl_pct,
        "hit_rate": 0.0,  # Would calculate
        "max_drawdown": 0.0,  # Would calculate
    }


def generate_allocator_report(metrics_text: str) -> Dict[str, Dict[str, float]]:
    """Generate allocator report"""
    allocations = {}
    
    # In production, would parse all allocator metrics
    # For now, return placeholder
    strategies = [
        "expiry_short_strangle",
        "gamma_scalper",
        "calendar_arb",
        "dispersion_arb",
    ]
    
    for strategy in strategies:
        raw_score = parse_metric(metrics_text, f'allocator_raw_score{{strategy="{strategy}"}}')
        final_weight = parse_metric(metrics_text, f'allocator_final_weight{{strategy="{strategy}"}}')
        max_cap = parse_metric(metrics_text, f'allocator_max_capital_pct{{strategy="{strategy}"}}')
        enabled = parse_metric(metrics_text, f'allocator_enabled{{strategy="{strategy}"}}')
        
        if raw_score > 0 or final_weight > 0:
            allocations[strategy] = {
                "raw_score": raw_score,
                "final_weight": final_weight,
                "max_capital_pct": max_cap,
                "enabled": bool(enabled > 0.5),
            }
    
    return allocations


def generate_tail_coverage_report(metrics_text: str) -> Dict[str, Dict[str, float]]:
    """Generate tail coverage report"""
    coverage = {}
    
    underlyings = ["NIFTY", "BANKNIFTY"]
    for underlying in underlyings:
        short_notional = parse_metric(metrics_text, f'tail_short_vol_short_notional{{underlying="{underlying}"}}')
        tail_notional = parse_metric(metrics_text, f'tail_short_vol_tail_notional{{underlying="{underlying}"}}')
        coverage_pct = parse_metric(metrics_text, f'tail_short_vol_coverage_pct{{underlying="{underlying}"}}')
        adjustments = parse_metric(metrics_text, f'tail_short_vol_adjustments{{underlying="{underlying}"}}')
        
        if short_notional > 0 or tail_notional > 0:
            coverage[underlying] = {
                "avg_coverage_pct": coverage_pct,
                "min_coverage_pct": coverage_pct,  # Would track min/max in production
                "max_coverage_pct": coverage_pct,
                "short_notional": short_notional,
                "tail_notional": tail_notional,
                "adjustments": int(adjustments),
            }
    
    return coverage


def generate_daily_report() -> Dict[str, any]:
    """Generate complete daily report"""
    print("Generating daily report...")
    
    metrics_text = fetch_metrics()
    if not metrics_text:
        print("⚠️  Could not fetch metrics")
        return {}
    
    date = datetime.now().strftime("%Y-%m-%d")
    
    report = {
        "date": date,
        "timestamp": datetime.now().isoformat(),
        "strategies": {},
        "allocator": generate_allocator_report(metrics_text),
        "tail_coverage": generate_tail_coverage_report(metrics_text),
        "regime_timeline": get_regime_timeline(metrics_text),
    }
    
    # Add strategy reports
    strategies = ["gamma_scalper", "calendar_arb", "dispersion_arb"]
    for strategy in strategies:
        report["strategies"][strategy] = generate_strategy_report(metrics_text, strategy)
    
    return report


def save_report(report: Dict[str, any]) -> None:
    """Save report to file"""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    date = report.get("date", datetime.now().strftime("%Y-%m-%d"))
    json_path = REPORT_DIR / f"{date}_report.json"
    md_path = REPORT_DIR / f"{date}_report.md"
    
    # Save JSON
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)
    
    # Save Markdown
    with open(md_path, "w") as f:
        f.write(f"# Daily Trading Report - {date}\n\n")
        f.write(f"Generated: {report.get('timestamp', '')}\n\n")
        
        f.write("## Strategies\n\n")
        for strategy, data in report.get("strategies", {}).items():
            f.write(f"### {strategy}\n")
            f.write(f"- Trades: {data.get('trades', 0)}\n")
            f.write(f"- PnL %: {data.get('pnl_pct', 0):.2f}%\n")
            f.write(f"- Hit Rate: {data.get('hit_rate', 0):.2f}\n\n")
        
        f.write("## Allocator\n\n")
        for strategy, data in report.get("allocator", {}).items():
            f.write(f"### {strategy}\n")
            f.write(f"- Score: {data.get('raw_score', 0):.2f}\n")
            f.write(f"- Weight: {data.get('final_weight', 0):.2f}\n")
            f.write(f"- Max Cap: {data.get('max_capital_pct', 0)*100:.1f}%\n")
            f.write(f"- Enabled: {data.get('enabled', False)}\n\n")
        
        f.write("## Tail Coverage\n\n")
        for underlying, data in report.get("tail_coverage", {}).items():
            f.write(f"### {underlying}\n")
            f.write(f"- Coverage: {data.get('avg_coverage_pct', 0):.2f}%\n")
            f.write(f"- Short Notional: {data.get('short_notional', 0):.0f}\n")
            f.write(f"- Tail Notional: {data.get('tail_notional', 0):.0f}\n")
            f.write(f"- Adjustments: {data.get('adjustments', 0)}\n\n")
        
        f.write("## Regime Timeline\n\n")
        for entry in report.get("regime_timeline", []):
            f.write(f"- {entry.get('time')}: {entry.get('regime')}\n")
    
    print(f"✅ Report saved: {json_path}")
    print(f"✅ Report saved: {md_path}")


def main():
    """Generate and save daily report"""
    report = generate_daily_report()
    if report:
        save_report(report)
        return 0
    else:
        print("❌ Failed to generate report")
        return 1


if __name__ == "__main__":
    sys.exit(main())


