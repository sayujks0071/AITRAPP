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

# Defaults now read from environment for security; no hardcoded credentials.
DEFAULT_API_KEY = os.getenv("KITE_API_KEY")
DEFAULT_API_SECRET = os.getenv("KITE_API_SECRET")
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

def update_env_file(access_token, user_id, mode):
    env_path = os.path.join(os.getcwd(), ".env")
    if not os.path.exists(env_path):
        print(f"⚠️  .env file not found at {env_path}")
        return

    with open(env_path, "r") as f:
        lines = f.readlines()

    new_lines = []
    keys_updated = {"KITE_ACCESS_TOKEN": False, "KITE_USER_ID": False, "KITE_TOKEN_CREATED_AT_ISO": False}

    current_time = datetime.now().isoformat()

    for line in lines:
        # Preserve lines without '=', empty lines, and full-line comments as-is
        stripped = line.lstrip()
        if "=" not in line or stripped.startswith("#") or stripped.strip() == "":
            new_lines.append(line)
            continue

        # Split into key and value once; preserve the original value/comment suffix where possible
        key_part, value_part = line.split("=", 1)
        key = key_part.strip()

        # Extract any inline comment suffix (e.g., "value  # comment")
        comment_suffix = ""
        if "#" in value_part:
            value_body, inline_comment = value_part.split("#", 1)
            comment_suffix = "#" + inline_comment.rstrip("\n")
        else:
            value_body = value_part.rstrip("\n")

        if key == "KITE_ACCESS_TOKEN":
            new_line = f"{key}=({access_token})"
            if comment_suffix:
                # Ensure a space before the inline comment if not already present
                if not comment_suffix.startswith(" "):
                    new_line += " "
                new_line += comment_suffix
            new_lines.append(new_line + "\n")
            keys_updated["KITE_ACCESS_TOKEN"] = True
        elif key == "KITE_USER_ID":
            new_line = f"{key}={user_id}"
            if comment_suffix:
                if not comment_suffix.startswith(" "):
                    new_line += " "
                new_line += comment_suffix
            new_lines.append(new_line + "\n")
            keys_updated["KITE_USER_ID"] = True
        elif key == "KITE_TOKEN_CREATED_AT_ISO":
            new_line = f"{key}={current_time}"
            if comment_suffix:
                if not comment_suffix.startswith(" "):
                    new_line += " "
                new_line += comment_suffix
            new_lines.append(new_line + "\n")
            keys_updated["KITE_TOKEN_CREATED_AT_ISO"] = True
        else:
            # For other keys, leave the line unchanged
            new_lines.append(line)

    # Append if not found
    if not keys_updated["KITE_ACCESS_TOKEN"]:
        new_lines.append(f"KITE_ACCESS_TOKEN={access_token}\n")
    if not keys_updated["KITE_USER_ID"]:
        new_lines.append(f"KITE_USER_ID={user_id}\n")
    if not keys_updated["KITE_TOKEN_CREATED_AT_ISO"]:
        new_lines.append(f"KITE_TOKEN_CREATED_AT_ISO={current_time}\n")

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
