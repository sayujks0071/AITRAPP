#!/usr/bin/env python3
"""
Kite Headless Login with TOTP (No Browser)
===========================================

Automates Kite login using user/password + TOTP to fetch a fresh access token.
Updates .env with new KITE_ACCESS_TOKEN (and optionally KITE_USER_ID).

Requirements:
  pip install requests pyotp python-dotenv

Environment (.env):
  KITE_API_KEY=...
  KITE_API_SECRET=...
  KITE_USER_ID=...
  KITE_PASSWORD=...
  KITE_TOTP_SECRET=...   # 32-char secret from Zerodha TOTP setup

Usage:
  python3 scripts/kite_headless_login.py
"""

import os
import sys
import json
import re
import time
from pathlib import Path
from urllib.parse import urlencode

import requests
import pyotp
from dotenv import load_dotenv
from kiteconnect import KiteConnect


KITE_LOGIN_URL = "https://kite.zerodha.com/api/login"
KITE_TWOFA_URL = "https://kite.zerodha.com/api/twofa"


def load_env():
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    return {
        "api_key": os.getenv("KITE_API_KEY"),
        "api_secret": os.getenv("KITE_API_SECRET"),
        "user_id": os.getenv("KITE_USER_ID"),
        "password": os.getenv("KITE_PASSWORD"),
        "totp_secret": os.getenv("KITE_TOTP_SECRET"),
        "env_path": env_path,
    }


def headless_login(api_key: str, user_id: str, password: str, totp_secret: str) -> str:
    """Perform headless login to obtain request_token."""
    session = requests.Session()
    # Step 1: login with user_id/password
    payload = {"user_id": user_id, "password": password}
    resp = session.post(f"{KITE_LOGIN_URL}?api_key={api_key}", data=payload, timeout=10)
    resp.raise_for_status()
    data = resp.json().get("data") or {}
    request_id = data.get("request_id")
    if not request_id:
        raise RuntimeError(f"Login failed: {resp.text}")
    # Step 2: TOTP submission
    otp = pyotp.TOTP(totp_secret).now()
    twofa_payload = {
        "user_id": user_id,
        "request_id": request_id,
        "twofa_value": otp,
        "twofa_type": "totp",
    }
    resp2 = session.post(f"{KITE_TWOFA_URL}?api_key={api_key}", data=twofa_payload, timeout=10)
    resp2.raise_for_status()
    data2 = resp2.json().get("data") or {}
    request_token = data2.get("request_token") or data2.get("login_token")
    if not request_token:
        raise RuntimeError(f"TOTP step failed: {resp2.text}")
    return request_token


def generate_access_token(api_key: str, api_secret: str, request_token: str) -> dict:
    kite = KiteConnect(api_key=api_key)
    return kite.generate_session(request_token, api_secret=api_secret)


def update_env(env_path: Path, access_token: str, user_id: str):
    content = ""
    if env_path.exists():
        content = env_path.read_text()
    def upsert(key: str, value: str, text: str) -> str:
        pattern = rf"^{key}=.*$"
        repl = f"{key}={value}"
        if re.search(pattern, text, flags=re.MULTILINE):
            return re.sub(pattern, repl, text, flags=re.MULTILINE)
        return text + ("" if text.endswith("\n") else "\n") + repl + "\n"
    content = upsert("KITE_ACCESS_TOKEN", access_token, content)
    if user_id:
        content = upsert("KITE_USER_ID", user_id, content)
    content = upsert("KITE_TOKEN_REFRESHED_AT", time.strftime("%Y-%m-%dT%H:%M:%S"), content)
    env_path.write_text(content)


def main():
    cfg = load_env()
    api_key = cfg["api_key"]
    api_secret = cfg["api_secret"]
    user_id = cfg["user_id"]
    password = cfg["password"]
    totp_secret = cfg["totp_secret"]
    env_path = cfg["env_path"]

    missing = [k for k,v in [("KITE_API_KEY", api_key), ("KITE_API_SECRET", api_secret),
                             ("KITE_USER_ID", user_id), ("KITE_PASSWORD", password),
                             ("KITE_TOTP_SECRET", totp_secret)] if not v]
    if missing:
        print(f"❌ Missing env vars: {', '.join(missing)}")
        sys.exit(1)

    try:
        req_token = headless_login(api_key, user_id, password, totp_secret)
        session_data = generate_access_token(api_key, api_secret, req_token)
        access_token = session_data.get("access_token")
        if not access_token:
            raise RuntimeError("No access_token in session response")
        update_env(env_path, access_token, user_id)
        print("✅ Access token refreshed (headless) and .env updated.")
    except Exception as e:
        print(f"❌ Headless login failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
