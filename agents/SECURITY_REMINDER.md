# ⚠️ SECURITY REMINDER - API Keys

## Immediate Actions Required

1. **DO NOT commit these keys to git**
   - They are already in your shell history
   - Consider rotating them if this repo is public

2. **Store keys securely:**
   ```bash
   # Option 1: Add to ~/.bashrc or ~/.zshrc (for your user only)
   export BINANCE_API_KEY="your_key"
   export BINANCE_API_SECRET="your_secret"
   
   # Option 2: Use a secrets manager
   # Option 3: Use .env file (ensure it's in .gitignore)
   ```

3. **Verify .gitignore includes:**
   - `.env`
   - `*.key`
   - `*.secret`
   - Any files containing keys

4. **Binance Security Settings:**
   - ✅ Enable IP whitelist (restrict to your server IP)
   - ✅ Disable withdrawals
   - ✅ Enable trading only
   - ✅ Use read-only keys for monitoring (if available)

## Current Keys (Session Only)

These are exported in your current shell session. They will be lost when you close the terminal.

To persist them (securely):
```bash
# Add to your shell profile (~/.zshrc or ~/.bashrc)
echo 'export BINANCE_API_KEY="sGxx4Ew7NpskzfhmgRhWWaBwGRQlgPNLGyZTdlGLTqoomBaJ1T01gS4ImLn9MdK9"' >> ~/.zshrc
echo 'export BINANCE_API_SECRET="CGgUGCTfbg3TXN7AycyxFd7YFFy1YYEjK8O2dKg7PBg3d1RmcxiD4BmLtBwzauZC"' >> ~/.zshrc
source ~/.zshrc
```

## If Keys Are Exposed

1. **Rotate immediately** in Binance API Management
2. **Revoke old keys**
3. **Check for unauthorized activity**
4. **Update all systems using the keys**

