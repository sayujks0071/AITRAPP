#!/usr/bin/env python3
"""
Kite Trader - Simple CLI tool to login and start trading

This tool provides a user-friendly interface to:
1. Login to Kite Connect
2. Select trading mode (PAPER/LIVE)
3. Start the trading system
4. Monitor status
"""

import os
import sys
import subprocess
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Add project to path
sys.path.insert(0, os.getcwd())

from src.auth.kite_auth import KiteAuth


class KiteTrader:
    """Kite Trader CLI"""

    def __init__(self):
        load_dotenv(override=True)
        self.auth = KiteAuth()
        self.api_port = int(os.getenv("API_PORT", "8000"))

    def print_banner(self):
        """Print welcome banner"""
        print("=" * 70)
        print("    🚀 AITRAPP - Kite Trading System")
        print("=" * 70)
        print()

    def check_session(self) -> bool:
        """Check if current session is valid"""
        print("📡 Checking session status...")
        try:
            if self.auth.is_session_valid():
                print("✅ Session is valid!")
                return True
            else:
                print("❌ Session is invalid or expired")
                return False
        except Exception as e:
            print(f"❌ Error checking session: {e}")
            return False

    def login(self) -> bool:
        """Handle login flow"""
        print("\n" + "=" * 70)
        print("    🔐 LOGIN TO KITE")
        print("=" * 70)

        # Check if credentials are set
        if not self.auth.api_key or not self.auth.api_secret:
            print("\n❌ Missing KITE_API_KEY or KITE_API_SECRET in .env file")
            print("\nPlease add them to your .env file:")
            print("  KITE_API_KEY=your_api_key")
            print("  KITE_API_SECRET=your_api_secret")
            return False

        try:
            # Generate login URL
            login_url = self.auth.get_login_url()

            print("\n📝 Login Steps:")
            print("1. Open this URL in your browser:")
            print(f"\n   {login_url}\n")
            print("2. Login with your Zerodha credentials")
            print("3. After login, copy the 'request_token' from the redirect URL")
            print("   (URL will look like: http://...?request_token=XXXXX&...)")

            # Get request token from user
            request_token = input("\n4. Paste the request_token here: ").strip()

            if not request_token:
                print("❌ No request token provided")
                return False

            # Exchange token
            print("\n🔄 Exchanging token...")
            access_token = self.auth.exchange_request_token(request_token)

            # Persist token
            self.auth.persist_access_token(access_token)

            print("✅ Login successful! Token saved to .env")
            return True

        except Exception as e:
            print(f"\n❌ Login failed: {e}")
            print("\nTroubleshooting:")
            print("1. Make sure you copied the request_token correctly")
            print("2. The request_token expires quickly - complete login within 2-3 minutes")
            print("3. Check your API key and secret are correct")
            return False

    def select_mode(self) -> str:
        """Select trading mode"""
        print("\n" + "=" * 70)
        print("    ⚙️  SELECT TRADING MODE")
        print("=" * 70)

        current_mode = os.getenv("APP_MODE", "PAPER")
        print(f"\nCurrent mode: {current_mode}")

        print("\nAvailable modes:")
        print("  1. PAPER  - Simulated trading (safe, no real money)")
        print("  2. LIVE   - Real trading (WARNING: uses real money!)")

        while True:
            choice = input("\nSelect mode (1 for PAPER, 2 for LIVE) [1]: ").strip() or "1"

            if choice == "1":
                return "PAPER"
            elif choice == "2":
                # Require confirmation for LIVE mode
                print("\n⚠️  WARNING: LIVE mode will execute real trades with real money!")
                confirm = input("Type 'CONFIRM LIVE TRADING' to proceed: ").strip()

                if confirm == "CONFIRM LIVE TRADING":
                    return "LIVE"
                else:
                    print("❌ LIVE mode not confirmed. Defaulting to PAPER mode.")
                    return "PAPER"
            else:
                print("❌ Invalid choice. Please enter 1 or 2.")

    def update_env_mode(self, mode: str):
        """Update APP_MODE in .env file"""
        env_file = Path(".env")

        if env_file.exists():
            with open(env_file, 'r') as f:
                content = f.read()

            # Update or append APP_MODE
            if 'APP_MODE=' in content:
                import re
                content = re.sub(r'APP_MODE=.*', f'APP_MODE={mode}', content)
            else:
                content += f"\nAPP_MODE={mode}"

            with open(env_file, 'w') as f:
                f.write(content)

            print(f"✅ Updated APP_MODE to {mode} in .env")
        else:
            print("⚠️  .env file not found. Mode will be set for this session only.")

        # Also set in environment for current session
        os.environ["APP_MODE"] = mode

    def start_trading_system(self):
        """Start the trading API server"""
        print("\n" + "=" * 70)
        print("    🚀 STARTING TRADING SYSTEM")
        print("=" * 70)

        mode = os.getenv("APP_MODE", "PAPER")
        print(f"\nMode: {mode}")
        print(f"Port: {self.api_port}")

        if mode == "LIVE":
            print("\n⚠️  ⚠️  ⚠️  LIVE MODE - REAL MONEY TRADING ⚠️  ⚠️  ⚠️")

        print("\nStarting API server...")
        print(f"\nAPI endpoints will be available at:")
        print(f"  - Health:     http://localhost:{self.api_port}/health")
        print(f"  - Status:     http://localhost:{self.api_port}/state")
        print(f"  - Positions:  http://localhost:{self.api_port}/positions")
        print(f"  - Risk:       http://localhost:{self.api_port}/risk")
        print(f"  - Metrics:    http://localhost:{self.api_port}/metrics")
        print(f"  - API Docs:   http://localhost:{self.api_port}/docs")

        print("\n" + "=" * 70)
        print("Press Ctrl+C to stop the trading system")
        print("=" * 70 + "\n")

        # Start the API server
        try:
            subprocess.run([
                sys.executable,
                "-m",
                "uvicorn",
                "apps.api.main:app",
                "--host", os.getenv("API_HOST", "0.0.0.0"),
                "--port", str(self.api_port),
                "--reload" if os.getenv("RELOAD", "false").lower() == "true" else "--no-reload"
            ])
        except KeyboardInterrupt:
            print("\n\n🛑 Trading system stopped")

    def show_status(self):
        """Show current status"""
        print("\n" + "=" * 70)
        print("    📊 STATUS")
        print("=" * 70)

        # Session status
        valid = self.check_session()

        # Mode
        mode = os.getenv("APP_MODE", "PAPER")
        print(f"\n📍 Trading Mode: {mode}")

        # API Key
        if self.auth.api_key:
            print(f"🔑 API Key: {self.auth.api_key[:8]}...")
        else:
            print("🔑 API Key: Not set")

        # Access Token
        if self.auth.access_token:
            print(f"🎫 Access Token: Set (valid: {valid})")
        else:
            print("🎫 Access Token: Not set")

        # User ID
        user_id = os.getenv("KITE_USER_ID")
        if user_id:
            print(f"👤 User ID: {user_id}")

        print("\n" + "=" * 70)

    def run(self, args):
        """Main run loop"""
        self.print_banner()

        # Handle different commands
        if args.status:
            self.show_status()
            return

        if args.login_only:
            # Just login
            if self.login():
                print("\n✅ Login complete!")
            else:
                print("\n❌ Login failed")
                sys.exit(1)
            return

        # Full flow: check session -> login if needed -> select mode -> start

        # Step 1: Check session
        if not self.check_session():
            print("\n⚠️  You need to login first")
            if not self.login():
                print("\n❌ Unable to proceed without valid login")
                sys.exit(1)

        # Step 2: Select mode (unless --mode provided)
        if args.mode:
            mode = args.mode.upper()
            if mode not in ["PAPER", "LIVE"]:
                print(f"❌ Invalid mode: {mode}. Must be PAPER or LIVE")
                sys.exit(1)

            if mode == "LIVE":
                print("\n⚠️  WARNING: LIVE mode will execute real trades!")
                confirm = input("Type 'CONFIRM LIVE TRADING' to proceed: ").strip()
                if confirm != "CONFIRM LIVE TRADING":
                    print("❌ LIVE mode not confirmed. Exiting.")
                    sys.exit(1)
        else:
            mode = self.select_mode()

        # Update mode in .env
        self.update_env_mode(mode)

        # Step 3: Start trading system (unless --no-start)
        if not args.no_start:
            time.sleep(1)  # Brief pause
            self.start_trading_system()
        else:
            print("\n✅ Setup complete! Use --status to check status anytime.")
            print(f"\nTo start trading, run:")
            print(f"  python kite_trader.py")


def main():
    parser = argparse.ArgumentParser(
        description="Kite Trader - Simple CLI tool to login and start trading",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full flow: login, select mode, and start trading
  python kite_trader.py

  # Just login (don't start trading)
  python kite_trader.py --login-only

  # Start with specific mode
  python kite_trader.py --mode PAPER

  # Check status
  python kite_trader.py --status

  # Setup but don't start (useful for CI/CD)
  python kite_trader.py --no-start --mode PAPER
        """
    )

    parser.add_argument(
        "--login-only",
        action="store_true",
        help="Only perform login, don't start trading system"
    )

    parser.add_argument(
        "--mode",
        choices=["PAPER", "LIVE", "paper", "live"],
        help="Trading mode (PAPER or LIVE)"
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current status and exit"
    )

    parser.add_argument(
        "--no-start",
        action="store_true",
        help="Don't start the trading system (setup only)"
    )

    args = parser.parse_args()

    trader = KiteTrader()
    trader.run(args)


if __name__ == "__main__":
    main()
