#!/usr/bin/env python3
"""Quick script to generate Kite Connect access token"""
import sys
from kiteconnect import KiteConnect

API_KEY = "nhe2vo0afks02ojs"
API_SECRET = "cs82nkkdvin37nrydnyou6cwn2b8zojl"

def main():
    print("=" * 60)
    print("Kite Connect Access Token Generator")
    print("=" * 60)
    print(f"\nAPI Key: {API_KEY}")
    
    # Check if token provided as argument
    if len(sys.argv) > 1:
        request_token = sys.argv[1].strip()
        print(f"\nUsing request_token from command line")
    else:
        print("\n📝 Steps:")
        print("1. Visit this URL in your browser:")
        print(f"   https://kite.trade/connect/login?api_key={API_KEY}&v=3")
        print("\n2. Login with your Zerodha credentials")
        print("\n3. After login, you'll be redirected to a URL like:")
        print("   http://localhost:8080/callback?request_token=XXXXX&action=login&status=success")
        print("\n4. Copy the 'request_token' value from the URL")
        print("\n   Then run:")
        print("   python get_kite_token.py YOUR_REQUEST_TOKEN")
        print("=" * 60)
        
        if sys.stdin.isatty():
            request_token = input("\nPaste the request_token here: ").strip()
        else:
            print("\n❌ No request token provided.")
            print("\nUsage: python get_kite_token.py YOUR_REQUEST_TOKEN")
            print("\nOr visit the URL above and login first.")
            return
    
    if not request_token:
        print("❌ No request token provided. Exiting.")
        return
    
    try:
        kite = KiteConnect(api_key=API_KEY)
        data = kite.generate_session(request_token, api_secret=API_SECRET)
        
        print("\n" + "=" * 60)
        print("✅ SUCCESS! Your credentials:")
        print("=" * 60)
        print(f"\nAccess Token: {data['access_token']}")
        print(f"User ID: {data['user_id']}")
        print(f"\n📋 Add these to your .env file:")
        print(f"KITE_ACCESS_TOKEN={data['access_token']}")
        print(f"KITE_USER_ID={data['user_id']}")
        print("\n" + "=" * 60)
        
        # Auto-update .env file
        import os
        env_file = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                content = f.read()
            
            # Replace placeholders or existing values
            import re
            content = re.sub(r'KITE_ACCESS_TOKEN=.*', 
                           f"KITE_ACCESS_TOKEN={data['access_token']}", content)
            content = re.sub(r'KITE_USER_ID=.*', 
                           f"KITE_USER_ID={data['user_id']}", content)
            
            with open(env_file, 'w') as f:
                f.write(content)
            
            print("\n✅ .env file updated automatically!")
        else:
            print("\n⚠️  .env file not found - please update manually")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("1. You copied the request_token correctly")
        print("2. You logged in within the last few minutes")
        print("3. The request_token hasn't expired")

if __name__ == "__main__":
    main()

