# AI Build Prompt: AITRAPP

## Prompt (copy/paste)
BEGIN PROMPT
You are a senior software engineer. Build AITRAPP, an autonomous trading
application for India's NSE that integrates with Zerodha Kite Connect.
Deliver a working repo with production-grade safety controls, auditability,
and runbooks. The system must default to PAPER mode and only trade LIVE when
explicitly confirmed.

Primary goal
- Implement a full-stack backend trading system that matches the scope below.

Core tech stack
- Language: Python 3.11
- API: FastAPI with Uvicorn
- Persistence: PostgreSQL with SQLAlchemy + Alembic migrations
- Cache/lock/bus: Redis
- Monitoring: Prometheus metrics endpoint
- Config: YAML app config + environment variables via Pydantic Settings

Repository layout
- apps/api: FastAPI control plane
- packages/core: trading engine, market data, execution, risk, metrics
- packages/storage: database models and persistence helpers
- configs: app.yaml and strategy configs
- scripts/ops: operational scripts and runbooks
- docs: setup, compliance, backtesting, and runbooks

Functional requirements
1) Trading modes and safety
   - Support PAPER and LIVE modes.
   - LIVE mode must require the exact confirmation string:
     "CONFIRM LIVE TRADING".
   - Provide a kill switch endpoint to flatten all positions quickly.
   - Support pause/resume to stop new entries without closing open positions.
   - Implement pre-live gating using Day-2 scorer JSON with freshness checks,
     and block LIVE if JSON is missing or fails the gate.
   - Log mode changes and overrides into the audit log with config SHA and
     git head details.

2) Market data and orchestration
   - Use Kite WebSocket for tick data; aggregate bars (1s and 5s windows).
   - Provide a PAPER-mode tick simulator when no data connection is present.
   - Heartbeats: market data, order stream, and scan ticks.
   - Implement a trading orchestrator that:
     - scans the universe
     - generates signals via strategies
     - ranks signals
     - applies risk checks
     - places orders
     - manages exits and OCO siblings

3) Strategies
   - Implement base Strategy interface and at least:
     - ORB
     - TrendPullback
     - OptionsRanker
   - Strategy configs are loaded from configs/app.yaml.

4) Risk and execution
   - Risk controls:
     - per-trade risk percentage
     - portfolio heat limit
     - daily loss stop
     - slippage and fees
   - Execution engine:
     - order types (market, limit, SL, SLM)
     - limit chase and retry backoff
     - idempotent client order IDs
     - OCO management for bracket exits

5) Persistence and audit
   - Use Postgres tables for:
     - instruments, signals, decisions, orders, positions, trades,
       risk events, audit logs
   - Ensure deterministic IDs for idempotency.
   - Persist audit entries for key actions (mode change, kill switch,
     order placed/filled, position opened/closed, risk blocks).

6) Compliance checks
   - Provide a compliance status endpoint to validate:
     - static egress IP match
     - OAuth freshness
     - TOPS cap (orders per second)
     - algorithm ID presence
     - optional family-only whitelist

7) Observability
   - Structured JSON logs with timestamps.
   - Prometheus metrics with trader_* prefix for:
     - signals, decisions, orders, fills
     - portfolio heat and daily PnL
     - leader lock, heartbeats, scan latency
     - kill switch count and leader changes

API requirements
- Implement a FastAPI service with endpoints:
  - GET /health
  - GET /ready (must fail if leader lock or heartbeats are stale)
  - GET /compliance/status
  - POST /mode (requires confirmation for LIVE)
  - POST /pause
  - POST /resume
  - POST /flatten (kill switch)
  - GET /positions
  - POST /positions/{position_id}/close
  - GET /orders
  - GET /state
  - POST /universe/reload
  - POST /strategies/reload
  - POST /backtest
  - GET /metrics
  - GET /risk
  - GET / (root)
  - GET /auth/kite/callback (exchange request_token for access_token)

Configuration and environment
- configs/app.yaml must include sections:
  - mode, timezone
  - risk, universe, options_filters, strategies, ranking
  - exits, market, execution
  - alerts, websocket, logging, monitoring
- Required env vars include:
  - KITE_API_KEY, KITE_API_SECRET, KITE_ACCESS_TOKEN, KITE_USER_ID
  - DATABASE_URL, REDIS_URL, API_SECRET_KEY
  - APP_MODE, API_HOST, API_PORT

Operational tooling
- Provide Makefile targets or scripts for:
  - setup, migrations, start in PAPER, start in LIVE
  - pre-live gate checks, burn-in scoring
  - smoke tests, rollback, post-close procedures

Backtesting
- Implement a backtest engine that runs strategies on historical data
  and returns metrics, with an API endpoint to trigger it.

Definition of done
- The app starts in PAPER mode with dockerized Postgres and Redis.
- /health and /metrics respond after startup.
- /ready returns 503 when leader lock or heartbeats are stale.
- /mode blocks LIVE unless confirmation string is correct and gate passes.
- /flatten closes positions and pauses trading.
- Data model migrations apply cleanly.
- README and runbooks explain setup, tokens, and operations.
END PROMPT
