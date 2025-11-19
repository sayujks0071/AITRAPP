#!/usr/bin/env python3
"""
Kite Token Self-Check
=====================

Quick verification that your KITE_ACCESS_TOKEN is valid and working.

Usage:
    export KITE_API_KEY="***"
    export KITE_ACCESS_TOKEN="***"
    python scripts/kite_token_check.py
"""

import os
import sys

try:
    from kiteconnect import KiteConnect
except ImportError:
    print("❌ kiteconnect not installed. Run: pip install kiteconnect")
    sys.exit(1)


def main():
    api_key = os.getenv("KITE_API_KEY")
    access_token = os.getenv("KITE_ACCESS_TOKEN")
    
    if not api_key:
        print("❌ KITE_API_KEY not set")
        print("   Export it: export KITE_API_KEY=\"***\"")
        sys.exit(1)
    
    if not access_token:
        print("❌ KITE_ACCESS_TOKEN not set")
        print("   Export it: export KITE_ACCESS_TOKEN=\"***\"")
        print("   Or run: make kite-token-refresh")
        sys.exit(1)
    
    try:
        kite = KiteConnect(api_key=api_key)
        kite.set_access_token(access_token)
        
        # Test API call
        profile = kite.profile()
        user_id = profile.get("user_id", "N/A")
        
        print("="*60)
        print("✅ Token is valid and working!")
        print("="*60)
        print(f"\n📋 User ID: {user_id}")
        print(f"📋 API Key: {api_key[:10]}...")
        print(f"📋 Token: {access_token[:20]}...")
        print("\n✅ Ready for LIVE trading!")
        print("="*60)
        
    except Exception as e:
        error_str = str(e).lower()
        if "401" in error_str or "403" in error_str or "token" in error_str or "unauthorized" in error_str:
            print("="*60)
            print("❌ Token is invalid or expired")
            print("="*60)
            print("\n💡 Token expires daily at midnight IST")
            print("   Run: make kite-token-refresh")
            print("="*60)
        else:
            print("="*60)
            print(f"❌ Error: {e}")
            print("="*60)
        sys.exit(1)


if __name__ == "__main__":
    main()






