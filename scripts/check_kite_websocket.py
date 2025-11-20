#!/usr/bin/env python3
"""
Diagnostic script to check Kite WebSocket connection and app settings.

This script helps identify why WebSocket connections are failing with 403 errors.
"""
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

try:
    from kiteconnect import KiteConnect, KiteTicker
except ImportError:
    print("❌ kiteconnect not installed. Run: pip install kiteconnect")
    sys.exit(1)

# Load environment
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

def check_rest_api(api_key: str, access_token: str) -> bool:
    """Test REST API connection"""
    print("\n🔍 Testing REST API Connection...")
    try:
        kite = KiteConnect(api_key=api_key)
        kite.set_access_token(access_token)
        profile = kite.profile()
        print(f"✅ REST API: SUCCESS")
        print(f"   User: {profile.get('user_name', 'N/A')} ({profile.get('user_id', 'N/A')})")
        print(f"   Email: {profile.get('email', 'N/A')}")
        return True
    except Exception as e:
        print(f"❌ REST API: FAILED - {e}")
        return False

def test_websocket_connection(api_key: str, access_token: str) -> bool:
    """Test WebSocket connection with detailed error reporting"""
    print("\n🔍 Testing WebSocket Connection...")
    
    connection_established = False
    error_code = None
    error_reason = None
    
    def on_connect(ws, response):
        nonlocal connection_established
        connection_established = True
        print("✅ WebSocket: CONNECTED")
        print(f"   Response: {response}")
    
    def on_error(ws, code, reason):
        nonlocal error_code, error_reason
        error_code = code
        error_reason = reason
        print(f"❌ WebSocket Error: Code={code}, Reason={reason}")
        
        if code == 403:
            print("\n" + "="*70)
            print("🚨 403 FORBIDDEN ERROR DETECTED")
            print("="*70)
            print("\nThis error means your Kite Connect app does NOT have")
            print("WebSocket streaming enabled.")
            print("\n📋 ACTION REQUIRED:")
            print("1. Go to: https://developers.kite.trade/apps")
            print("2. Find your app (API Key: " + api_key + ")")
            print("3. Click on your app to open settings")
            print("4. Look for 'Websocket streaming' or 'Streaming' option")
            print("5. Enable it and save")
            print("6. Restart your trading server")
            print("\n" + "="*70)
    
    def on_close(ws, code, reason):
        print(f"⚠️  WebSocket closed: Code={code}, Reason={reason}")
    
    def on_ticks(ws, ticks):
        print(f"✅ Received {len(ticks)} ticks - WebSocket is working!")
        ws.close()
    
    try:
        # Create KiteTicker instance
        kws = KiteTicker(api_key, access_token)
        
        # Set callbacks
        kws.on_connect = on_connect
        kws.on_error = on_error
        kws.on_close = on_close
        kws.on_ticks = on_ticks
        
        print("   Attempting connection...")
        print("   (This may take 5-10 seconds)")
        
        # Connect in threaded mode
        kws.connect(threaded=True)
        
        # Wait for connection (max 10 seconds)
        timeout = 10
        start_time = time.time()
        while not connection_established and error_code is None:
            if time.time() - start_time > timeout:
                print("⏱️  Connection timeout after 10 seconds")
                kws.close()
                break
            time.sleep(0.5)
        
        # If connected, subscribe to a test token (NIFTY 50 index)
        if connection_established:
            print("\n   Subscribing to test instrument (NIFTY 50)...")
            # NIFTY 50 index token: 256265
            kws.subscribe([256265])
            kws.set_mode(kws.MODE_LTP, [256265])
            
            # Wait for ticks (max 5 seconds)
            time.sleep(5)
            kws.close()
            return True
        else:
            if error_code == 403:
                return False
            print("⚠️  Connection status unknown")
            return False
            
    except Exception as e:
        print(f"❌ WebSocket initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*70)
    print("🔍 KITE WEBSOCKET DIAGNOSTIC TOOL")
    print("="*70)
    
    api_key = os.getenv("KITE_API_KEY")
    access_token = os.getenv("KITE_ACCESS_TOKEN")
    
    if not api_key or not access_token:
        print("❌ Missing credentials in .env file")
        print("   Required: KITE_API_KEY, KITE_ACCESS_TOKEN")
        sys.exit(1)
    
    print(f"\n📋 API Key: {api_key}")
    print(f"📋 Token: {access_token[:30]}...")
    
    # Test REST API first
    rest_ok = check_rest_api(api_key, access_token)
    
    if not rest_ok:
        print("\n❌ REST API failed. Fix this first before testing WebSocket.")
        sys.exit(1)
    
    # Test WebSocket
    ws_ok = test_websocket_connection(api_key, access_token)
    
    print("\n" + "="*70)
    print("📊 DIAGNOSTIC SUMMARY")
    print("="*70)
    print(f"REST API: {'✅ OK' if rest_ok else '❌ FAILED'}")
    print(f"WebSocket: {'✅ OK' if ws_ok else '❌ FAILED'}")
    
    if not ws_ok:
        print("\n🔧 NEXT STEPS:")
        print("1. Enable WebSocket streaming in your Kite app settings")
        print("2. Wait 1-2 minutes for changes to propagate")
        print("3. Run this script again to verify")
        print("4. Restart your trading server")
        sys.exit(1)
    else:
        print("\n✅ All checks passed! WebSocket is working correctly.")
        sys.exit(0)

if __name__ == "__main__":
    main()

