# Compliant Algorithmic Trading Architecture (NSE/SEBI 2025)

Guidance for retail/tech-savvy investors to build a Kite Connect trading stack that satisfies the 2025 SEBI/NSE retail algo controls while still developing locally in Cursor.

## 1) Why This Matters in 2025
- SEBI circular (Feb 2025) + NSE implementation standards (Aug 2025) end the unregulated retail-algo era.
- Retail API use is permitted, but only with traceable identity (static IP), throughput discipline (<10 OPS), mandatory tagging, and provable audit trails.
- The modern retail trader is treated as a professional operator; ad-hoc scripts on home Wi-Fi will be blocked.

## 2) Regulatory Pillars (What Must Exist)
- **Static IP identity**: Broker must see a whitelisted static IP for every API call; dynamic IP = 403/429.
- **Throughput boundary**: <10 orders/second per segment stays retail; >10 requires exchange registration + Algo ID.
- **Mandatory tagging**: All automated orders carry a tag (8 chars). Registered strategies must use the exchange Algo ID; retail algos should use a stable tag for audit trail.
- **Vendor/DIY separation**: Only exchange-empanelled vendors can sell/rout algos. DIY code is allowed but fully attributable to the client.

## 3) Static IP Options (choose one)
| Architecture | Effort | Latency | Compliance | Notes |
| --- | --- | --- | --- | --- |
| ISP static IP | Low (admin) | None | High | Expensive business plans; no redundancy. |
| Cloud VPS (headless) | Medium (DevOps) | Lower | High | Code runs remotely; develop via SSH/VS Code Remote. |
| Proxy tunneling (recommended) | Medium-High (network) | +5-20 ms | High | Code runs locally in Cursor; HTTP routed through cloud proxy with static IP. |

### AWS Proxy Tunneling (recommended hybrid)
1) Launch small EC2 in ap-south-1; attach Elastic IP.  
2) Install Squid/TinyProxy; lock Security Group to your current home IP on the proxy port (e.g., 3128).  
3) Whitelist the Elastic IP in the Zerodha developer console (24h SLA).  
4) Configure Python HTTP client to use the proxy:  
   ```python
   proxies = {
       "http": "http://user:pass@ELASTIC_IP:3128",
       "https": "http://user:pass@ELASTIC_IP:3128",
   }
   kite = KiteConnect(api_key=api_key, proxies=proxies)
   ```

## 4) Cursor/AI Security Hygiene
- Enable Cursor **Privacy Mode** to enforce zero data retention with LLM providers.
- Store credentials in `.env`; load via `python-dotenv`. Never hardcode keys/tokens/TOTP secrets.
- Add `.cursorignore` to exclude `.env`, secrets, logs, keys, and virtualenvs from LLM indexing (see repo root).

## 5) Kite Connect Authentication & Session
- Use `pyotp` to generate TOTP for headless login:  
  ```python
  totp = pyotp.TOTP(os.getenv("KITE_TOTP_SECRET"))
  otp = totp.now()
  ```
- Automate login (headless browser or direct POST) to capture `request_token`, then exchange for `access_token` via `kite.generate_session`.
- Persist a valid `access_token` for the trading day to avoid login flakiness at market open; refresh only when expired.

## 6) Order Routing & Safety
- Always set `tag` (<=8 chars). Use the exchange Algo ID if registered; otherwise use a stable retail tag (e.g., `R_ALGO1`).
- Prefer market-protected limit orders over pure market: price = `ltp * 1.01` for buys / `ltp * 0.99` for sells (tunable buffer).
- Keep SSL verification on when tunneling; avoid `disable_ssl`.

## 7) Rate Limiting (<10 OPS guardrail)
- Implement a **token bucket** (capacity 10, refill 10 tokens/sec; allow small burst e.g., 20). Protect with a `threading.Lock` if multi-threaded.
- On 429 errors, backoff exponentially (0.1s, 0.2s, 0.4s...) instead of hammering the gateway.

## 8) Risk Controls
- **Kill switch**: Set `TRADING_ACTIVE=False`, cancel all open orders, and (optionally) square off positions.
- **Circuit breakers**: Max loss guard (P&L threshold), loop detection (repeated orders in short window), heartbeat monitor (WebSocket down >60s triggers safe mode).
- Enforce margin/quantity/freeze checks before place_order; do not rely on broker rejection.

## 9) Audit & Observability
- Log to structured JSON with microsecond timestamps: function, params, tag, order_id, price/qty/symbol, decision context.
- Retain logs for regulatory inquiries; mirror to durable storage.  
- Alert on critical events (kill switch, login failure, loss breach) via Telegram/email.

## 10) Quick Compliance Checklist
| Requirement | Implementation | Status target |
| --- | --- | --- |
| Static IP | AWS proxy + Elastic IP whitelisted | Blocker |
| Throughput | Token bucket limiter (<10 OPS) | High |
| Tagging | `tag` set on every order (Algo ID if registered) | High |
| 2FA/TOTP | `pyotp` in automated login; persist daily token | High |
| Market protection | Buffered limit instead of pure market | High |
| Kill switch | Global flag + cancel/square-off routine | High |
| Audit trail | JSON logs + retention; alerting on failures | High |
| Data privacy | `.env` secrets + `.cursorignore` + Privacy Mode | Medium |
