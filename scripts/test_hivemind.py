#!/usr/bin/env python3
"""
HiveMind Test Script - Level 7
===============================

Test script to demonstrate The Council of Seven in action.
"""

import sys
import os
import logging
from dotenv import load_dotenv

sys.path.append(os.getcwd())

from packages.core.hivemind.swarm import HiveMindSwarm

logging.basicConfig(level=logging.INFO, format='%(message)s')


def get_mock_live_state():
    """
    In production, this fetches real data from Redis/Orchestrator.
    
    Returns:
        Dictionary with mock trading state
    """
    return {
        "vix": 15.5,
        "trend": "UP",
        "events": "None",
        "pnl": -0.5,  # Losing day
        "margin_used": 45,
        "net_delta": 120,  # High delta exposure
        "strategy_metrics": {
            "trend_credit_spread": {"win_rate": 0.4, "pnl": -1000},
            "intraday_short_strangle": {"win_rate": 0.8, "pnl": 2000}
        },
        "avg_slippage": 2.0,
        "chase_savings": 1500,
        "portfolio_risk": {
            "daily_pnl": -5000.0,
            "portfolio_heat_pct": 1.2,
            "net_liquid": 1000000.0,
            "margin_utilization_pct": 45.0
        },
        "execution_stats": {
            "avg_slippage": 2.0,
            "chase_savings": 1500,
            "avg_slippage_bps": 2.0,
            "avg_limit_chase_savings_bps": 1.5
        }
    }


def main():
    """Main test function"""
    load_dotenv()
    print("🔮 SUMMONING THE HIVEMIND (LEVEL 7 INTELLIGENCE)")
    print("=" * 50)
    
    hive = HiveMindSwarm("configs/kite_day1_live.yaml")
    
    # Run the meeting
    verdict = hive.run_council_meeting(get_mock_live_state())
    
    print("=" * 50)
    print("🏛️  FINAL DECREE:")
    import json
    print(json.dumps(verdict, indent=2))


if __name__ == "__main__":
    main()





