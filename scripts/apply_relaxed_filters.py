#!/usr/bin/env python3
"""
Apply relaxed filters to all strategies for backtesting.
Updates R:R calculations and adds relaxed volume/cooldown checks.
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

def update_rr_calculations(file_path):
    """Update R:R calculations to use backtest_rr_min"""
    content = file_path.read_text()
    
    # Pattern: reward = risk * self.rr_min
    pattern = r'reward = risk \* self\.rr_min'
    replacement = r'rr_required = self.backtest_rr_min if hasattr(self, \'_backtest_mode\') and self._backtest_mode else self.rr_min\n        reward = risk * rr_required'
    
    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content)
        file_path.write_text(content)
        print(f"  ✅ Updated R:R calculations in {file_path.name}")
        return True
    return False

def add_relaxed_volume_check(file_path):
    """Add relaxed volume check method"""
    content = file_path.read_text()
    
    if "_check_volume_confirmation_backtest" in content:
        print(f"  ⚠️  {file_path.name} already has backtest volume check")
        return False
    
    # Find _check_volume_confirmation method
    pattern = r'(def _check_volume_confirmation\(self, bars: List\[Bar\]\) -> bool:[\s\S]*?return current_volume >= avg_volume \* self\.min_volume_mult)'
    
    replacement = r'''\1
    
    def _check_volume_confirmation_backtest(self, bars: List[Bar]) -> bool:
        """Relaxed volume check for backtesting"""
        if not self.volume_confirmation or len(bars) < self.volume_lookback + 1:
            return True
        
        recent_volumes = [b.volume for b in bars[-self.volume_lookback:]]
        avg_volume = sum(recent_volumes) / len(recent_volumes)
        current_volume = bars[-1].volume
        
        return current_volume >= avg_volume * self.backtest_volume_mult'''
    
    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content)
        file_path.write_text(content)
        print(f"  ✅ Added relaxed volume check to {file_path.name}")
        return True
    return False

def add_relaxed_cooldown(file_path):
    """Add relaxed cooldown check"""
    content = file_path.read_text()
    
    # Find cooldown check pattern
    pattern = r'(# Check for cooldown\s+if not self\._can_generate_signal\(token, context\.timestamp\):\s+.*?return \[\])'
    
    replacement = r'''# Check for cooldown (relaxed in backtest mode)
        if context.backtest_mode:
            if token in self.last_signal_time:
                time_diff = (context.timestamp - self.last_signal_time[token]).total_seconds() / 60
                if time_diff < 5:  # 5 min cooldown in backtest
                    logger.debug("Cooldown period active (backtest)", token=token)
                    return []
        else:
            if not self._can_generate_signal(token, context.timestamp):
                logger.debug("Cooldown period active", token=token)
                return []'''
    
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        file_path.write_text(content)
        print(f"  ✅ Added relaxed cooldown to {file_path.name}")
        return True
    return False

def add_relaxed_volume_usage(file_path):
    """Update volume confirmation to use relaxed check in backtest mode"""
    content = file_path.read_text()
    
    # Find volume confirmation check
    pattern = r'(# Check volume confirmation\s+if not self\._check_volume_confirmation\(bars\):\s+logger\.debug\("Volume confirmation failed", token=token\)\s+return \[\])'
    
    replacement = r'''# Check volume confirmation (relaxed in backtest mode)
        if context.backtest_mode:
            if not self._check_volume_confirmation_backtest(bars):
                logger.debug("Volume confirmation failed (backtest)", token=token)
                return []
        else:
            if not self._check_volume_confirmation(bars):
                logger.debug("Volume confirmation failed", token=token)
                return []'''
    
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        file_path.write_text(content)
        print(f"  ✅ Added relaxed volume usage to {file_path.name}")
        return True
    return False

def main():
    print("🔧 Applying relaxed filters to strategies for backtesting...\n")
    
    for strategy_file in STRATEGIES:
        file_path = STRATEGIES_DIR / strategy_file
        if not file_path.exists():
            print(f"  ❌ {strategy_file} not found")
            continue
        
        print(f"\n📝 Processing {strategy_file}:")
        update_rr_calculations(file_path)
        add_relaxed_volume_check(file_path)
        add_relaxed_volume_usage(file_path)
        add_relaxed_cooldown(file_path)
    
    print("\n✅ Done! All strategies now have relaxed filters for backtesting.")

if __name__ == "__main__":
    main()

