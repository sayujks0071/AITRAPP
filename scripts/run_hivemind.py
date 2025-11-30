#!/usr/bin/env python3
"""
HiveMind Swarm Runner - Level 7
================================

Convene The Council of Seven for real-time decision-making.

Usage:
    python3 scripts/run_hivemind.py
    python3 scripts/run_hivemind.py --live  # Connect to running orchestrator
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.core.hivemind.swarm import HiveMindSwarm
from packages.core.config import app_config, settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("hivemind_cli")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="HiveMind Swarm - Convene The Council of Seven"
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Connect to running orchestrator for live context"
    )
    parser.add_argument(
        "--memory-path",
        type=str,
        default="data/memory.json",
        help="Path to RAG memory JSON file"
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("🧠 HIVEMIND - THE COUNCIL OF SEVEN")
    logger.info("=" * 60)
    logger.info(f"📁 Memory: {args.memory_path}")
    logger.info(f"🔗 Live Mode: {args.live}")
    logger.info("")
    
    try:
        # Determine config path
        if hasattr(app_config, 'config_path'):
            config_path = str(app_config.config_path)
        elif settings.app_config_path:
            config_path = settings.app_config_path
        else:
            config_path = "configs/kite_day1_live.yaml"
        
        logger.info(f"📁 Config: {config_path}")
        
        # Initialize Strategic Memory Engine (Level 8) if available
        sme = None
        try:
            from packages.core.intelligence.sme import StrategicMemoryEngine
            sme = StrategicMemoryEngine()
            logger.info("✅ Strategic Memory Engine (SME) loaded - Level 8 active")
        except Exception as e:
            logger.warning(f"⚠️  Could not load SME: {e}")
        
        # Initialize HiveMind (with SME if available)
        swarm = HiveMindSwarm(config_path=config_path, sme=sme)
        
        # Get orchestrator if live mode
        orchestrator = None
        if args.live:
            try:
                # Try to import and get orchestrator from app state
                from apps.api.main import app_state
                orchestrator = app_state.orchestrator
                if not orchestrator:
                    logger.warning("⚠️  Orchestrator not available in app_state")
            except Exception as e:
                logger.warning(f"⚠️  Could not connect to orchestrator: {e}")
        
        # Build context
        if orchestrator:
            context = swarm._build_context(orchestrator)
        else:
            context = swarm._build_context()
        
        # Run council meeting
        verdict = swarm.run_council_meeting(context)
        
        # Format result for display
        agent_insights = verdict.get("agent_insights", {})
        result = {
            "binding_directive": verdict,
            "agent_insights": {
                "MarketAgent": agent_insights.get("market_analysis", {}),
                "StrategyAgent": agent_insights.get("strategy_recs", {}),
                "RiskAgent": agent_insights.get("risk_analysis", {}),
                "ExecutionAgent": agent_insights.get("exec_analysis", {}),
                "AnalystAgent": agent_insights.get("historical_context", {}),
                "AllocatorAgent": agent_insights.get("allocation_proposal", {}),
                "RefereeAgent": verdict
            }
        }
        
        # Display results
        logger.info("")
        logger.info("=" * 60)
        logger.info("📊 COUNCIL DECISION")
        logger.info("=" * 60)
        
        directive = result["binding_directive"]
        logger.info(f"Directive: {directive.get('final_directive', directive.get('directive', 'N/A'))}")
        logger.info(f"Override: {directive.get('global_override', 'N/A')}")
        logger.info(f"Confidence: {directive.get('confidence', 0.0):.1%}")
        logger.info("")
        logger.info("Details:")
        logger.info(f"  {directive.get('directive_details', directive.get('reasoning', 'N/A'))}")
        logger.info("")
        logger.info("Rationale:")
        logger.info(f"  {directive.get('reasoning', directive.get('rationale', 'N/A'))}")
        logger.info("")
        
        # Show agent insights summary
        logger.info("Agent Insights:")
        for agent_name, insight in result["agent_insights"].items():
            if agent_name == "MarketAgent":
                regime = insight.get("regime", "N/A")
                logger.info(f"  {agent_name}: Regime={regime}")
            elif agent_name == "RiskAgent":
                defcon = insight.get("defcon_level", "N/A")
                action = insight.get("action_required", "N/A")
                logger.info(f"  {agent_name}: DEFCON {defcon}, Action={action}")
            elif agent_name == "AnalystAgent":
                insight_text = insight.get("insight", "N/A")
                logger.info(f"  {agent_name}: {insight_text[:60]}...")
            elif agent_name == "StrategyAgent":
                recs = insight.get("recommendations", {})
                logger.info(f"  {agent_name}: {len(recs)} strategy recommendations")
            elif agent_name == "ExecutionAgent":
                mode = insight.get("execution_mode", "N/A")
                logger.info(f"  {agent_name}: Mode={mode}")
            elif agent_name == "AllocatorAgent":
                allocs = insight.get("allocations", {})
                logger.info(f"  {agent_name}: {len(allocs)} allocations proposed")
            elif agent_name != "RefereeAgent":
                recommendation = insight.get("recommendation", "N/A")
                logger.info(f"  {agent_name}: {recommendation}")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ Council Meeting Complete")
        logger.info("=" * 60)
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ HiveMind failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

