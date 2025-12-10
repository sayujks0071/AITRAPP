#!/usr/bin/env python3
"""
Emergency Hotfix: Extend Entry Window to 15:00 PM
==================================================
Extends the entry window to allow trading in afternoon session.
"""
import sys
import os
import yaml
from pathlib import Path

# Target the config mentioned in your report
CONFIG_PATH = "configs/kite_day1_live.yaml" 
# fallback if you are using canary
if not os.path.exists(CONFIG_PATH):
    CONFIG_PATH = "configs/kite_canary_live.yaml"

def extend_window():
    print(f"🔧 Patching {CONFIG_PATH} for Afternoon Session...")
    
    try:
        config_path = Path(CONFIG_PATH)
        if not config_path.exists():
            print(f"❌ Config file not found: {CONFIG_PATH}")
            return False
            
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f) or {}

        # 1. Extend Entry Window
        if 'entry' not in config: 
            config['entry'] = {}
        
        old_window_end = config['entry'].get('window_end', 'N/A')
        print(f"   - Old Window End: {old_window_end}")
        
        config['entry']['window_start'] = "09:15"  # Ensure start is open
        config['entry']['window_end'] = "15:00"    # EXTEND to 3 PM
        config['entry']['max_entries_per_day'] = 3  # Allow retries
        
        print(f"   - New Window End: {config['entry']['window_end']}")

        # 2. Update strategy-specific entry windows if they exist
        if 'strategies' in config:
            for strat in config['strategies']:
                if isinstance(strat, dict):
                    # Update individual strategy times if they exist
                    if 'params' in strat:
                        params = strat['params']
                        # Check for entry_time in params
                        if 'entry_time' in params:
                            print(f"   - Updating {strat.get('name', 'Unknown')} entry_time")
                            params['entry_time'] = "09:30"
                        if 'entry_window_start' in params:
                            params['entry_window_start'] = "09:30"
                        if 'entry_window_end' in params:
                            params['entry_window_end'] = "15:00"
                        if 'entry_after_time' in params:
                            # Remove or extend this restriction
                            print(f"   - Removing entry_after_time restriction from {strat.get('name', 'Unknown')}")
                            params.pop('entry_after_time', None)

        # Write back with proper formatting
        with open(config_path, 'w') as f:
            yaml.dump(config, f, sort_keys=False, default_flow_style=False, allow_unicode=True)
            
        print("✅ Config Patched Successfully.")
        print(f"   - Entry window now: {config['entry']['window_start']} - {config['entry']['window_end']}")
        return True
        
    except Exception as e:
        print(f"❌ Patch Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = extend_window()
    sys.exit(0 if success else 1)




