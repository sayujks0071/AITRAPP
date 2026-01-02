#!/usr/bin/env python3
"""Kite Daily Auth Assistant.

Manual login is required. This script starts a local callback server,
exchanges request_token -> access_token, and persists it to .env without
printing the token.
"""

import datetime as dt
import os
import re
import sys
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, Optional

from kiteconnect import KiteConnect


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
DEFAULT_TIMEOUT_SEC = 180


def read_env_file(path: str) -> Dict[str, str]:
    env: Dict[str, str] = {}
    try:
        with open(path, "r") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[len("export ") :]
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if value and value[0] == value[-1] and value[0] in ("'", '"'):
                    value = value[1:-1]
                env[key] = value
    except FileNotFoundError:
        pass
    return env


def get_setting(key: str, env_file: Dict[str, str]) -> Optional[str]:
    return os.getenv(key) or env_file.get(key)


def upsert_env_var(contents: str, key: str, value: str) -> str:
    pattern = re.compile(rf"^(\s*export\s+)?{re.escape(key)}=.*$", re.MULTILINE)

    def repl(match: re.Match) -> str:
        prefix = match.group(1) or ""
        return f"{prefix}{key}={value}"

    if pattern.search(contents):
        return pattern.sub(repl, contents)
    if contents and not contents.endswith("\n"):
        contents += "\n"
    return contents + f"{key}={value}\n"


def update_env_file(path: str, updates: Dict[str, str]) -> None:
    try:
        with open(path, "r") as handle:
            contents = handle.read()
    except FileNotFoundError:
        contents = ""

    for key, value in updates.items():
        contents = upsert_env_var(contents, key, value)

    with open(path, "w") as handle:
        handle.write(contents)


class TokenServer(HTTPServer):
    def __init__(self, server_address, request_handler_class, event: threading.Event):
        super().__init__(server_address, request_handler_class)
        self.event = event
        self.request_token: Optional[str] = None
        self.request_error: Optional[str] = None


class TokenHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args) -> None:
        # Silence default request logging to avoid leaking query strings.
        return

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        token = params.get("request_token", [None])[0]
        status = params.get("status", [None])[0]

        if token:
            self.server.request_token = token
            self.server.event.set()
            self._respond(200, "Authentication complete. You can close this tab.")
            return

        if status and status.lower() != "success":
            self.server.request_error = f"Login failed (status={status})."
            self.server.event.set()
            self._respond(400, "Login failed. Check the terminal for details.")
            return

        self._respond(400, "Missing request_token. Check the login flow.")

    def _respond(self, code: int, message: str) -> None:
        body = (
            "<html><head><title>Kite Auth</title></head>"
            f"<body><h3>{message}</h3></body></html>"
        )
        body_bytes = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.end_headers()
        self.wfile.write(body_bytes)


def main() -> int:
    env_path = os.getenv("KITE_ENV_FILE", ".env")
    env_file = read_env_file(env_path)

    trading_mode = get_setting("TRADING_MODE", env_file)
    app_mode = get_setting("APP_MODE", env_file)
    if trading_mode or app_mode:
        mode = (trading_mode or app_mode).upper()
    else:
        mode = "PAPER"
        print("TRADING_MODE/APP_MODE not set; defaulting to PAPER.")
    if mode not in {"PAPER", "LIVE"}:
        print(f"Warning: Unrecognized TRADING_MODE/APP_MODE={mode}. Proceeding anyway.")
    elif mode == "LIVE":
        print("Warning: TRADING_MODE/APP_MODE=LIVE. Proceeding with token bootstrap.")

    api_key = get_setting("KITE_API_KEY", env_file)
    api_secret = get_setting("KITE_API_SECRET", env_file)
    if not api_key or not api_secret:
        print("Missing KITE_API_KEY or KITE_API_SECRET in environment or .env.")
        return 1

    host = os.getenv("KITE_AUTH_HOST", env_file.get("KITE_AUTH_HOST", DEFAULT_HOST))
    port_raw = os.getenv("KITE_AUTH_PORT", env_file.get("KITE_AUTH_PORT", str(DEFAULT_PORT)))
    timeout_raw = os.getenv(
        "KITE_AUTH_TIMEOUT_SEC", env_file.get("KITE_AUTH_TIMEOUT_SEC", str(DEFAULT_TIMEOUT_SEC))
    )

    try:
        port = int(port_raw)
        timeout = int(timeout_raw)
    except ValueError:
        print("Invalid KITE_AUTH_PORT or KITE_AUTH_TIMEOUT_SEC.")
        return 1

    login_url = f"https://kite.trade/connect/login?api_key={api_key}&v=3"
    callback_url = f"http://{host}:{port}/callback"

    print("Manual login required. This script does not automate credentials.")
    print(f"Callback URL must be configured in Kite Connect: {callback_url}")
    print(f"Login URL: {login_url}")

    event = threading.Event()
    try:
        server = TokenServer((host, port), TokenHandler, event)
    except OSError as exc:
        print(f"Failed to start callback server on {host}:{port}: {exc}")
        return 1

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        webbrowser.open(login_url, new=1, autoraise=True)
    except Exception:
        pass

    print(f"Waiting for request_token (timeout {timeout}s)...")
    if not event.wait(timeout):
        server.shutdown()
        server.server_close()
        print("Timed out waiting for request_token. Try again.")
        return 1
    
    server.shutdown()
    server.server_close()
    if server.request_error:
        print(server.request_error)
        return 1
    if not server.request_token:
        print("No request_token received.")
        return 1

    print("Request token received. Exchanging for access token...")
    try:
        kite = KiteConnect(api_key=api_key)
        data = kite.generate_session(server.request_token, api_secret=api_secret)
    except Exception as exc:
        print(f"Token exchange failed: {exc}")
        return 1

    access_token = data.get("access_token")
    user_id = data.get("user_id")
    if not access_token or not user_id:
        print("Token exchange response missing access_token or user_id.")
        return 1

    issued_iso = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    update_env_file(
        env_path,
        {
            "KITE_ACCESS_TOKEN": access_token,
            "KITE_USER_ID": user_id,
            "KITE_TOKEN_CREATED_AT_ISO": issued_iso,
        },
    )

    print(f"Updated {env_path} with new Kite session (token not printed).")
    print(f"User ID: {user_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
