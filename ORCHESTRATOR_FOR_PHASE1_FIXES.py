"""
ORCHESTRATOR.PY - Ready for Phase 1 Fixes

This file is provided for implementing the Phase 1 improvements:
1. Fix token limit (20 → 50 or strategy-specific filtering)
2. Add priority ordering (sort strategies by priority)
3. Enhance StrategyContext (add regime/event context)

Current Issues:
- Line 692: Token limit hardcoded to 20
- Line 684: Strategies run in list order (no priority sorting)
- Line 708: StrategyContext missing regime/event fields

Key Sections:
- Lines 662-725: _scan_cycle() - Main execution loop
- Lines 684-724: Strategy execution loop (needs priority sorting)
- Lines 708-717: StrategyContext creation (needs regime/event)
"""

# This is a reference file - the actual orchestrator is at:
# packages/core/orchestrator.py

