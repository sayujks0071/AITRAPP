#!/usr/bin/env python3
"""
Nightly HiveMind Round - Agent-to-Agent Config Tuning
======================================================

Runs a full agent conversation loop to generate config tuning suggestions.
All agents share the same LLM backend (Claude or OpenAI).

Usage:
    python3 scripts/nightly_hivemind_round.py [--dry-run]
"""

import argparse
import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from packages.core.hivemind.orchestrator import HiveMindOrchestrator
from packages.core.hivemind.patch_converter import convert_sg1_to_patches

load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        description="Run HiveMind agent-to-agent config tuning round"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate suggestions but don't apply them"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (default: reports/hivemind/{date}_hivemind_patches.json)"
    )
    parser.add_argument(
        "--format",
        choices=["raw", "patches"],
        default="patches",
        help="Output format: 'raw' (agent outputs) or 'patches' (patch schema)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🧠 HIVEMIND ORCHESTRATOR: AGENT-TO-AGENT ROUND")
    print("=" * 60)
    
    # Check provider
    provider = os.getenv("HIVEMIND_PROVIDER", "anthropic").lower()
    print(f"📡 LLM Provider: {provider}")
    if provider == "anthropic":
        print(f"   Model: {os.getenv('HIVEMIND_ANTHROPIC_MODEL', 'claude-3-5-sonnet-latest')}")
    else:
        print(f"   Model: {os.getenv('HIVEMIND_OPENAI_MODEL', 'gpt-5')}")
    print()
    
    # Initialize orchestrator
    hm = HiveMindOrchestrator(vector_store=None)  # TODO: Add vector store if available
    
    # Build core context (TODO: Load from actual metrics/DB)
    core_ctx = {
        "day": datetime.now().strftime("%Y-%m-%d"),
        "metrics": {
            "intraday_short_strangle_v1": {
                "trades": 4,
                "wins": 3,
                "losses": 1,
                "max_dd": -2800,
                "win_rate": 0.75,
                "avg_rr": 1.4,
                "streak": 2
            },
            "trend_credit_spread_v1": {
                "trades": 2,
                "wins": 1,
                "losses": 1,
                "max_dd": -1900,
                "win_rate": 0.50,
                "avg_rr": 0.8,
                "streak": -1
            }
        },
        "guardrails": {
            "max_dd_per_strategy": 0.03,
            "max_dd_portfolio": 0.05,
        },
    }
    
    print("📊 Running agent conversation round...")
    print("   1. CortexAnalyst analyzing metrics...")
    print("   2. SG1StrategyGenerator generating patches...")
    print()
    
    # Run the round
    try:
        result = hm.run_config_round(core_ctx)
        
        print("=" * 60)
        print("✅ AGENT ROUND COMPLETE")
        print("=" * 60)
        print()
        
        # Pretty print results
        print("📋 CORTEX ANALYST OUTPUT:")
        print(json.dumps(result["analyst"], indent=2))
        print()
        
        print("🔧 SG-1 STRATEGY GENERATOR OUTPUT:")
        print(json.dumps(result["sg1"], indent=2))
        print()
        
        # Convert to patch format if requested
        if args.format == "patches":
            patch_doc = convert_sg1_to_patches(
                sg1_output=result["sg1"],
                analyst_output=result["analyst"],
                day=core_ctx["day"]
            )
            
            print("📦 PATCH DOCUMENT:")
            print(json.dumps(patch_doc, indent=2))
            print()
            
            # Save patch document
            if args.output:
                patch_path = Path(args.output)
            else:
                reports_dir = Path("reports/hivemind")
                reports_dir.mkdir(parents=True, exist_ok=True)
                patch_path = reports_dir / f"{core_ctx['day']}_hivemind_patches.json"
            
            with open(patch_path, "w") as f:
                json.dump(patch_doc, f, indent=2)
            
            print(f"💾 Patch document saved to: {patch_path}")
            print()
            print("📋 Next steps:")
            print(f"   1. Review patches: cat {patch_path}")
            print(f"   2. Dry-run apply: DRY_RUN=1 python scripts/apply_hivemind_patches.py --config configs/kite_day1_live.yaml --patch {patch_path}")
            print(f"   3. Apply changes: python scripts/apply_hivemind_patches.py --config configs/kite_day1_live.yaml --patch {patch_path}")
        else:
            # Save raw agent outputs
            if args.output:
                output_path = Path(args.output)
            else:
                reports_dir = Path("reports/tuning")
                reports_dir.mkdir(parents=True, exist_ok=True)
                output_path = reports_dir / f"{core_ctx['day']}_HIVEMIND_ROUND.json"
            
            with open(output_path, "w") as f:
                json.dump(result, f, indent=2)
            
            print(f"💾 Results saved to: {output_path}")
        
        if args.dry_run:
            print()
            print("⚠️  DRY RUN MODE: No changes applied")
        else:
            print()
            print("📝 Next steps:")
            print("   1. Review the proposed changes")
            print("   2. If approved, apply using config patcher")
            print("   3. Test in backtest mode before live deployment")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

