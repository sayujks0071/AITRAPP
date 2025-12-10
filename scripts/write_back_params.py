#!/usr/bin/env python3
"""
Write back tuned parameters to config files.

Usage:
    python scripts/write_back_params.py \
        --input reports/tuning/orb_nifty_walkforward.json \
        --config configs/app.yaml \
        --strategy orb
"""
import argparse
import json
import sys
from pathlib import Path

import yaml


def main():
    parser = argparse.ArgumentParser(description="Write back tuned parameters to configs")
    parser.add_argument("--input", required=True, help="JSON file with tuning results")
    parser.add_argument("--config", required=True, help="Config file to update")
    parser.add_argument("--strategy", required=True, help="Strategy name (orb, trend_pullback, etc.)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be written without modifying files")
    
    args = parser.parse_args()
    
    # Load tuning results
    with open(args.input, "r") as f:
        results = json.load(f)
    
    best_params = results.get("best_params", {})
    if not best_params:
        print("❌ No best_params found in results")
        sys.exit(1)
    
    # Load config
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)
    
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    # Map strategy name
    strategy_key = args.strategy.lower()
    if strategy_key == "orb":
        strategy_key = "orb"
    elif strategy_key == "trendpullback":
        strategy_key = "trend_pullback"
    elif strategy_key == "optionsranker":
        strategy_key = "options_ranker"
    
    # Ensure strategies section exists
    if "strategies" not in config:
        config["strategies"] = {}
    
    if strategy_key not in config["strategies"]:
        config["strategies"][strategy_key] = {}
    
    # Map parameters
    strategy_config = config["strategies"][strategy_key]
    
    # ORB mapping
    if args.strategy.lower() == "orb":
        if "window_min" in best_params:
            strategy_config["session_or"] = f"{best_params['window_min']}m"
        if "atr_mult" in best_params:
            strategy_config["atr_mult"] = best_params["atr_mult"]
        if "confirm_candles" in best_params:
            strategy_config["confirm_candles"] = best_params["confirm_candles"]
        if "vol_z" in best_params:
            strategy_config["vol_z"] = best_params["vol_z"]
        if "widen_n" in best_params:
            strategy_config["widen_n"] = best_params["widen_n"]
        if "cool_down" in best_params:
            strategy_config["cool_down"] = best_params["cool_down"]
        if "atr_len" in best_params:
            strategy_config["atr_len"] = best_params["atr_len"]
        else:
            strategy_config["atr_len"] = 14  # Default
    
    # Show what will be written
    print(f"📝 Writing back to {config_path}")
    print(f"   Strategy: {strategy_key}")
    print(f"\n   Parameters:")
    for key, value in strategy_config.items():
        print(f"     {key}: {value}")
    
    if args.dry_run:
        print("\n⚠️  DRY RUN - No changes made")
        return
    
    # Write back
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print(f"\n✅ Updated {config_path}")


if __name__ == "__main__":
    main()


