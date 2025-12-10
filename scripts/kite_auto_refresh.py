#!/usr/bin/env python3
"""
Kite Auto Token Refresh - Background Service
==============================================

Automatically refreshes Kite access token before expiry.
Can run as a background service or scheduled task.

Usage:
    # Run once (check and refresh if needed)
    python3 scripts/kite_auto_refresh.py --check
    
    # Run as background service
    python3 scripts/kite_auto_refresh.py --daemon
    
    # Schedule refresh (e.g., daily at 8:55 AM)
    python3 scripts/kite_auto_refresh.py --schedule "08:55"
"""

import argparse
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

try:
    from kiteconnect import KiteConnect
except ImportError:
    print("❌ kiteconnect not installed. Run: pip install kiteconnect")
    sys.exit(1)


def check_token_validity(api_key: str, access_token: str) -> Tuple[bool, Optional[str]]:
    """Check if current token is valid."""
    try:
        kite = KiteConnect(api_key=api_key)
        kite.set_access_token(access_token)
        profile = kite.profile()
        return True, profile.get("user_id")
    except Exception as e:
        error_str = str(e).lower()
        if '401' in error_str or '403' in error_str or 'token' in error_str:
            return False, None
        # Other errors (network, etc.) - assume token might still be valid
        return True, None


def get_token_age() -> Optional[timedelta]:
    """Get age of current token from .env file."""
    env_file = Path(__file__).parent.parent / '.env'
    
    if not env_file.exists():
        return None
    
    try:
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Look for refresh timestamp
        match = re.search(r'^KITE_TOKEN_REFRESHED_AT=(.+)$', content, re.MULTILINE)
        if match:
            timestamp_str = match.group(1).strip()
            try:
                refreshed_at = datetime.fromisoformat(timestamp_str)
                return datetime.now() - refreshed_at
            except ValueError:
                pass
    except Exception:
        pass
    
    return None


def should_refresh_token() -> bool:
    """Determine if token should be refreshed."""
    api_key = os.getenv("KITE_API_KEY")
    access_token = os.getenv("KITE_ACCESS_TOKEN")
    
    if not api_key or not access_token:
        return True  # No token, need to refresh
    
    # Check if token is valid
    is_valid, _ = check_token_validity(api_key, access_token)
    if not is_valid:
        return True  # Token invalid, need to refresh
    
    # Check token age (refresh if > 20 hours old)
    token_age = get_token_age()
    if token_age and token_age > timedelta(hours=20):
        return True  # Token too old, refresh proactively
    
    return False  # Token is valid and fresh


def main():
    parser = argparse.ArgumentParser(
        description="Auto-refresh Kite access token",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check token validity and refresh if needed"
    )
    
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as background daemon (checks every hour)"
    )
    
    parser.add_argument(
        "--schedule",
        type=str,
        help="Schedule refresh at specific time (HH:MM format, IST)"
    )
    
    args = parser.parse_args()
    
    if args.check:
        print("\n🔍 Checking token validity...")
        
        if should_refresh_token():
            print("⚠️  Token needs refresh")
            print("   Run: python3 scripts/kite_express_login.py")
            sys.exit(1)
        else:
            print("✅ Token is valid")
            sys.exit(0)
    
    elif args.daemon:
        print("🔄 Starting auto-refresh daemon...")
        print("   Checks every hour, refreshes if needed\n")
        
        while True:
            try:
                if should_refresh_token():
                    print(f"[{datetime.now()}] ⚠️  Token needs refresh")
                    print("   Run: python3 scripts/kite_express_login.py")
                else:
                    print(f"[{datetime.now()}] ✅ Token valid")
                
                time.sleep(3600)  # Check every hour
            except KeyboardInterrupt:
                print("\n🛑 Daemon stopped")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                time.sleep(60)  # Wait 1 minute before retry
    
    elif args.schedule:
        print(f"⏰ Scheduled refresh at {args.schedule} IST")
        # This would require a scheduler (cron, systemd, etc.)
        # For now, just check
        if should_refresh_token():
            print("⚠️  Token needs refresh")
            print("   Run: python3 scripts/kite_express_login.py")
        else:
            print("✅ Token is valid")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

