#!/usr/bin/env python3
"""Verify E1 Event Vol Engine is loaded and working"""
import sys
from datetime import date, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
from packages.core.event_vol_engine import EventVolEngine


def main():
    """Verify E1 engine"""
    print("🔍 E1 Event Vol Engine Verification")
    print("=" * 60)
    print()
    
    # Load config
    cfg_path = Path("configs/event_vol_engine.yaml")
    if not cfg_path.exists():
        print(f"❌ Config not found: {cfg_path}")
        return 1
    
    try:
        with open(cfg_path, "r") as f:
            raw = yaml.safe_load(f)
        
        e1_cfg = raw.get("event_vol_engine", {})
        if not e1_cfg:
            print("❌ No event_vol_engine config found")
            return 1
        
        print("✅ Config loaded")
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return 1
    
    # Initialize engine
    try:
        engine = EventVolEngine(cfg=e1_cfg, metrics=None)
        print("✅ EventVolEngine initialized")
        print(f"   Enabled: {engine.enabled}")
        print(f"   Events loaded: {len(engine.events)}")
        print()
    except Exception as e:
        print(f"❌ Error initializing engine: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Test day context for various dates
    print("📅 Testing Day Context (7-day window)")
    print("-" * 60)
    
    today = date.today()
    underlyings = ["NIFTY", "BANKNIFTY"]
    
    for underlying in underlyings:
        print(f"\n{underlying}:")
        for delta in range(-3, 4):
            d = today + timedelta(days=delta)
            ctx = engine.get_day_context(d, underlying)
            
            event_info = ""
            if ctx.primary_event:
                event_info = f" ({ctx.primary_event}, {ctx.primary_type})"
            
            print(
                f"  {d}: {ctx.day_type:12s} "
                f"severity={ctx.severity:.2f} "
                f"h1_mult={ctx.h1_coverage_multiplier:.2f}"
                f"{event_info}"
            )
    
    print()
    print("=" * 60)
    print("✅ E1 Event Vol Engine verification complete!")
    print()
    print("💡 E1 provides:")
    print("   - Day type classification (NORMAL/PRE_EVENT/EVENT_DAY/POST_EVENT)")
    print("   - R1 regime bias hints")
    print("   - Allocator role multipliers")
    print("   - H1 coverage multipliers")
    print()
    print("📊 Integration:")
    print("   - R1: Can use event context for regime hints")
    print("   - Allocator: Uses event_ctx.allocator_role_multipliers")
    print("   - H1: Uses event_ctx.h1_coverage_multiplier")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())


