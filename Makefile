.PHONY: help dev paper paper-start paper-boot paper-stop live stop stop-docker clean test test-integration test-replay lint format install ops-smoke ops-smoke-no-ui ops-verify-cors ops-verify-preflight ops-verify-expose ops-smoke-proxy

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ''
	@echo 'Ops Browser Commands:'
	@echo '  ops-smoke          - API + UI smoke test'
	@echo '  ops-smoke-no-ui    - API-only smoke test (SKIP_UI_CHECK=true)'
	@echo '  ops-smoke-proxy    - Production smoke test (API behind proxy)'
	@echo '  ops-verify-cors    - Verify CORS headers on all endpoints'
	@echo '  ops-verify-preflight - Verify OPTIONS preflight CORS headers'
	@echo '  ops-verify-expose  - Verify Access-Control-Expose-Headers'

install: ## Install Python dependencies
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

install-web: ## Install Node dependencies for web dashboard
	cd apps/web && npm install

dev: ## Start development environment (Docker)
	docker-compose up -d postgres redis
	@echo "Development infrastructure started"
	@echo "Postgres: localhost:5432"
	@echo "Redis: localhost:6379"

up-infra: ## Start infrastructure services (Postgres + Redis)
	@echo "Starting AITRAPP infrastructure..."
	docker-compose up -d postgres redis
	@echo "Waiting for services to be healthy..."
	@sleep 3
	@docker-compose ps
	@echo ""
	@echo "✅ Infrastructure started"
	@echo "Postgres: localhost:5432"
	@echo "Redis: localhost:6379"

paper: ## Run in PAPER mode (safe simulation) - foreground
	@echo "Starting in PAPER MODE (simulation only)"
	@if [ -d "venv" ]; then \
		echo "Using virtual environment..."; \
		source venv/bin/activate; \
	fi; \
	PORT=$${PORT:-8000}; \
	export APP_MODE=PAPER; \
	python -m uvicorn apps.api.main:app --host 0.0.0.0 --port $$PORT

paper-start: ## Start paper API in background (logs to logs/api_8000.log)
	@scripts/start_paper_api.sh

paper-boot: ## Morning bootstrap: start paper API and verify health/ready
	@scripts/morning_paper_boot.sh

paper-stop: ## Stop paper API (by PID or port)
	@scripts/stop_paper_api.sh

live: ## Run in LIVE mode (⚠️ REAL TRADING - USE WITH CAUTION)
	@echo "╔════════════════════════════════════════════════╗"
	@echo "║         ⚠️  LIVE TRADING MODE WARNING  ⚠️      ║"
	@echo "╠════════════════════════════════════════════════╣"
	@echo "║  This will execute REAL trades with REAL money ║"
	@echo "║  Losses can exceed your expectations           ║"
	@echo "║  Type exactly: CONFIRM LIVE TRADING            ║"
	@echo "╚════════════════════════════════════════════════╝"
	@read -p "Confirmation: " confirm; \
	if [ "$$confirm" = "CONFIRM LIVE TRADING" ]; then \
		export APP_MODE=LIVE && python -m apps.api.main; \
	else \
		echo "❌ Confirmation failed. Aborting."; \
		exit 1; \
	fi

stop: paper-stop ## Stop all services (API + Docker)
	@docker-compose down

stop-docker: ## Stop only Docker services
	@docker-compose down

clean: ## Clean up containers and volumes
	docker-compose down -v
	rm -rf logs/*.log
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

test: ## Run unit tests
	pytest tests/unit -v --cov=packages --cov=apps --cov-report=term-missing

test-integration: ## Run integration tests
	pytest tests/integration -v --cov=packages --cov=apps

test-replay: ## Run replay tests on historical data
	pytest tests/replay -v

lint: ## Run linters
	ruff check packages apps
	mypy packages apps

format: ## Format code
	ruff format packages apps
	ruff check --fix packages apps

migrate: ## Run database migrations
	alembic upgrade head

burnin-report: ## Generate daily trading report
	python scripts/daily_report.py --date $$(date +%Y-%m-%d)

verify-env: ## Verify environment and connectivity
	python scripts/verify_env.py

health-check: ## Run comprehensive infrastructure health check
	python3 scripts/health_check.py

verify-r1: ## Verify R1 Regime-Switching Volatility Engine is loaded and working
	python3 scripts/verify_r1.py

test-r1-routing: ## Test R1 routing to A-G strategies (usage: make test-r1-routing UNDERLYING=BANKNIFTY)
	@bash scripts/test_r1_routing.sh $${UNDERLYING:-BANKNIFTY}

verify-g1: ## Verify G1 Gamma Scalper is loaded and working
	python3 scripts/verify_g1.py

verify-t1: ## Verify T1 Calendar Arb is loaded and working
	python3 scripts/verify_t1.py

verify-d1: ## Verify D1 Dispersion Arb is loaded and working
	python3 scripts/verify_d1.py

verify-allocator: ## Verify Strategy Allocator is loaded and working
	python3 scripts/verify_allocator.py

verify-h1: ## Verify H1 Tail Short Vol Overlay is loaded and working
	python3 scripts/verify_h1.py

verify-e1: ## Verify E1 Event Vol Engine is loaded and working
	python3 scripts/verify_e1.py

daily-report: ## Generate daily trading report
	python3 scripts/generate_daily_report.py

sanity-check: ## Quick sanity check of all strategy metrics
	@python3 scripts/quick_sanity_check.py

commit-configs: ## Commit config changes (usage: make commit-configs MSG="tune: R1 bands")
	@if [ -z "$(MSG)" ]; then \
		echo "❌ Usage: make commit-configs MSG='tune: description'"; \
		exit 1; \
	fi; \
	./scripts/commit_configs.sh "$(MSG)"

save-snapshot: ## Save daily snapshot (report + sanity check + configs)
	@./scripts/save_daily_snapshot.sh

sanity-check-position-store: ## Sanity check position store with round-trip test
	python3 scripts/sanity_check_position_store.py

dry-run-playbook: ## Dry run PAPER playbook (rehearsal, no markets needed)
	python3 scripts/dry_run_paper_playbook.py

smoke-test: ## Run 60-minute smoke test
	bash scripts/smoke_test.sh

rollback: ## Rollback from LIVE to PAPER
	bash scripts/rollback.sh

red-team-drills: ## Run red-team resilience drills
	bash scripts/red_team_drills.sh

failure-drills: ## Run failure drills (dual-runner, WS flap, band jump)
	bash scripts/failure_drills.sh

post-close: ## Run post-close hygiene (DB snapshot, archive logs, latency summary)
	bash scripts/post_close_hygiene.sh

live-dashboard: ## Create tmux dashboard for LIVE monitoring
	bash ops/live.sh dashboard

live-precheck: ## Run canary pre-check before LIVE switch
	bash ops/canary_precheck.sh

live-switch: ## Switch to LIVE mode
	bash ops/live.sh switch

live-full: prelive-gate ## Full LIVE sequence (gate → switch → monitor)
	bash ops/live.sh full

abort: ## Immediate abort (pause + flatten + PAPER)
	bash ops/abort.sh

paper-e2e: ## Run 30-minute PAPER end-to-end test
	python scripts/paper_e2e.py

prelive-gate: ## Run pre-LIVE gate checks (blocks switch if tripwires triggered)
	bash scripts/prelive_gate.sh

smoke-check: ## Run 2-minute smoke test after migration
	bash scripts/smoke_check.sh

quick-sanity: ## Run quick sanity checks (enum, column, endpoints)
	bash scripts/quick_sanity.sh

migration-checklist: ## Run complete migration checklist
	bash scripts/run_migration_checklist.sh

start-paper: ## Start complete PAPER session (automated)
	bash scripts/start_paper_session.sh

# Crypto-related targets removed - focusing on NSE only
# crypto-paper: ## (REMOVED - NSE focus only)
# score-crypto-day1: ## (REMOVED - NSE focus only)

watch-metrics: ## Watch key metrics (leader, heartbeats, errors) - generic for Kite/Crypto
	@watch -n 5 'curl -s http://localhost:8000/metrics 2>/dev/null | grep -E "^trader_(is_leader|.*heartbeat.*|.*errors.*|oco_orphans_total)" | sort' || echo "⚠️  API not running or watch command not available"

# Crypto-related targets removed - focusing on NSE only
# watch-crypto: ## (REMOVED - NSE focus only)
# watch-all: ## (REMOVED - NSE focus only)
# crypto-oco-drill: ## (REMOVED - NSE focus only)
	@sleep 2
	@echo "📉 Flattening positions..."
	@curl -fsS -X POST http://localhost:8000/flatten | jq || (echo "❌ Flatten failed" && exit 1)
	@sleep 1
	@echo "📊 Checking positions..."
	@POS_COUNT=$$(curl -fsS http://localhost:8000/positions 2>/dev/null | jq '.count // 0'); \
	if [ "$$POS_COUNT" -eq 0 ]; then \
		echo "✅ Positions count: $$POS_COUNT (expected 0)"; \
	else \
		echo "⚠️  Positions count: $$POS_COUNT (expected 0)"; \
		exit 1; \
	fi

crypto-report: ## Generate crypto report from last 24h scorer JSONs
	bash scripts/crypto_report.sh

crypto-gonogo: ## Run GO/NO-GO check before canary launch
	bash scripts/crypto_gonogo_check.sh

crypto-canary-launch: ## Launch crypto canary (pre-flight → launch → watch instructions)
	bash scripts/crypto_canary_launch.sh

crypto-canary-stop: ## Stop crypto canary and flatten positions
	@echo "🛑 Stopping crypto canary..."
	@curl -fsS -X POST http://localhost:8000/flatten >/dev/null 2>&1 || true
	@pkill -f 'uvicorn' || true
	@echo "✅ Canary stopped and flattened"

crypto-canary-status: ## Check crypto canary status (ready + key metrics)
	@echo "📊 Crypto Canary Status"
	@echo "======================"
	@echo ""
	@echo "1️⃣  /ready endpoint:"
	@curl -s http://localhost:8000/ready | jq . || echo "   ❌ API not responding"
	@echo ""
	@echo "2️⃣  Key metrics:"
	@curl -s http://localhost:8000/metrics 2>/dev/null | grep -E '^trader_(is_leader|.*heartbeat.*|oco_orphans_total|crypto_ws_reconnects_total)' || echo "   ⚠️  Metrics not available"

# Kite Canary Commands
kite-size: ## Calculate Kite debit spread sizing (CAPITAL=30000 RISK_PCT=0.30)
	@if [ -z "$(CAPITAL)" ]; then \
		echo "❌ Usage: make kite-size CAPITAL=30000 RISK_PCT=0.30"; \
		exit 1; \
	fi; \
	python3 scripts/kite_sizing_calc.py --capital $(CAPITAL) --risk-pct $${RISK_PCT:-0.30}

kite-canary-launch: ## Launch Kite canary (pre-flight → gate → watch instructions)
	@echo "🚀 Kite Canary Launch Sequence"
	@echo "=============================="
	@echo ""
	@echo "1️⃣  Pre-flight gate checks..."
	@make prelive-gate || (echo "❌ Pre-flight gate failed. Fix issues before proceeding." && exit 1)
	@echo ""
	@echo "2️⃣  API readiness check..."
	@curl -fsS http://localhost:8000/ready | jq . || (echo "❌ API not ready" && exit 1)
	@echo ""
	@echo "3️⃣  Starting metrics watch (Ctrl+C to stop)..."
	@echo "   Key metrics to watch:"
	@echo "   - trader_is_leader should be 1"
	@echo "   - *_heartbeat_seconds should be < 5"
	@echo "   - leader_changes_total should be 0"
	@echo ""
	@echo "✅ Canary ready. Monitoring metrics..."
	@echo "   Run 'make kite-canary-status' in another terminal to check status"
	@echo "   Run 'make kite-canary-stop' to stop and flatten"
	@make watch-metrics

kite-canary-stop: ## Stop Kite canary and flatten positions
	@echo "🛑 Stopping Kite canary..."
	@curl -fsS -X POST http://localhost:8000/flatten >/dev/null 2>&1 || echo "   ⚠️  Flatten endpoint not available or already flat"
	@pkill -f 'uvicorn.*apps.api.main' || echo "   ⚠️  API process not found"
	@echo "✅ Canary stopped and flattened"

kite-canary-status: ## Check Kite canary status (ready + key metrics)
	@echo "📊 Kite Canary Status"
	@echo "===================="
	@echo ""
	@echo "1️⃣  /ready endpoint:"
	@curl -s http://localhost:8000/ready | jq . || echo "   ❌ API not responding"
	@echo ""
	@echo "2️⃣  Key metrics:"
	@curl -s http://localhost:8000/metrics 2>/dev/null | grep -E '^trader_(is_leader|.*heartbeat.*|oco_orphans_total|leader_changes_total)' || echo "   ⚠️  Metrics not available"

kite-token-refresh: ## Refresh Kite access token (daily - opens browser for OAuth)
	@echo "🔄 Refreshing Kite access token..."
	@python3 scripts/kite_token_refresh.py || echo "   ❌ Token refresh failed. Check KITE_API_KEY and KITE_API_SECRET are set."

kite-token-check: ## Verify Kite access token is valid (quick self-check)
	@echo "🔍 Checking Kite access token..."
	@python3 scripts/kite_token_check.py || echo "   ❌ Token check failed. Run 'make kite-token-refresh' to get a fresh token."

kite-token-smoke: ## Smoke test token refresh script (no secrets, dry run)
	@bash scripts/kite_token_smoke_test.sh

verify-infra: ## Verify infrastructure (orchestrator, metrics, docker, watch commands)
	@bash scripts/verify_infrastructure.sh

proxy-health: ## Check proxy health and verify static IP (SEBI compliance)
	@python3 scripts/check_proxy_health.py

# Ops Browser Commands
ops-smoke: ## Run ops browser smoke test (API + UI)
	@if [ -z "$$API_BASE" ]; then API_BASE=http://localhost:8000; fi; \
	if [ -z "$$UI_BASE" ]; then UI_BASE=http://localhost:3000; fi; \
	API_BASE=$$API_BASE UI_BASE=$$UI_BASE \
	bash apps/ops-browser/scripts/prod_smoke.sh

ops-smoke-no-ui: ## Run ops browser smoke test (API only, skip UI check)
	@if [ -z "$$API_BASE" ]; then API_BASE=http://localhost:8000; fi; \
	SKIP_UI_CHECK=true API_BASE=$$API_BASE \
	bash apps/ops-browser/scripts/prod_smoke.sh

ops-verify-cors: ## Verify CORS headers on API endpoints
	@bash apps/ops-browser/scripts/verify_cors.sh

ops-verify-preflight: ## Verify OPTIONS preflight CORS headers
	@bash apps/ops-browser/scripts/verify_preflight.sh

ops-verify-expose: ## Verify Access-Control-Expose-Headers on API endpoints
	@API=$${API:-http://localhost:8000} ORIGIN=$${ORIGIN:-http://localhost:3000} ENDPOINT=$${ENDPOINT:-/ready} STRICT=$${STRICT:-true} TEST_ERROR_ENDPOINT=$${TEST_ERROR_ENDPOINT:-} \
	bash apps/ops-browser/scripts/ops-verify-expose.sh

ops-smoke-proxy: ## Run production smoke test (API behind reverse proxy)
	@if [ -z "$$API" ]; then API=https://ops-api.yourdomain.com; fi; \
	if [ -z "$$ORIGIN" ]; then ORIGIN=https://ops-ui.yourdomain.com; fi; \
	API=$$API ORIGIN=$$ORIGIN \
	bash apps/ops-browser/scripts/prod_smoke_proxy.sh

# Crypto-related targets removed - focusing on NSE only
# crypto-prelaunch-smoke: ## (REMOVED - NSE focus only)
# crypto-validation-flight: ## (REMOVED - NSE focus only)
# test-binance: ## (REMOVED - NSE focus only)

quick-proveout: ## Run quick prove-out test (health, metrics, kill-switch)
	bash scripts/quick_proveout.sh

quick-health: ## Run 5 critical health checks for burn-in readiness
	bash scripts/quick_health_check.sh

burnin-check: ## Quick burn-in check (leader, heartbeats, supervisor, readiness)
	bash scripts/burn_in_check.sh

reconcile-db: ## Run database reconciliation (check duplicates/orphans)
	@if [ -z "$$DATABASE_URL" ]; then \
		echo "❌ DATABASE_URL not set"; \
		exit 1; \
	fi; \
	psql "$${DATABASE_URL#postgresql+psycopg2://}" -f scripts/reconcile_db.sql

chaos-suite: ## Run full chaos test suite (leader lock, rate limit, postgres)
	@echo "🧪 Running chaos test suite..."
	@NONINTERACTIVE=1 PAUSE_ON_FAIL=1 bash scripts/chaos_test_leader_lock.sh
	@bash scripts/chaos_test_rate_limit.sh
	@bash scripts/chaos_test_postgres.sh
	@echo "✅ Chaos suite complete"

score-day1: ## One-shot Day-1 PASS scorer (readiness, heartbeats, DB integrity)
	bash scripts/score_day1.sh

score-day2: ## One-shot Day-2 PASS scorer (includes leader flaps check)
	bash scripts/score_day2.sh

print-latency: ## Print latency histogram p50/p95 (EOD sanity check)
	bash scripts/print_latency_histogram.sh

prometheus-flare: ## Print key Prometheus metrics (leader changes, order ack p95, scan HB)
	bash scripts/print_prometheus_flare.sh

read-day2: ## Read Day-2 scorer JSON and print compact PASS/FAIL line (jq-less)
	@bash scripts/read_day2_pass.sh || true

verify: ## Verify system readiness (clock drift, gate, metrics)
	@echo "🔍 Verifying system readiness..."
	@bash scripts/check_ntp_drift.sh || echo "⚠️  Clock drift check unavailable"
	@bash scripts/read_day2_pass.sh || echo "⚠️  Day-2 JSON check failed"
	@echo "✅ Verification complete"

.PHONY: verify-egress force-daily-logout sebi-verify

verify-egress: ## Verify egress IP matches expected
	@bash scripts/egress_ip_check.sh

force-daily-logout: ## Force daily logout (SEBI/NSE requirement)
	@bash scripts/force_daily_logout.sh

sebi-verify: ## Verify SEBI/NSE compliance status
	@curl -s :8000/compliance/status | jq .
	@bash scripts/prelive_gate.sh

setup-venv: ## Set up clean virtual environment with pinned dependencies
	bash scripts/setup_venv.sh

check-versions: ## Check installed dependency versions
	bash scripts/check_versions.sh

docker-build: ## Build Docker images
	docker-compose build

docker-up: ## Start all services in Docker
	docker-compose up -d

docker-logs: ## View Docker logs
	docker-compose logs -f

docker-restart: ## Restart all services
	docker-compose restart

shell-api: ## Open shell in API container
	docker-compose exec api /bin/sh

shell-postgres: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U aitrapp -d aitrapp

health: ## Check system health
	@curl -s http://localhost:8000/health | python -m json.tool

metrics: ## View Prometheus metrics
	@curl -s http://localhost:8000/metrics

dashboard: ## Open dashboard in browser
	@open http://localhost:3000 || xdg-open http://localhost:3000

backup-db: ## Backup database
	@mkdir -p backups
	docker-compose exec -T postgres pg_dump -U aitrapp aitrapp > backups/aitrapp_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Database backed up to backups/"

restore-db: ## Restore database (requires BACKUP_FILE=path)
	@if [ -z "$(BACKUP_FILE)" ]; then echo "Usage: make restore-db BACKUP_FILE=path/to/backup.sql"; exit 1; fi
	docker-compose exec -T postgres psql -U aitrapp aitrapp < $(BACKUP_FILE)

init: install dev migrate ## Initialize project (install deps, start infra, migrate DB)
	@echo "✅ Project initialized. Run 'make paper' to start in simulation mode."

# Kite MCP Server commands
mcp-build: ## Build Kite MCP Server (requires Go)
	@eval "$$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv 2>/dev/null || true)" && \
	if ! command -v go &> /dev/null; then \
		echo "❌ Go is not installed. Install Go first: brew install go"; \
		echo "   Or download from: https://go.dev/dl/"; \
		exit 1; \
	fi && \
	cd kite-mcp-server && go build -o kite-mcp-server
	@echo "✅ MCP server built successfully"

mcp-setup: ## Setup MCP server environment
	@if [ ! -f kite-mcp-server/.env ]; then \
		echo "Creating MCP server .env file..."; \
		cd kite-mcp-server && \
		echo "KITE_API_KEY=$${KITE_API_KEY:-your_api_key}" > .env && \
		echo "KITE_API_SECRET=$${KITE_API_SECRET:-your_api_secret}" >> .env && \
		echo "APP_MODE=http" >> .env && \
		echo "APP_PORT=8080" >> .env && \
		echo "APP_HOST=localhost" >> .env && \
		echo "✅ MCP server .env created. Edit kite-mcp-server/.env with your API keys."; \
	else \
		echo "✅ MCP server .env already exists"; \
	fi

mcp-run: mcp-build ## Run Kite MCP Server
	@if [ ! -f kite-mcp-server/kite-mcp-server ]; then \
		echo "Building MCP server first..."; \
		$(MAKE) mcp-build; \
	fi
	@if [ ! -f kite-mcp-server/.env ]; then \
		echo "❌ .env file not found. Run: make mcp-setup"; \
		exit 1; \
	fi
	@echo "🚀 Starting Kite MCP Server on http://localhost:8080"
	@cd kite-mcp-server && export $$(grep -v '^#' .env | xargs) && ./kite-mcp-server

mcp-run-readonly: mcp-build ## Run MCP Server in read-only mode (no trading)
	@if [ ! -f kite-mcp-server/kite-mcp-server ]; then \
		echo "Building MCP server first..."; \
		$(MAKE) mcp-build; \
	fi
	@if [ ! -f kite-mcp-server/.env ]; then \
		echo "❌ .env file not found. Run: make mcp-setup"; \
		exit 1; \
	fi
	@echo "🚀 Starting Kite MCP Server (READ-ONLY) on http://localhost:8080"
	@cd kite-mcp-server && export $$(grep -v '^#' .env | xargs) && EXCLUDED_TOOLS=place_order,modify_order,cancel_order,place_gtt_order,modify_gtt_order,delete_gtt_order ./kite-mcp-server

mcp-status: ## Check MCP server status
	@curl -s http://localhost:8080/ 2>/dev/null || echo "❌ MCP server is not running"

# GitHub Actions Runner (self-hosted)
runner-setup: ## Setup self-hosted GitHub Actions runner (macOS)
	@bash scripts/setup_github_runner.sh

runner-status: ## Check runner status
	@if [ -d ~/actions-runner ]; then \
		cd ~/actions-runner && ./svc.sh status || echo "❌ Runner not installed"; \
	else \
		echo "❌ Runner directory not found. Run: make runner-setup"; \
	fi

runner-logs: ## View runner logs
	@if [ -d ~/actions-runner ]; then \
		tail -n 50 ~/actions-runner/_diag/*.log 2>/dev/null || echo "No logs found"; \
	else \
		echo "❌ Runner directory not found"; \
	fi

runner-verify: ## Verify runner setup (check all components)
	@bash scripts/verify_runner.sh
