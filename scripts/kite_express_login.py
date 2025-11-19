#!/usr/bin/env python3
"""
Kite Express Login - One-Click Morning Login
=============================================

Automated morning login process:
1. Opens browser for quick login
2. Waits for callback URL
3. Automatically extracts and refreshes token
4. Updates .env file
5. Optionally restarts API

Usage:
    python3 scripts/kite_express_login.py
    python3 scripts/kite_express_login.py --auto-restart
    python3 scripts/kite_express_login.py --background
"""

import argparse
import os
import re
import sys
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse, parse_qs

try:
    from kiteconnect import KiteConnect
except ImportError:
    print("❌ kiteconnect not installed. Run: pip install kiteconnect")
    sys.exit(1)


def get_credentials() -> Tuple[str, str]:
    """Get API key and secret from env."""
    api_key = os.getenv("KITE_API_KEY")
    api_secret = os.getenv("KITE_API_SECRET")
    
    if not api_key or not api_secret:
        print("❌ KITE_API_KEY and KITE_API_SECRET not set in environment")
        print("\nSet them in .env file or export:")
        print("  export KITE_API_KEY=\"***\"")
        print("  export KITE_API_SECRET=\"***\"")
        sys.exit(1)
    
    return api_key, api_secret


def open_login_url(api_key: str) -> None:
    """Open Kite login URL in browser."""
    login_url = f"https://kite.trade/connect/login?api_key={api_key}&v=3"
    print(f"\n🌐 Opening Kite login page...")
    print(f"   {login_url}\n")
    
    try:
        webbrowser.open(login_url)
    except Exception as e:
        print(f"⚠️  Could not open browser automatically: {e}")
        print(f"   Please visit: {login_url}")


def extract_token_from_url(url: str) -> Optional[str]:
    """Extract request_token from callback URL."""
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        if "request_token" in params:
            return params["request_token"][0]
    except Exception:
        pass
    return None


def generate_access_token(api_key: str, api_secret: str, request_token: str) -> dict:
    """Generate access token from request token."""
    try:
        kite = KiteConnect(api_key=api_key)
        data = kite.generate_session(request_token, api_secret=api_secret)
        return data
    except Exception as e:
        print(f"\n❌ Error generating access token: {e}")
        raise


def update_env_file(access_token: str, user_id: Optional[str] = None) -> bool:
    """Update .env file with new token."""
    env_file = Path(__file__).parent.parent / '.env'
    
    if not env_file.exists():
        print(f"⚠️  .env file not found at {env_file}")
        return False
    
    try:
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Update or add KITE_ACCESS_TOKEN
        if re.search(r'^KITE_ACCESS_TOKEN=', content, re.MULTILINE):
            content = re.sub(
                r'^KITE_ACCESS_TOKEN=.*',
                f'KITE_ACCESS_TOKEN={access_token}',
                content,
                flags=re.MULTILINE
            )
        else:
            content += f'\nKITE_ACCESS_TOKEN={access_token}\n'
        
        # Update or add KITE_USER_ID
        if user_id:
            if re.search(r'^KITE_USER_ID=', content, re.MULTILINE):
                content = re.sub(
                    r'^KITE_USER_ID=.*',
                    f'KITE_USER_ID={user_id}',
                    content,
                    flags=re.MULTILINE
                )
            else:
                content += f'KITE_USER_ID={user_id}\n'
        
        # Add token refresh timestamp
        timestamp = datetime.now().isoformat()
        if re.search(r'^KITE_TOKEN_REFRESHED_AT=', content, re.MULTILINE):
            content = re.sub(
                r'^KITE_TOKEN_REFRESHED_AT=.*',
                f'KITE_TOKEN_REFRESHED_AT={timestamp}',
                content,
                flags=re.MULTILINE
            )
        else:
            content += f'KITE_TOKEN_REFRESHED_AT={timestamp}\n'
        
        with open(env_file, 'w') as f:
            f.write(content)
        
        return True
    except Exception as e:
        print(f"⚠️  Could not update .env file: {e}")
        return False


def cleanup_old_tokens() -> None:
    """Clean up old token files/logs if any."""
    # This is a placeholder for future cleanup logic
    # Could remove old token backup files, logs, etc.
    pass


def prompt_for_token() -> Optional[str]:
    """Prompt user to paste request_token or callback URL."""
    print("\n" + "="*60)
    print("📋 INSTRUCTIONS:")
    print("="*60)
    print("1. Login with your Zerodha credentials in the browser")
    print("2. Complete 2FA if prompted")
    print("3. You'll be redirected to a callback URL")
    print("4. Copy the ENTIRE URL or just the request_token")
    print("\n   Example URL:")
    print("   http://localhost:8080/callback?request_token=XXXXX&action=login&status=success")
    print("="*60)
    
    user_input = input("\n📋 Paste request_token or callback URL here: ").strip()
    
    if not user_input:
        return None
    
    # Try to extract if user pasted full URL
    if "request_token=" in user_input:
        extracted = extract_token_from_url(user_input)
        if extracted:
            return extracted
    
    return user_input


def main():
    parser = argparse.ArgumentParser(
        description="Express login for Kite Connect (one-click morning login)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--auto-restart",
        action="store_true",
        help="Automatically restart API after token refresh"
    )
    
    parser.add_argument(
        "--background",
        action="store_true",
        help="Run in background mode (for automation)"
    )
    
    parser.add_argument(
        "--request-token",
        type=str,
        help="Request token (skip browser prompt)"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("🚀 KITE EXPRESS LOGIN")
    print("="*60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Get credentials
    api_key, api_secret = get_credentials()
    
    # Get request token
    request_token = args.request_token
    
    if not request_token:
        # Open browser
        open_login_url(api_key)
        
        # Prompt for token
        request_token = prompt_for_token()
        
        if not request_token:
            print("\n❌ No request token provided")
            sys.exit(1)
    
    # Generate access token
    print("\n🔄 Generating access token...")
    try:
        data = generate_access_token(api_key, api_secret, request_token)
    except Exception as e:
        print(f"\n❌ Failed to generate access token: {e}")
        sys.exit(1)
    
    access_token = data['access_token']
    user_id = data.get('user_id', '')
    
    # Update .env file
    print("💾 Updating .env file...")
    if update_env_file(access_token, user_id):
        print("✅ .env file updated")
    else:
        print("⚠️  Could not update .env file (continuing anyway)")
    
    # Cleanup old tokens
    cleanup_old_tokens()
    
    # Success message
    print("\n" + "="*60)
    print("✅ EXPRESS LOGIN SUCCESSFUL!")
    print("="*60)
    print(f"\n📋 User ID: {user_id}")
    print(f"📋 Token: {access_token[:20]}...")
    print(f"📋 Refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Auto-restart API if requested
    if args.auto_restart:
        print("\n🔄 Restarting API...")
        import subprocess
        try:
            # Stop existing API
            subprocess.run(["pkill", "-f", "uvicorn apps.api.main:app"], 
                         capture_output=True)
            time.sleep(2)
            
            # Start API
            script_dir = Path(__file__).parent.parent
            subprocess.Popen(
                ["python3", "-m", "uvicorn", "apps.api.main:app", 
                 "--host", "0.0.0.0", "--port", "8000"],
                cwd=script_dir,
                env={**os.environ, "KITE_ACCESS_TOKEN": access_token}
            )
            print("✅ API restarted")
        except Exception as e:
            print(f"⚠️  Could not restart API: {e}")
    
    print("\n✅ Ready for LIVE trading!\n")
    
    # Export command for manual use
    print("="*60)
    print("📋 EXPORT COMMAND (if needed):")
    print("="*60)
    print(f"export KITE_ACCESS_TOKEN=\"{access_token}\"")
    if user_id:
        print(f"export KITE_USER_ID=\"{user_id}\"")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()

