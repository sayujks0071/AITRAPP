.PHONY: help dev paper live stop clean test test-integration test-replay lint format install

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

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

paper: ## Run in PAPER mode (safe simulation)
	@echo "Starting in PAPER MODE (simulation only)"
	@export APP_MODE=PAPER && python -m apps.api.main

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

stop: ## Stop all services
	docker-compose down

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
	python -m packages.storage.migrate

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
