#!/usr/bin/env python3
"""
Kite Auth Bootstrap Script
- Starts a local server to handle the Kite Connect login callback.
- Captures the request_token automatically.
- Exchanges it for an access_token.
- Updates the local .env file.
"""

import http.server
import socketserver
import urllib.parse
import webbrowser
import threading
import sys
import os
import argparse
from datetime import datetime
from kiteconnect import KiteConnect

# Defaults from get_kite_token.py
DEFAULT_API_KEY = "nhe2vo0afks02ojs"
DEFAULT_API_SECRET = "cs82nkkdvin37nrydnyou6cwn2b8zojl"
REDIRECT_PORT = 8080
REDIRECT_PATH = "/callback"

captured_request_token = None

class CallbackHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        global captured_request_token
        parsed_url = urllib.parse.urlparse(self.path)
        if parsed_url.path == REDIRECT_PATH:
            query_params = urllib.parse.parse_qs(parsed_url.query)
            if "request_token" in query_params:
                captured_request_token = query_params["request_token"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>Login Successful</h1><p>You can close this window now. Return to your terminal.</p>")

                # Signal server to stop in a separate thread to avoid deadlock
                threading.Thread(target=self.server.shutdown).start()
            else:
                self.send_response(400)
                self.wfile.write(b"Missing request_token")
        else:
            self.send_response(404)
            self.wfile.write(b"Not Found")

    def log_message(self, format, *args):
        # Suppress logging to keep terminal clean
        pass

def validate_credentials_for_mode(api_key, api_secret, mode):
    """
    Validate that the API credentials match the intended trading mode.
    This helps prevent accidentally using LIVE credentials in PAPER mode or vice versa.
    
    Note: This is a best-effort validation. The Kite API doesn't provide a direct way
    to determine if credentials are for PAPER or LIVE, but we can check against
    known defaults and provide warnings.
    """
    # Known PAPER mode defaults (from get_kite_token.py)
    PAPER_API_KEY = "nhe2vo0afks02ojs"
    PAPER_API_SECRET = "cs82nkkdvin37nrydnyou6cwn2b8zojl"
    
    is_using_paper_defaults = (api_key == PAPER_API_KEY and api_secret == PAPER_API_SECRET)
    
    if mode == "PAPER" and not is_using_paper_defaults:
        print("\n⚠️  WARNING: You're authenticating for PAPER mode but using custom API credentials.")
        print("    Make sure these credentials are for PAPER trading, not LIVE trading.")
        print(f"    API Key: {api_key[:10]}...")
        
        if sys.stdin.isatty():
            confirmation = input("\n    Continue? (y/N): ")
            if confirmation.lower() != 'y':
                print("❌ Aborted by user.")
                sys.exit(1)
    
    elif mode == "LIVE" and is_using_paper_defaults:
        print("\n❌ ERROR: You're trying to authenticate for LIVE mode but using PAPER credentials.")
        print("    LIVE trading requires your own Kite Connect API key and secret.")
        print("    Please set KITE_API_KEY and KITE_API_SECRET environment variables with your LIVE credentials.")
        sys.exit(1)

def update_env_file(access_token, user_id, mode):
    env_path = os.path.join(os.getcwd(), ".env")
    if not os.path.exists(env_path):
        print(f"⚠️  .env file not found at {env_path}")
        return

    with open(env_path, "r") as f:
        lines = f.readlines()

    new_lines = []
    keys_updated = {
        "KITE_ACCESS_TOKEN": False, 
        "KITE_USER_ID": False, 
        "KITE_TOKEN_CREATED_AT_ISO": False,
        "APP_MODE": False
    }

    current_time = datetime.now().isoformat()

    for line in lines:
        if "=" not in line:
            new_lines.append(line)
            continue

        key = line.split("=")[0].strip()
        if key == "KITE_ACCESS_TOKEN":
            new_lines.append(f"KITE_ACCESS_TOKEN={access_token}\n")
            keys_updated["KITE_ACCESS_TOKEN"] = True
        elif key == "KITE_USER_ID":
            new_lines.append(f"KITE_USER_ID={user_id}\n")
            keys_updated["KITE_USER_ID"] = True
        elif key == "KITE_TOKEN_CREATED_AT_ISO":
            new_lines.append(f"KITE_TOKEN_CREATED_AT_ISO={current_time}\n")
            keys_updated["KITE_TOKEN_CREATED_AT_ISO"] = True
        elif key == "APP_MODE":
            new_lines.append(f"APP_MODE={mode}\n")
            keys_updated["APP_MODE"] = True
        else:
            new_lines.append(line)

    # Append if not found
    if not keys_updated["KITE_ACCESS_TOKEN"]:
        new_lines.append(f"KITE_ACCESS_TOKEN={access_token}\n")
    if not keys_updated["KITE_USER_ID"]:
        new_lines.append(f"KITE_USER_ID={user_id}\n")
    if not keys_updated["KITE_TOKEN_CREATED_AT_ISO"]:
        new_lines.append(f"KITE_TOKEN_CREATED_AT_ISO={current_time}\n")
    if not keys_updated["APP_MODE"]:
        new_lines.append(f"APP_MODE={mode}\n")

    with open(env_path, "w") as f:
        f.writelines(new_lines)

    print(f"✅ Updated .env with new credentials (Mode: {mode})")

def main():
    parser = argparse.ArgumentParser(description="Kite Auth Bootstrap")
    parser.add_argument("--mode", choices=["PAPER", "LIVE"], default="PAPER", help="Trading mode (default: PAPER)")
    args = parser.parse_args()

    print("=" * 60)
    print(f"🚀 Kite Auth Bootstrap (Mode: {args.mode})")
    print("=" * 60)

    if args.mode == "LIVE":
        print("\n⚠️  WARNING: You are authenticating for LIVE TRADING.")
        print("This will update your credentials to allow real execution.")

        # In a non-interactive environment (like CI/CD or some shells), this might fail.
        # But this script is intended for manual bootstrap.
        if sys.stdin.isatty():
            confirmation = input("\nType 'LIVE' to confirm: ")
            if confirmation != "LIVE":
                print("❌ Confirmation failed. Exiting.")
                sys.exit(1)
        else:
            print("⚠️  Non-interactive mode detected. Proceeding with caution for LIVE mode.")

    # Try to load keys from env, otherwise use defaults
    # We don't load .env here automatically to avoid polluting environment if not needed,
    # but we should check if they are already in env (e.g. exported in shell).
    # If not, we can try to read .env just to get keys if they are there?
    # Actually, simpler to just use os.environ and fallback to defaults.

    api_key = os.environ.get("KITE_API_KEY", DEFAULT_API_KEY)
    api_secret = os.environ.get("KITE_API_SECRET", DEFAULT_API_SECRET)

    # Validate that credentials match the selected mode
    validate_credentials_for_mode(api_key, api_secret, args.mode)

    kite = KiteConnect(api_key=api_key)
    login_url = kite.login_url()

    print(f"\n1. Opening login URL in your browser...")
    print(f"   URL: {login_url}")

    try:
        webbrowser.open(login_url)
    except Exception:
        print("   (Please open the URL manually if it didn't open)")

    print(f"\n2. Waiting for callback on http://localhost:{REDIRECT_PORT}{REDIRECT_PATH}...")

    try:
        # allow_reuse_address is useful if we restart quickly
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", REDIRECT_PORT), CallbackHandler) as httpd:
            httpd.serve_forever()
    except OSError as e:
        if e.errno == 48: # Address already in use
            print(f"\n❌ Port {REDIRECT_PORT} is busy. Is the script already running?")
        else:
            print(f"\n❌ Error starting server: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user.")
        sys.exit(1)

    if captured_request_token:
        print(f"\n✅ Received request_token: {captured_request_token}")
        print("3. Exchanging for access_token...")
        try:
            data = kite.generate_session(captured_request_token, api_secret=api_secret)
            print(f"✅ Authentication successful!")

            update_env_file(data["access_token"], data["user_id"], args.mode)

            print("\n✨ Ready to trade! You can now start the application.")

        except Exception as e:
            print(f"\n❌ Error generating session: {e}")
            sys.exit(1)
    else:
        print("\n❌ Failed to capture request_token.")
        sys.exit(1)

if __name__ == "__main__":
    main()
