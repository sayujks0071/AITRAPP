#!/usr/bin/env python3
"""
Proxy Health Check Script
==========================

Verifies that API calls are routing through the whitelisted static IP proxy
before market open. This ensures SEBI/NSE compliance (static IP requirement).

Usage:
    python scripts/check_proxy_health.py
    
    # With custom proxy
    PROXY_URL=http://user:pass@ELASTIC_IP:3128 python scripts/check_proxy_health.py
    
    # With expected IP
    EXPECTED_IP=1.2.3.4 python scripts/check_proxy_health.py

Requirements:
    - Proxy must be configured and accessible
    - Expected static IP must be whitelisted in Zerodha developer console
"""

import os
import sys
import json
import requests
from typing import Optional, Dict, Any
from urllib.parse import urlparse

# Try to load from .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def get_egress_ip(proxy_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Get the egress IP address (what the broker sees).
    
    Args:
        proxy_url: Optional proxy URL (http://user:pass@host:port)
        
    Returns:
        Dict with 'ip', 'country', 'city', 'proxy_used', 'error'
    """
    proxies = None
    if proxy_url:
        proxies = {
            "http": proxy_url,
            "https": proxy_url,
        }
    
    # Use multiple services for redundancy
    ip_services = [
        "https://api.ipify.org?format=json",
        "https://ifconfig.me/all.json",
        "https://ipapi.co/json/",
    ]
    
    for service_url in ip_services:
        try:
            response = requests.get(service_url, proxies=proxies, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            # Different services return different formats
            ip = (
                data.get("ip") or 
                data.get("origin") or 
                data.get("query")
            )
            
            if ip:
                return {
                    "ip": ip,
                    "country": data.get("country", data.get("country_name", "N/A")),
                    "city": data.get("city", "N/A"),
                    "proxy_used": proxy_url is not None,
                    "service": service_url,
                    "error": None
                }
        except Exception as e:
            continue
    
    return {
        "ip": None,
        "country": None,
        "city": None,
        "proxy_used": proxy_url is not None,
        "service": None,
        "error": "All IP services failed"
    }


def verify_proxy_configuration() -> Dict[str, Any]:
    """
    Verify proxy configuration from environment.
    
    Returns:
        Dict with proxy_url, expected_ip, status
    """
    proxy_url = os.getenv("PROXY_URL") or os.getenv("KITE_PROXY_URL")
    expected_ip = os.getenv("EXPECTED_IP") or os.getenv("KITE_WHITELISTED_IP")
    
    return {
        "proxy_url": proxy_url,
        "expected_ip": expected_ip,
        "proxy_configured": proxy_url is not None,
        "expected_ip_configured": expected_ip is not None
    }


def main():
    """Main health check routine"""
    print("=" * 70)
    print("Proxy Health Check - SEBI/NSE Static IP Compliance")
    print("=" * 70)
    print()
    
    # 1. Check configuration
    config = verify_proxy_configuration()
    print("📋 Configuration:")
    print(f"   Proxy URL: {'✅ Set' if config['proxy_configured'] else '❌ Not set'}")
    print(f"   Expected IP: {config['expected_ip'] or '❌ Not set'}")
    print()
    
    if not config['proxy_configured']:
        print("⚠️  WARNING: No proxy configured!")
        print("   Set PROXY_URL or KITE_PROXY_URL environment variable")
        print("   Example: PROXY_URL=http://user:pass@ELASTIC_IP:3128")
        print()
        response = input("Continue without proxy? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # 2. Get egress IP (with proxy if configured)
    print("🔍 Checking egress IP...")
    result = get_egress_ip(config['proxy_url'])
    print()
    
    if result['error']:
        print(f"❌ ERROR: {result['error']}")
        sys.exit(1)
    
    # 3. Display results
    print("📊 Results:")
    print(f"   Egress IP: {result['ip']}")
    print(f"   Location: {result['city']}, {result['country']}")
    print(f"   Proxy Used: {'✅ Yes' if result['proxy_used'] else '❌ No'}")
    print()
    
    # 4. Verify against expected IP
    if config['expected_ip']:
        if result['ip'] == config['expected_ip']:
            print("✅ SUCCESS: Egress IP matches expected whitelisted IP")
            print(f"   IP: {result['ip']}")
            return 0
        else:
            print("❌ FAILURE: Egress IP does NOT match expected IP!")
            print(f"   Expected: {config['expected_ip']}")
            print(f"   Actual:   {result['ip']}")
            print()
            print("⚠️  ACTION REQUIRED:")
            print("   1. Verify proxy is correctly configured")
            print("   2. Check proxy is running and accessible")
            print("   3. Ensure Elastic IP is whitelisted in Zerodha console")
            print("   4. Wait 24h for IP whitelist to propagate")
            return 1
    else:
        print("⚠️  WARNING: No expected IP configured for verification")
        print("   Set EXPECTED_IP or KITE_WHITELISTED_IP to enable verification")
        print(f"   Current egress IP: {result['ip']}")
        print()
        print("💡 Tip: Whitelist this IP in Zerodha developer console")
        return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)






