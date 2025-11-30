#!/usr/bin/env python3
"""
SG-1 Strategy Generator - CLI Runner
====================================

Autonomous strategy generation using AI.

Usage:
    python3 scripts/run_sg1.py [--regime REGIME]
    python3 scripts/run_sg1.py --regime "SIDEWAYS_CHOP"
    python3 scripts/run_sg1.py  # Auto-ideates worst-performing regime
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.core.intelligence.sg1 import SG1Generator
from packages.core.rag_memory import RAGMemory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("sg1_cli")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="SG-1 Strategy Generator - Generate new trading strategies using AI"
    )
    parser.add_argument(
        "--regime",
        type=str,
        default=None,
        help="Target market regime (e.g., 'SIDEWAYS_CHOP', 'LOW_VOL'). If not specified, auto-ideates worst-performing regime."
    )
    parser.add_argument(
        "--memory-path",
        type=str,
        default="data/memory.json",
        help="Path to RAG memory JSON file"
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("🤖 SG-1 STRATEGY GENERATOR")
    logger.info("=" * 60)
    logger.info(f"📁 Memory: {args.memory_path}")
    if args.regime:
        logger.info(f"🎯 Target Regime: {args.regime}")
    else:
        logger.info("🎯 Auto-Ideation: Will find worst-performing regime")
    logger.info("")
    
    try:
        # Initialize SG-1
        memory = RAGMemory(db_path=args.memory_path)
        sg1 = SG1Generator(memory=memory)
        
        if not sg1.model:
            logger.error("❌ SG-1: Gemini API not configured. Cannot generate strategies.")
            logger.error("   Set GEMINI_API_KEY in .env file")
            logger.error("   Install: pip install google-generativeai")
            sys.exit(1)
        
        # Generate strategy
        filepath = sg1.generate_new_strategy(regime_focus=args.regime)
        
        if filepath:
            logger.info("")
            logger.info("=" * 60)
            logger.info("✅ STRATEGY GENERATION SUCCESSFUL")
            logger.info("=" * 60)
            logger.info(f"📁 Generated File: {filepath}")
            logger.info("")
            logger.info("📋 Next Steps:")
            logger.info("   1. Review the generated strategy code")
            logger.info("   2. Test it in backtest mode")
            logger.info("   3. If approved, add to config YAML")
            logger.info("   4. Deploy to live trading")
            logger.info("")
            sys.exit(0)
        else:
            logger.error("")
            logger.error("=" * 60)
            logger.error("❌ STRATEGY GENERATION FAILED")
            logger.error("=" * 60)
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ SG-1 failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

