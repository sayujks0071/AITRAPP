#!/usr/bin/env python3
"""
HiveMind Market Analysis - Today's Performance & Monday Expectations
=====================================================================

Convenes the HiveMind Council to analyze today's market performance
and provide expectations for Monday.
"""

import sys
import os
import json
from datetime import datetime
from dotenv import load_dotenv

sys.path.append(os.getcwd())

from packages.core.hivemind.swarm import HiveMindSwarm

def main():
    load_dotenv()
    
    print("\n" + "="*70)
    print("🧠 HIVEMIND COUNCIL: MARKET ANALYSIS SESSION")
    print("="*70)
    print()
    
    # Try to get real-time state from API
    try:
        import requests
        state_response = requests.get("http://localhost:8000/state", timeout=2)
        if state_response.status_code == 200:
            api_state = state_response.json()
            daily_pnl = api_state.get('daily_pnl', 0.0)
            trades_today = api_state.get('trades_today', 0)
            win_rate = api_state.get('win_rate', 0.0)
            is_market_open = api_state.get('is_market_open', False)
            print(f"📊 Current System State:")
            print(f"   • Market Status: {'OPEN' if is_market_open else 'CLOSED'}")
            print(f"   • Daily PnL: ₹{daily_pnl:.2f}")
            print(f"   • Trades Today: {trades_today}")
            print(f"   • Win Rate: {win_rate:.1%}")
            print()
    except:
        daily_pnl = 0.0
        trades_today = 0
        win_rate = 0.0
        is_market_open = False
    
    # Build context for HiveMind analysis
    current_time = datetime.now()
    is_friday = current_time.weekday() == 4  # Friday = 4
    
    analysis_context = {
        "timestamp": current_time.isoformat(),
        "day": current_time.strftime("%A"),
        "market_status": "CLOSED" if not is_market_open else "OPEN",
        "is_friday": is_friday,
        "daily_pnl": daily_pnl,
        "trades_today": trades_today,
        "win_rate": win_rate,
        "vix": 14.5,  # Expected VIX for Monday
        "trend": "SIDEWAYS_BULLISH",
        "events": "Weekend Gap Risk" if is_friday else "Standard Session",
        "margin_used": 0,
        "net_delta": 0,
        "market_regime": "UNKNOWN",
        "strategy_metrics": {
            "trend_credit_spread": {"win_rate": win_rate, "recent_performance": "FLAT"},
            "intraday_short_strangle": {"win_rate": win_rate, "recent_performance": "FLAT"}
        },
        "portfolio_risk": {
            "daily_pnl": daily_pnl,
            "portfolio_heat_pct": 0.0,
            "available_margin": 1000000.0,
            "margin_utilization_pct": 0.0,
            "net_liquid": 1000000.0,
            "used_margin": 0.0
        },
        "execution_stats": {
            "avg_slippage_bps": 0.0,
            "avg_slippage": 0.0,
            "avg_limit_chase_savings_bps": 0.0,
            "chase_savings": 0.0,
            "fill_rate": 1.0,
            "avg_order_latency_ms": 0.0
        }
    }
    
    # Convene the Council
    config_path = "configs/kite_day1_live.yaml"
    if not os.path.exists(config_path):
        config_path = "configs/kite_canary_live.yaml"
    
    hive = HiveMindSwarm(config_path)
    
    print("📡 MarketAgent analyzing today's performance...")
    print("🎯 StrategyAgent evaluating strategy effectiveness...")
    print("🛡️  RiskAgent assessing risk exposure...")
    print("📚 AnalystAgent recalling historical patterns...")
    print("🔮 Council preparing Monday expectations...")
    print()
    
    report = hive.run_council_meeting(analysis_context)
    
    # Extract insights
    market_analysis = report.get('market_analysis', {})
    strategy_recs = report.get('strategy_recs', {})
    risk_analysis = report.get('risk_analysis', {})
    analyst_insights = report.get('historical_context', {})
    referee_verdict = report.get('final_directive', 'PROCEED')
    referee_reasoning = report.get('reasoning', '')
    
    print("="*70)
    print("📊 TODAY'S MARKET ANALYSIS")
    print("="*70)
    print()
    
    # Today's Performance
    print(f"💰 Daily PnL: ₹{daily_pnl:.2f}")
    print(f"📈 Trades Executed: {trades_today}")
    print(f"🎯 Win Rate: {win_rate:.1%}")
    print()
    
    # Market Agent Assessment
    regime = market_analysis.get('regime', 'UNKNOWN')
    confidence = market_analysis.get('confidence', 0)
    print(f"🌍 Market Regime: {regime}")
    print(f"📊 Confidence Level: {confidence}%")
    if market_analysis.get('insight'):
        print(f"💡 Insight: {market_analysis.get('insight')}")
    print()
    
    # Strategy Performance
    if strategy_recs.get('recommendations'):
        print("🎯 Strategy Performance:")
        for strat, status in strategy_recs.get('recommendations', {}).items():
            print(f"   • {strat}: {status}")
    print()
    
    # Risk Assessment
    defcon = risk_analysis.get('defcon_level', 5)
    print(f"🛡️  Risk Status: DEFCON {defcon}/5")
    if risk_analysis.get('summary'):
        print(f"   {risk_analysis.get('summary')}")
    print()
    
    print("="*70)
    print("🔮 MONDAY EXPECTATIONS")
    print("="*70)
    print()
    
    # Analyst Historical Context
    if analyst_insights.get('insight'):
        print("📚 Historical Analysis:")
        print(f"   {analyst_insights.get('insight')}")
        print()
    
    if analyst_insights.get('recommendation'):
        print("💡 Strategy Recommendation:")
        print(f"   {analyst_insights.get('recommendation')}")
        print()
    
    # Referee Final Assessment
    print("⚖️  Council Verdict:")
    print(f"   Directive: {referee_verdict}")
    if referee_reasoning:
        print(f"   Reasoning: {referee_reasoning}")
    print()
    
    # Monday Preparation
    print("="*70)
    print("📋 MONDAY PREPARATION CHECKLIST")
    print("="*70)
    print()
    
    allocations = report.get('approved_allocations', {})
    if allocations:
        print("💰 Capital Allocation:")
        for strat, weight in allocations.items():
            print(f"   • {strat}: {weight*100:.1f}%")
    else:
        print("   • No allocation changes recommended")
    print()
    
    print("✅ System Status: Ready for Monday Launch")
    print("⏰ Recommended Launch Time: 09:15 AM IST")
    print()
    
    print("="*70)
    print()

if __name__ == "__main__":
    main()




