# CI-First Setup - Quick Reference

## ✅ What Was Added

### Workflows (`.github/workflows/`)
1. **`ci.yml`** - Runs on every push/PR: lint, test, smoke backtest
2. **`nightly-backtest.yml`** - Daily full backtests at 18:00 UTC
3. **`weekly-ai-review.yml`** - Weekly AI analysis every Monday 03:00 UTC

### Helper Scripts (`scripts/`)
1. **`summarise_backtests.py`** - Converts backtest output to Markdown
2. **`ai_weekly_review.py`** - Generates AI-powered weekly reviews

### Documentation
- **`docs/CI_FIRST_SETUP.md`** - Complete setup guide
- **`CI_QUICK_REFERENCE.md`** - This file

## 🚀 Quick Start

### 1. Push to GitHub
```bash
git add .github/workflows/ scripts/ docs/
git commit -m "feat: add CI-first workflows"
git push
```

### 2. Check Actions Tab
- Go to GitHub → Actions
- Workflows will run automatically

### 3. (Optional) Add AI API Keys
- Settings → Secrets → Actions
- Add `OPENAI_API_KEY` or `GEMINI_API_KEY`

## 📋 Workflow Details

### CI Workflow
- **When:** Every push/PR
- **Duration:** ~5-10 min
- **Checks:** Lint, test, smoke backtest, security

### Nightly Backtests
- **When:** Daily 18:00 UTC (23:30 IST)
- **Duration:** ~30-60 min
- **Output:** Artifacts with backtest reports

### Weekly AI Review
- **When:** Monday 03:00 UTC (08:30 IST)
- **Duration:** ~10-15 min
- **Output:** AI-generated performance review

## 🔧 Local Testing

```bash
# Test CI checks locally
ruff check .
pytest tests/

# Test smoke backtest
python scripts/run_backtest.py \
  --symbol NIFTY \
  --start-date 2025-11-01 \
  --end-date 2025-11-07 \
  --strategy ORB

# Test summarise script
python scripts/summarise_backtests.py \
  --date 2025-11-22 \
  --out reports/backtests/test_summary.md

# Test AI review (requires API key)
export OPENAI_API_KEY="your-key"
python scripts/ai_weekly_review.py \
  --output docs/weekly-reviews/test.md \
  --lookback-days 7
```

## 🎯 Key Features

✅ **No Trading** - Workflows never connect to broker  
✅ **Security Checks** - Fails if `.env` files committed  
✅ **Artifact Storage** - Backtest reports saved for 30-90 days  
✅ **AI Integration** - Optional weekly AI insights  
✅ **Copilot Ready** - Scripts designed for AI assistance  

## 📊 Expected Outputs

### CI Artifacts
- None (workflow just validates)

### Nightly Backtests
- `nifty_YYYY-MM-DD.txt` - NIFTY backtest output
- `banknifty_YYYY-MM-DD.txt` - BANKNIFTY backtest output
- `YYYY-MM-DD_summary.md` - Markdown summary

### Weekly AI Review
- `YYYY-WVV.md` - AI-generated weekly review

## 🔗 Related Files

- **Setup Guide:** `docs/CI_FIRST_SETUP.md`
- **Backtest Script:** `scripts/run_backtest.py`
- **Existing Workflows:** `.github/workflows/nightly-tuning.yml` (reference)

## 🚨 Common Issues

**Q: Workflow fails on smoke backtest?**  
A: Expected if historical data not in repo. Workflow uses `continue-on-error`.

**Q: AI review shows "Basic Summary"?**  
A: Add `OPENAI_API_KEY` or `GEMINI_API_KEY` to GitHub Secrets.

**Q: Tests pass locally but fail in CI?**  
A: Check Python version (CI uses 3.11) and dependencies.

---

**Status:** ✅ Ready to use. Push to GitHub to activate!

