#!/usr/bin/env python3
"""
Quick script to apply backtest mode filters to all strategies.
This adds relaxed filters for backtesting to generate trades.
"""
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
STRATEGIES_DIR = BASE_DIR / "packages" / "core" / "strategies"

STRATEGIES = [
    "rsi_mean_reversion.py",
    "bollinger_bands_strategy.py",
    "vwap_strategy.py",
    "breakout_strategy.py",
    "mean_reversion.py"
]

def add_backtest_params(file_path):
    """Add backtest mode parameters to strategy __init__"""
    content = file_path.read_text()
    
    # Check if already has backtest params
    if "backtest_rr_min" in content:
        print(f"  ⚠️  {file_path.name} already has backtest params")
        return False
    
    # Find the params section
    pattern = r'(self\.rr_min = params\.get\("rr_min", [\d.]+\))\s*\n'
    replacement = r'\1\n        \n        # Backtest mode parameters (relaxed filters)\n        self.backtest_rr_min = params.get("backtest_rr_min", 1.0)\n        self.backtest_volume_mult = params.get("backtest_volume_mult", 0.0)\n'
    
    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content)
        file_path.write_text(content)
        print(f"  ✅ Added backtest params to {file_path.name}")
        return True
    else:
        print(f"  ⚠️  Could not find rr_min in {file_path.name}")
        return False

def add_backtest_mode_flag(file_path):
    """Add backtest mode flag storage in generate_signals"""
    content = file_path.read_text()
    
    if "_backtest_mode = context.backtest_mode" in content:
        print(f"  ⚠️  {file_path.name} already has backtest mode flag")
        return False
    
    # Find generate_signals method start
    pattern = r'(def generate_signals\(self, context: StrategyContext\) -> List\[Signal\]:\s*""".*?"""\s*if not self\.validate\(context\):)'
    replacement = r'\1\n        # Store backtest mode for use in signal creation\n        self._backtest_mode = context.backtest_mode\n        '
    
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        file_path.write_text(content)
        print(f"  ✅ Added backtest mode flag to {file_path.name}")
        return True
    else:
        # Try simpler pattern
        pattern = r'(def generate_signals\(self, context: StrategyContext\) -> List\[Signal\]:\s*"""[\s\S]*?"""\s*if not self\.validate\(context\):)'
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            file_path.write_text(content)
            print(f"  ✅ Added backtest mode flag to {file_path.name}")
            return True
        else:
            print(f"  ⚠️  Could not find generate_signals pattern in {file_path.name}")
            return False

def main():
    print("🔧 Applying backtest mode filters to strategies...\n")
    
    for strategy_file in STRATEGIES:
        file_path = STRATEGIES_DIR / strategy_file
        if not file_path.exists():
            print(f"  ❌ {strategy_file} not found")
            continue
        
        print(f"\n📝 Processing {strategy_file}:")
        add_backtest_params(file_path)
        add_backtest_mode_flag(file_path)
    
    print("\n✅ Done! Strategies now support backtest mode with relaxed filters.")

if __name__ == "__main__":
    main()

