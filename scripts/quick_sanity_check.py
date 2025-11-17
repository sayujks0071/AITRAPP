#!/usr/bin/env python3
"""
Quick sanity check script to query key metrics for observation.

Usage:
    python3 scripts/quick_sanity_check.py

This queries Prometheus for the key metrics mentioned in OBSERVATION_CHECKLIST.md
to help you quickly verify each component is behaving as expected.
"""

import os
import sys
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
API_URL = os.getenv("API_URL", "http://localhost:8000")


def query_prometheus(query: str) -> Optional[Dict[str, Any]]:
    """Query Prometheus for a metric."""
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        if data["status"] == "success" and data["data"]["result"]:
            return data["data"]["result"][0]
        return None
    except Exception as e:
        print(f"⚠️  Error querying Prometheus: {e}")
        return None


def get_latest_value(metric_name: str, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
    """Get the latest value of a metric."""
    label_str = ""
    if labels:
        label_parts = [f'{k}="{v}"' for k, v in labels.items()]
        label_str = "{" + ",".join(label_parts) + "}"
    
    query = f"{metric_name}{label_str}"
    result = query_prometheus(query)
    if result:
        return float(result["value"][1])
    return None


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def check_r1():
    """Check R1 Regime Engine metrics."""
    print_section("R1 — Regime Engine")
    
    for underlying in ["NIFTY", "BANKNIFTY"]:
        regime_code = get_latest_value("algo_vol_regime_code", {"underlying": underlying})
        iv_rank = get_latest_value("algo_vol_iv_rank", {"underlying": underlying})
        atr_pct = get_latest_value("algo_vol_atr_pct", {"underlying": underlying})
        rv_iv = get_latest_value("algo_vol_rv_iv_ratio", {"underlying": underlying})
        vix_rank = get_latest_value("algo_vol_vix_rank", {"underlying": underlying})
        
        regime_map = {
            0: "UNKNOWN",
            1: "LOW_MEAN_REVERT",
            2: "MEDIUM_TREND",
            3: "HIGH_EVENT",
            4: "CHAOTIC",
        }
        regime_name = regime_map.get(int(regime_code) if regime_code else 0, "UNKNOWN")
        
        print(f"\n{underlying}:")
        print(f"  Regime: {regime_name} (code: {regime_code})")
        print(f"  IV Rank: {iv_rank:.2f}" if iv_rank else "  IV Rank: N/A")
        print(f"  ATR%: {atr_pct:.2f}" if atr_pct else "  ATR%: N/A")
        print(f"  RV/IV: {rv_iv:.2f}" if rv_iv else "  RV/IV: N/A")
        print(f"  VIX Rank: {vix_rank:.2f}" if vix_rank else "  VIX Rank: N/A")


def check_g1():
    """Check G1 Gamma Scalper metrics."""
    print_section("G1 — Gamma Scalper")
    
    for underlying in ["NIFTY", "BANKNIFTY"]:
        abs_delta = get_latest_value("gamma_scalper_abs_delta", {"underlying": underlying})
        rebalances = get_latest_value("gamma_scalper_rebalances", {"underlying": underlying})
        books_opened = get_latest_value("gamma_scalper_books_opened", {"underlying": underlying})
        books_closed = get_latest_value("gamma_scalper_books_closed", {"underlying": underlying})
        
        print(f"\n{underlying}:")
        print(f"  |Δ|: {abs_delta:.2f}" if abs_delta else "  |Δ|: N/A")
        print(f"  Rebalances: {rebalances:.0f}" if rebalances else "  Rebalances: N/A")
        print(f"  Books Opened: {books_opened:.0f}" if books_opened else "  Books Opened: N/A")
        print(f"  Books Closed: {books_closed:.0f}" if books_closed else "  Books Closed: N/A")


def check_t1():
    """Check T1 Calendar Arb metrics."""
    print_section("T1 — Calendar Arb")
    
    for underlying in ["NIFTY", "BANKNIFTY"]:
        term_ratio = get_latest_value("calendar_arb_term_ratio", {"underlying": underlying})
        term_spread = get_latest_value("calendar_arb_term_spread", {"underlying": underlying})
        books_opened = get_latest_value("calendar_arb_books_opened", {"underlying": underlying})
        books_closed = get_latest_value("calendar_arb_books_closed", {"underlying": underlying})
        
        print(f"\n{underlying}:")
        print(f"  Term Ratio: {term_ratio:.3f}" if term_ratio else "  Term Ratio: N/A")
        print(f"  Term Spread: {term_spread:.2f}" if term_spread else "  Term Spread: N/A")
        print(f"  Books Opened: {books_opened:.0f}" if books_opened else "  Books Opened: N/A")
        print(f"  Books Closed: {books_closed:.0f}" if books_closed else "  Books Closed: N/A")


def check_d1():
    """Check D1 Dispersion Arb metrics."""
    print_section("D1 — Dispersion Arb")
    
    pairs = [
        ("NIFTY", "BANKNIFTY"),
        ("NIFTY", "FINNIFTY"),
        ("NIFTY", "MIDCAPNIFTY"),
    ]
    
    for parent, sector in pairs:
        vol_ratio = get_latest_value(
            "dispersion_arb_vol_ratio",
            {"parent": parent, "sector": sector}
        )
        corr = get_latest_value(
            "dispersion_arb_corr",
            {"parent": parent, "sector": sector}
        )
        iv_ratio = get_latest_value(
            "dispersion_arb_iv_ratio",
            {"parent": parent, "sector": sector}
        )
        books_opened = get_latest_value(
            "dispersion_arb_books_opened",
            {"parent": parent, "sector": sector}
        )
        
        print(f"\n{parent} vs {sector}:")
        print(f"  Vol Ratio: {vol_ratio:.3f}" if vol_ratio else "  Vol Ratio: N/A")
        print(f"  Correlation: {corr:.3f}" if corr else "  Correlation: N/A")
        print(f"  IV Ratio: {iv_ratio:.3f}" if iv_ratio else "  IV Ratio: N/A")
        print(f"  Books Opened: {books_opened:.0f}" if books_opened else "  Books Opened: N/A")


def check_allocator():
    """Check Allocator metrics."""
    print_section("Allocator")
    
    strategies = ["G1", "T1", "D1"]
    
    for strategy in strategies:
        final_weight = get_latest_value("allocator_final_weight", {"strategy": strategy})
        max_capital = get_latest_value("allocator_max_capital_pct", {"strategy": strategy})
        
        print(f"\n{strategy}:")
        print(f"  Final Weight: {final_weight:.3f}" if final_weight else "  Final Weight: N/A")
        print(f"  Max Capital %: {max_capital:.1f}%" if max_capital else "  Max Capital %: N/A")


def check_h1():
    """Check H1 Tail Short Vol Overlay metrics."""
    print_section("H1 — Tail Short Vol Overlay")
    
    for underlying in ["NIFTY", "BANKNIFTY"]:
        short_notional = get_latest_value("tail_short_vol_short_notional", {"underlying": underlying})
        tail_notional = get_latest_value("tail_short_vol_tail_notional", {"underlying": underlying})
        coverage = get_latest_value("tail_short_vol_coverage_pct", {"underlying": underlying})
        adjustments = get_latest_value("tail_short_vol_adjustments", {"underlying": underlying})
        
        print(f"\n{underlying}:")
        print(f"  Short Notional: {short_notional:.0f}" if short_notional else "  Short Notional: N/A")
        print(f"  Tail Notional: {tail_notional:.0f}" if tail_notional else "  Tail Notional: N/A")
        print(f"  Coverage %: {coverage:.1f}%" if coverage else "  Coverage %: N/A")
        print(f"  Adjustments: {adjustments:.0f}" if adjustments else "  Adjustments: N/A")


def check_e1():
    """Check E1 Event Engine metrics."""
    print_section("E1 — Event Engine")
    
    for underlying in ["NIFTY", "BANKNIFTY"]:
        # Try to get day type (may need to query differently)
        # This is a simplified check
        print(f"\n{underlying}:")
        print(f"  (Check Grafana for event_vol_engine_day_type and severity)")


def main():
    """Run all sanity checks."""
    print(f"\n🔍 Quick Sanity Check — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Prometheus: {PROMETHEUS_URL}")
    print(f"API: {API_URL}")
    
    try:
        check_r1()
        check_g1()
        check_t1()
        check_d1()
        check_allocator()
        check_h1()
        check_e1()
        
        print("\n" + "="*60)
        print("✅ Sanity check complete!")
        print("\n📋 See docs/OBSERVATION_CHECKLIST.md for pass/fail criteria")
        print("="*60 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

