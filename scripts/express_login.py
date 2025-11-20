#!/usr/bin/env python3
"""
Express Login - Entry Point
============================

This is a convenience wrapper that calls kite_express_login.py
with support for --redirect-url for non-interactive use.

Usage:
    python3 scripts/express_login.py
    python3 scripts/express_login.py --redirect-url "http://localhost:8080/callback?request_token=..."
"""

import sys
import argparse
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Import the main login script
sys.path.insert(0, str(Path(__file__).parent))
from kite_express_login import extract_token_from_url, main

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Express login for Kite Connect",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--redirect-url",
        type=str,
        help="Full redirect URL from Kite login (non-interactive mode)"
    )
    
    parser.add_argument(
        "--request-token",
        type=str,
        help="Request token directly (skip browser prompt)"
    )
    
    args = parser.parse_args()
    
    # If redirect URL is provided, extract token and pass as --request-token
    if args.redirect_url:
        token = extract_token_from_url(args.redirect_url)
        if not token:
            print("❌ Could not extract request_token from redirect URL")
            sys.exit(1)
        # Override sys.argv to pass token to main script
        sys.argv = [sys.argv[0], "--request-token", token]
    elif args.request_token:
        # Pass request token directly to main script
        sys.argv = [sys.argv[0], "--request-token", args.request_token]
    
    main()
