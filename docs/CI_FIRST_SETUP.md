# CI-First Trading Repository Setup

AITRAPP is now configured as a **CI-first** trading repository with GitHub Actions workflows that run automatically on every change.

## 🚀 Workflows Overview

### 1. **Continuous Integration** (`.github/workflows/ci.yml`)

**Triggers:**
- Every push to `main` or `develop`
- Every pull request
- Manual dispatch

**What it does:**
- ✅ Lints code with `ruff`
- ✅ Type checks with `mypy` (non-blocking)
- ✅ Runs unit tests with `pytest`
- ✅ Runs smoke backtest (quick validation)
- ✅ Checks for sensitive files (`.env`, `.env.bak`)

**Duration:** ~5-10 minutes

### 2. **Nightly Backtests** (`.github/workflows/nightly-backtest.yml`)

**Triggers:**
- Scheduled: Daily at 18:00 UTC (23:30 IST)
- Manual dispatch

**What it does:**
- 📊 Runs full backtest suite on NIFTY and BANKNIFTY
- 📝 Generates Markdown summaries
- 📦 Uploads reports as GitHub artifacts (30-day retention)

**Duration:** ~30-60 minutes

### 3. **Weekly AI Review** (`.github/workflows/weekly-ai-review.yml`)

**Triggers:**
- Scheduled: Every Monday at 03:00 UTC (08:30 IST)
- Manual dispatch

**What it does:**
- 🤖 Analyzes recent backtest results using AI (OpenAI/Gemini)
- 📊 Generates weekly performance insights
- 📦 Uploads review as GitHub artifact (90-day retention)

**Duration:** ~10-15 minutes

## 🔧 Setup Instructions

### 1. Enable Workflows

The workflows are already in `.github/workflows/`. They'll run automatically once you push to GitHub.

### 2. Configure Secrets (Optional - for AI Review)

If you want the weekly AI review to work, add these secrets in GitHub:

1. Go to: **Settings → Secrets and variables → Actions**
2. Add one or both:
   - `OPENAI_API_KEY` - For OpenAI GPT-4o-mini
   - `GEMINI_API_KEY` - For Google Gemini 1.5 Flash (recommended, cheaper)

**Note:** The AI review will still generate a basic summary even without API keys.

### 3. Verify Workflows

After pushing, check:
- **Actions tab** in GitHub to see workflow runs
- **Artifacts** section to download backtest reports

## 📋 Helper Scripts

### `scripts/summarise_backtests.py`

Converts backtest output into Markdown summaries.

```bash
python scripts/summarise_backtests.py \
  --date 2025-11-22 \
  --out reports/backtests/2025-11-22_summary.md
```

### `scripts/ai_weekly_review.py`

Generates AI-powered weekly reviews.

```bash
export OPENAI_API_KEY="your-key"  # or GEMINI_API_KEY
python scripts/ai_weekly_review.py \
  --output docs/weekly-reviews/2025-W47.md \
  --backtest-dir reports/backtests \
  --lookback-days 7
```

## 🎯 What Gets Tested

### CI Workflow Tests:
- **Code Quality**: Ruff linting, mypy type checking
- **Unit Tests**: All tests in `tests/` directory
- **Smoke Backtest**: Quick 1-week validation on NIFTY ORB strategy
- **Security**: Checks for accidentally committed `.env` files

### Nightly Backtests:
- **Full Suite**: All strategies on both NIFTY and BANKNIFTY
- **Date Range**: From 2025-08-15 to current date
- **Capital**: ₹10 lakh initial capital

## 📊 Viewing Results

### In GitHub:
1. Go to **Actions** tab
2. Click on a workflow run
3. Download artifacts (backtest reports, AI reviews)

### Locally:
```bash
# Run CI checks locally
ruff check .
pytest tests/

# Run smoke backtest
python scripts/run_backtest.py \
  --symbol NIFTY \
  --start-date 2025-11-01 \
  --end-date 2025-11-07 \
  --strategy ORB
```

## 🔒 Security Notes

- **No Trading**: These workflows **never** connect to your broker
- **No Credentials**: They run in isolated GitHub runners
- **Read-Only**: Workflows only read code and historical data
- **Sensitive File Checks**: CI automatically fails if `.env` files are committed

## 🚨 Troubleshooting

### Workflow Fails on Smoke Backtest

**Issue:** Backtest fails because historical data files aren't in repo.

**Solution:** 
- The workflow uses `continue-on-error` for backtests
- Or add historical data to repo (if small enough)
- Or skip backtest in CI, run only in nightly workflow

### AI Review Not Working

**Issue:** Weekly review shows "Basic Summary" instead of AI insights.

**Solution:**
1. Check GitHub Secrets are set correctly
2. Verify API keys are valid
3. Check workflow logs for API errors

### Tests Failing

**Issue:** Unit tests fail in CI but pass locally.

**Solution:**
- Check Python version (CI uses 3.11)
- Verify all dependencies in `requirements.txt`
- Check for environment-specific code

## 📈 Next Steps

1. **Customize Backtest Range**: Edit `nightly-backtest.yml` to change date ranges
2. **Add More Tests**: Add unit tests to `tests/` directory
3. **Enhance AI Prompts**: Modify `scripts/ai_weekly_review.py` for better insights
4. **Add Deployment**: Create `deploy.yml` when ready for production

## 🤖 Using with Copilot

These workflows are designed to work with GitHub Copilot:

1. **Stub Functions**: The workflows call scripts that Copilot can help implement
2. **Auto-Complete**: Copilot will suggest CLI arguments matching workflow commands
3. **Type Hints**: Use type hints in Python scripts for better Copilot suggestions

Example: Start typing in `scripts/ai_weekly_review.py`:
```python
def generate_weekly_review(...):
    # Copilot will suggest implementation based on workflow usage
```

---

**Status:** ✅ CI-First setup complete. All workflows are ready to run.



AITRAPP is now configured as a **CI-first** trading repository with GitHub Actions workflows that run automatically on every change.

## 🚀 Workflows Overview

### 1. **Continuous Integration** (`.github/workflows/ci.yml`)

**Triggers:**
- Every push to `main` or `develop`
- Every pull request
- Manual dispatch

**What it does:**
- ✅ Lints code with `ruff`
- ✅ Type checks with `mypy` (non-blocking)
- ✅ Runs unit tests with `pytest`
- ✅ Runs smoke backtest (quick validation)
- ✅ Checks for sensitive files (`.env`, `.env.bak`)

**Duration:** ~5-10 minutes

### 2. **Nightly Backtests** (`.github/workflows/nightly-backtest.yml`)

**Triggers:**
- Scheduled: Daily at 18:00 UTC (23:30 IST)
- Manual dispatch

**What it does:**
- 📊 Runs full backtest suite on NIFTY and BANKNIFTY
- 📝 Generates Markdown summaries
- 📦 Uploads reports as GitHub artifacts (30-day retention)

**Duration:** ~30-60 minutes

### 3. **Weekly AI Review** (`.github/workflows/weekly-ai-review.yml`)

**Triggers:**
- Scheduled: Every Monday at 03:00 UTC (08:30 IST)
- Manual dispatch

**What it does:**
- 🤖 Analyzes recent backtest results using AI (OpenAI/Gemini)
- 📊 Generates weekly performance insights
- 📦 Uploads review as GitHub artifact (90-day retention)

**Duration:** ~10-15 minutes

## 🔧 Setup Instructions

### 1. Enable Workflows

The workflows are already in `.github/workflows/`. They'll run automatically once you push to GitHub.

### 2. Configure Secrets (Optional - for AI Review)

If you want the weekly AI review to work, add these secrets in GitHub:

1. Go to: **Settings → Secrets and variables → Actions**
2. Add one or both:
   - `OPENAI_API_KEY` - For OpenAI GPT-4o-mini
   - `GEMINI_API_KEY` - For Google Gemini 1.5 Flash (recommended, cheaper)

**Note:** The AI review will still generate a basic summary even without API keys.

### 3. Verify Workflows

After pushing, check:
- **Actions tab** in GitHub to see workflow runs
- **Artifacts** section to download backtest reports

## 📋 Helper Scripts

### `scripts/summarise_backtests.py`

Converts backtest output into Markdown summaries.

```bash
python scripts/summarise_backtests.py \
  --date 2025-11-22 \
  --out reports/backtests/2025-11-22_summary.md
```

### `scripts/ai_weekly_review.py`

Generates AI-powered weekly reviews.

```bash
export OPENAI_API_KEY="your-key"  # or GEMINI_API_KEY
python scripts/ai_weekly_review.py \
  --output docs/weekly-reviews/2025-W47.md \
  --backtest-dir reports/backtests \
  --lookback-days 7
```

## 🎯 What Gets Tested

### CI Workflow Tests:
- **Code Quality**: Ruff linting, mypy type checking
- **Unit Tests**: All tests in `tests/` directory
- **Smoke Backtest**: Quick 1-week validation on NIFTY ORB strategy
- **Security**: Checks for accidentally committed `.env` files

### Nightly Backtests:
- **Full Suite**: All strategies on both NIFTY and BANKNIFTY
- **Date Range**: From 2025-08-15 to current date
- **Capital**: ₹10 lakh initial capital

## 📊 Viewing Results

### In GitHub:
1. Go to **Actions** tab
2. Click on a workflow run
3. Download artifacts (backtest reports, AI reviews)

### Locally:
```bash
# Run CI checks locally
ruff check .
pytest tests/

# Run smoke backtest
python scripts/run_backtest.py \
  --symbol NIFTY \
  --start-date 2025-11-01 \
  --end-date 2025-11-07 \
  --strategy ORB
```

## 🔒 Security Notes

- **No Trading**: These workflows **never** connect to your broker
- **No Credentials**: They run in isolated GitHub runners
- **Read-Only**: Workflows only read code and historical data
- **Sensitive File Checks**: CI automatically fails if `.env` files are committed

## 🚨 Troubleshooting

### Workflow Fails on Smoke Backtest

**Issue:** Backtest fails because historical data files aren't in repo.

**Solution:** 
- The workflow uses `continue-on-error` for backtests
- Or add historical data to repo (if small enough)
- Or skip backtest in CI, run only in nightly workflow

### AI Review Not Working

**Issue:** Weekly review shows "Basic Summary" instead of AI insights.

**Solution:**
1. Check GitHub Secrets are set correctly
2. Verify API keys are valid
3. Check workflow logs for API errors

### Tests Failing

**Issue:** Unit tests fail in CI but pass locally.

**Solution:**
- Check Python version (CI uses 3.11)
- Verify all dependencies in `requirements.txt`
- Check for environment-specific code

## 📈 Next Steps

1. **Customize Backtest Range**: Edit `nightly-backtest.yml` to change date ranges
2. **Add More Tests**: Add unit tests to `tests/` directory
3. **Enhance AI Prompts**: Modify `scripts/ai_weekly_review.py` for better insights
4. **Add Deployment**: Create `deploy.yml` when ready for production

## 🤖 Using with Copilot

These workflows are designed to work with GitHub Copilot:

1. **Stub Functions**: The workflows call scripts that Copilot can help implement
2. **Auto-Complete**: Copilot will suggest CLI arguments matching workflow commands
3. **Type Hints**: Use type hints in Python scripts for better Copilot suggestions

Example: Start typing in `scripts/ai_weekly_review.py`:
```python
def generate_weekly_review(...):
    # Copilot will suggest implementation based on workflow usage
```

---

**Status:** ✅ CI-First setup complete. All workflows are ready to run.




