# CI-First Workflows

This directory contains GitHub Actions workflows for automated testing, backtesting, and AI-powered reviews.

## New Workflows (CI-First Setup)

### 1. `ci.yml` - Continuous Integration
- **Triggers:** Push/PR to `main` or `develop`
- **Purpose:** Lint, test, smoke backtest, security checks
- **Duration:** ~5-10 minutes

### 2. `nightly-backtest.yml` - Nightly Backtests
- **Triggers:** Daily at 18:00 UTC (23:30 IST)
- **Purpose:** Full backtest suite on NIFTY & BANKNIFTY
- **Duration:** ~30-60 minutes
- **Output:** Artifacts with backtest reports

### 3. `weekly-ai-review.yml` - Weekly AI Review
- **Triggers:** Every Monday at 03:00 UTC (08:30 IST)
- **Purpose:** AI-powered performance analysis
- **Duration:** ~10-15 minutes
- **Output:** AI-generated weekly review

## Existing Workflows

- `actionlint.yml` - Actionlint validation
- `archive-day2-artifacts.yml` - Archive Day-2 reports
- `codeql.yml` - Security code analysis
- `comment-dispatcher.yml` - Slash command routing
- `crypto-health.yml` - Crypto health checks
- `manual-canary-live.yml` - Manual live gate
- `nightly-tuning.yml` - Research tuning
- `ops-browser-deploy.yml` - Deploy ops browser
- `paper-e2e.yml` - Paper trading E2E tests
- `paper-preopen.yml` - Pre-open checks
- `postclose-report.yml` - Post-close reports
- `prelive-gate.yml` - Pre-live gate checks
- `sbom-grype.yml` - SBOM & vulnerability scanning
- `scorecards.yml` - Security scorecards

## Quick Start

After pushing these workflows, they'll appear in the GitHub Actions tab:

1. **CI workflow** runs automatically on every push/PR
2. **Nightly backtests** run daily (check Actions → Scheduled workflows)
3. **Weekly AI review** runs every Monday (requires API keys in Secrets)

## Documentation

- **Setup Guide:** `docs/CI_FIRST_SETUP.md`
- **Quick Reference:** `CI_QUICK_REFERENCE.md`



This directory contains GitHub Actions workflows for automated testing, backtesting, and AI-powered reviews.

## New Workflows (CI-First Setup)

### 1. `ci.yml` - Continuous Integration
- **Triggers:** Push/PR to `main` or `develop`
- **Purpose:** Lint, test, smoke backtest, security checks
- **Duration:** ~5-10 minutes

### 2. `nightly-backtest.yml` - Nightly Backtests
- **Triggers:** Daily at 18:00 UTC (23:30 IST)
- **Purpose:** Full backtest suite on NIFTY & BANKNIFTY
- **Duration:** ~30-60 minutes
- **Output:** Artifacts with backtest reports

### 3. `weekly-ai-review.yml` - Weekly AI Review
- **Triggers:** Every Monday at 03:00 UTC (08:30 IST)
- **Purpose:** AI-powered performance analysis
- **Duration:** ~10-15 minutes
- **Output:** AI-generated weekly review

## Existing Workflows

- `actionlint.yml` - Actionlint validation
- `archive-day2-artifacts.yml` - Archive Day-2 reports
- `codeql.yml` - Security code analysis
- `comment-dispatcher.yml` - Slash command routing
- `crypto-health.yml` - Crypto health checks
- `manual-canary-live.yml` - Manual live gate
- `nightly-tuning.yml` - Research tuning
- `ops-browser-deploy.yml` - Deploy ops browser
- `paper-e2e.yml` - Paper trading E2E tests
- `paper-preopen.yml` - Pre-open checks
- `postclose-report.yml` - Post-close reports
- `prelive-gate.yml` - Pre-live gate checks
- `sbom-grype.yml` - SBOM & vulnerability scanning
- `scorecards.yml` - Security scorecards

## Quick Start

After pushing these workflows, they'll appear in the GitHub Actions tab:

1. **CI workflow** runs automatically on every push/PR
2. **Nightly backtests** run daily (check Actions → Scheduled workflows)
3. **Weekly AI review** runs every Monday (requires API keys in Secrets)

## Documentation

- **Setup Guide:** `docs/CI_FIRST_SETUP.md`
- **Quick Reference:** `CI_QUICK_REFERENCE.md`




