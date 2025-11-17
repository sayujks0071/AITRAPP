# Crypto Security & IP Lock Setup

## IP Lock (Recommended for LIVE)

If your exchange API key supports IP whitelisting, restrict it to your runner's public IP.

### Kraken IP Lock

1. **Get your runner's public IP:**
   ```bash
   curl -s https://api.ipify.org
   ```

2. **Configure IP restriction in Kraken:**
   - Log into Kraken account
   - Navigate to Security → API Keys
   - Edit your API key
   - Add IP restriction: `YOUR_PUBLIC_IP/32`
   - Save changes

3. **Verify IP lock:**
   ```bash
   # Test from runner
   curl -s https://api.kraken.com/0/public/Time
   
   # Test from different IP (should fail)
   # Use a VPN or different machine
   ```

### Binance IP Lock

1. **Get your runner's public IP:**
   ```bash
   curl -s https://api.ipify.org
   ```

2. **Configure IP whitelist in Binance:**
   - Log into Binance account
   - Navigate to API Management
   - Edit your API key
   - Add IP whitelist: `YOUR_PUBLIC_IP`
   - Save changes

### Notes

- **Self-hosted runners**: IP lock is highly recommended
- **Dynamic IPs**: If your runner's IP changes, you'll need to update the whitelist
- **Multiple runners**: Add all runner IPs to the whitelist
- **Backup access**: Keep a separate API key without IP lock for emergency access

## API Key Security

### Best Practices

1. **Separate keys for PAPER and LIVE**
   - Use different API keys for testing and production
   - Rotate keys periodically (every 90 days)

2. **Minimal permissions**
   - Only grant necessary permissions (e.g., spot trading, read-only balance)
   - Do NOT grant withdrawal permissions

3. **Environment variables**
   - Never commit API keys to git
   - Use secrets management (GitHub Secrets, Vault, etc.)
   - Rotate keys if accidentally exposed

4. **Key rotation**
   ```bash
   # Rotate keys (example)
   # 1. Generate new key in exchange
   # 2. Update secrets in GitHub/runner
   # 3. Test with PAPER mode
   # 4. Switch to LIVE after verification
   # 5. Revoke old key after 24h grace period
   ```

## Network Security

### Firewall Rules

- **Inbound**: Only allow necessary ports (8000 for API, 9090 for Prometheus)
- **Outbound**: Allow HTTPS to exchange APIs and WebSocket connections
- **VPN**: Consider using VPN for additional security layer

### WebSocket Security

- **TLS**: All WebSocket connections use WSS (TLS)
- **Certificate validation**: Verify exchange certificates
- **Reconnect backoff**: Exponential backoff prevents DDoS-like behavior

## Monitoring & Alerts

### Security Alerts

- **API key rotation**: Alert 7 days before key expiration
- **Unusual activity**: Alert on unexpected order patterns
- **IP changes**: Alert if runner IP changes unexpectedly

### Access Logs

- **Audit trail**: All API calls are logged
- **Retention**: 90 days minimum
- **Review**: Weekly review of access logs

## Incident Response

### If API Key Compromised

1. **Immediate actions:**
   ```bash
   # Flatten all positions
   curl -X POST http://localhost:8000/flatten
   
   # Revoke compromised key in exchange
   # Generate new key
   # Update secrets
   ```

2. **Investigation:**
   - Review audit logs
   - Check for unauthorized orders
   - Verify account balance

3. **Recovery:**
   - Rotate to new key
   - Verify all systems
   - Resume trading after verification

## Compliance

### SEBI-Style Guardrails

- **Manual gates**: No automated LIVE switches
- **Audit trail**: All decisions logged
- **Risk limits**: Conservative limits enforced
- **24/7 monitoring**: Continuous monitoring required


