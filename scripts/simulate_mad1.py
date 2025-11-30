#!/usr/bin/env python3
"""
MAD-1 Simulation Test
====================

Tests if MAD-1 correctly identifies liquidity collapse and spread blowout scenarios.
"""

import sys
import os
import logging
import time
import random

sys.path.append(os.getcwd())
from packages.core.reflex.mad1 import MAD1

logging.basicConfig(level=logging.INFO, format='%(message)s')


def simulate():
    print("🚨 TESTING MAD-1 (MARKET ANOMALY DETECTOR) - Level 10")
    print("-" * 50)
    
    # Config: Trigger if liquidity drops 60%
    config = {
        "liquidity_drop_pct": 0.60,
        "spread_sigma_threshold": 3.0,
        "window_seconds": 30
    }
    mad = MAD1(config)
    
    print("Phase 1: Establishing Baseline (Normal Market)")
    base_price = 24000.0
    
    for i in range(60):
        # Normal healthy ticks
        tick = {
            'last_price': base_price + random.uniform(-5, 5),
            'depth': {
                'buy': [{'price': base_price-1, 'quantity': random.randint(5000, 6000)}],
                'sell': [{'price': base_price+1, 'quantity': random.randint(5000, 6000)}]
            }
        }
        mad.update(tick)
        time.sleep(0.01)  # Small delay to simulate real-time
    
    print("   ✅ Baseline Established.")
    
    print("\nPhase 2: Simulating Liquidity Collapse...")
    # Suddenly, order book thins out (Pre-Crash signature)
    vac_tick = {
        'last_price': base_price - 10,
        'depth': {
            'buy': [{'price': base_price-15, 'quantity': 100}],  # Only 100 left!
            'sell': [{'price': base_price-5, 'quantity': 5000}]
        }
    }
    
    triggered = mad.update(vac_tick)
    
    if triggered:
        print(f"   ✅ SUCCESS: MAD-1 Triggered! Cause: {mad.cause}")
    else:
        print(f"   ❌ FAILED: MAD-1 slept through the collapse.")
    
    print("-" * 50)
    
    print("\nPhase 3: Simulating Spread Blowout...")
    mad.reset()
    
    # Refill history
    for i in range(60):
        tick = {
            'last_price': base_price,
            'depth': {
                'buy': [{'price': 24000, 'quantity': 5000}],
                'sell': [{'price': 24001, 'quantity': 5000}]  # Spread 1.0
            }
        }
        mad.update(tick)
        time.sleep(0.01)
    
    # Blowout Tick
    blowout_tick = {
        'last_price': base_price,
        'depth': {
            'buy': [{'price': 23990, 'quantity': 5000}],
            'sell': [{'price': 24010, 'quantity': 5000}]  # Spread 20.0
        }
    }
    
    triggered = mad.update(blowout_tick)
    
    if triggered:
        print(f"   ✅ SUCCESS: MAD-1 Triggered! Cause: {mad.cause}")
    else:
        print(f"   ❌ FAILED: Spread detection failed.")
    
    print("\n" + "=" * 50)
    print("✅ MAD-1 Level 10 Test Complete!")
    print("=" * 50)


if __name__ == "__main__":
    simulate()





