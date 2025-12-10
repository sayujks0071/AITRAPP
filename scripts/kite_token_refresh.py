#!/usr/bin/env python3
"""
Kite Token Refresh - Daily Access Token Generator
==================================================

Quick one-liner to get fresh Kite access_token for LIVE trading.

Usage:
    # With env vars set
    python scripts/kite_token_refresh.py

    # Or prompt for credentials
    python scripts/kite_token_refresh.py --interactive

    # Or pass request_token directly
    python scripts/kite_token_refresh.py --request-token YOUR_TOKEN

After running, copy the export command and paste into your terminal.
"""

import argparse
import os
import re
import sys
import webbrowser
from typing import Optional, Tuple
from urllib.parse import urlparse, parse_qs

try:
    from kiteconnect import KiteConnect
except ImportError:
    print("❌ kiteconnect not installed. Run: pip install kiteconnect")
    sys.exit(1)


def get_credentials(interactive: bool = False) -> Tuple[str, str]:
    """Get API key and secret from env or prompt."""
    api_key = os.getenv("KITE_API_KEY")
    api_secret = os.getenv("KITE_API_SECRET")
    
    if not api_key or not api_secret:
        if interactive:
            print("\n📝 Enter your Kite Connect credentials:")
            api_key = input("API Key: ").strip()
            api_secret = input("API Secret: ").strip()
        else:
            print("❌ KITE_API_KEY and KITE_API_SECRET not set in environment")
            print("\nEither:")
            print("  1. Export them: export KITE_API_KEY=... KITE_API_SECRET=...")
            print("  2. Use --interactive flag to enter them")
            sys.exit(1)
    
    return api_key, api_secret


def open_login_url(api_key: str) -> None:
    """Open Kite login URL in browser."""
    login_url = f"https://kite.trade/connect/login?api_key={api_key}&v=3"
    print(f"\n🌐 Opening login URL in browser...")
    print(f"   {login_url}")
    print("\n📋 Steps:")
    print("  1. Login with your Zerodha credentials")
    print("  2. Complete 2FA if prompted")
    print("  3. You'll be redirected to a callback URL")
    print("  4. Copy the 'request_token' from the URL")
    print("\n   Example URL:")
    print("   http://localhost:8080/callback?request_token=XXXXX&action=login&status=success")
    print("                                 ^^^^^^^^^^^^")
    print("                                 Copy this part")
    
    try:
        webbrowser.open(login_url)
    except Exception as e:
        print(f"\n⚠️  Could not open browser automatically: {e}")
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
        print("\nCommon issues:")
        print("  - Request token expired (use within a few minutes)")
        print("  - Invalid API key/secret")
        print("  - Request token already used")
        raise


def format_export_command(access_token: str, user_id: Optional[str] = None) -> str:
    """Format export command for easy copy-paste."""
    lines = [
        f"export KITE_ACCESS_TOKEN=\"{access_token}\""
    ]
    if user_id:
        lines.append(f"export KITE_USER_ID=\"{user_id}\"")
    return "\n".join(lines)


# Exported for testing (smoke test without secrets)
def _emit_exports(access_token: str, user_id: Optional[str] = None) -> str:
    """Emit export commands (alias for format_export_command, exposed for testing)."""
    return format_export_command(access_token, user_id)


def main():
    parser = argparse.ArgumentParser(
        description="Refresh Kite Connect access token (daily)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using environment variables
  export KITE_API_KEY="***"
  export KITE_API_SECRET="***"
  python scripts/kite_token_refresh.py

  # Interactive mode (prompts for credentials)
  python scripts/kite_token_refresh.py --interactive

  # With request token already available
  python scripts/kite_token_refresh.py --request-token YOUR_TOKEN

  # Or pass URL directly
  python scripts/kite_token_refresh.py --url "http://localhost:8080/callback?request_token=XXX&..."
        """
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Interactive mode: prompt for API key/secret"
    )
    
    parser.add_argument(
        "--request-token", "-t",
        type=str,
        help="Request token (from callback URL)"
    )
    
    parser.add_argument(
        "--url", "-u",
        type=str,
        help="Full callback URL (will extract request_token)"
    )
    
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open browser automatically"
    )
    
    args = parser.parse_args()
    
    # Get credentials
    api_key, api_secret = get_credentials(interactive=args.interactive)
    
    # Get request token
    request_token = None
    
    if args.request_token:
        request_token = args.request_token.strip()
    elif args.url:
        request_token = extract_token_from_url(args.url)
        if not request_token:
            print("❌ Could not extract request_token from URL")
            sys.exit(1)
    else:
        # Open browser and prompt for token
        if not args.no_browser:
            open_login_url(api_key)
        
        print("\n" + "="*60)
        request_token = input("Paste request_token here: ").strip()
        
        # Try to extract if user pasted full URL
        if "request_token=" in request_token:
            extracted = extract_token_from_url(request_token)
            if extracted:
                request_token = extracted
    
    if not request_token:
        print("❌ No request token provided")
        sys.exit(1)
    
    # Generate access token
    print("\n🔄 Generating access token...")
    try:
        data = generate_access_token(api_key, api_secret, request_token)
    except Exception:
        sys.exit(1)
    
    access_token = data['access_token']
    user_id = data.get('user_id', '')
    
    # Output results
    print("\n" + "="*60)
    print("✅ SUCCESS! Fresh access token generated")
    print("="*60)
    print(f"\n📋 Access Token: {access_token}")
    if user_id:
        print(f"📋 User ID: {user_id}")
    
    print("\n" + "="*60)
    print("📋 COPY-PASTE THIS (for tomorrow's session):")
    print("="*60)
    export_cmd = format_export_command(access_token, user_id)
    print(f"\n{export_cmd}\n")
    print("="*60)
    
    # Try to update .env file
    env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(env_file):
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
            
            with open(env_file, 'w') as f:
                f.write(content)
            
            print("\n✅ .env file updated automatically!")
        except Exception as e:
            print(f"\n⚠️  Could not update .env file: {e}")
            print("   Please update manually")
    else:
        print("\n💡 Tip: Create a .env file to auto-update tokens")
    
    print("\n✅ Ready for LIVE trading! Use the export command above.\n")


if __name__ == "__main__":
    main()

