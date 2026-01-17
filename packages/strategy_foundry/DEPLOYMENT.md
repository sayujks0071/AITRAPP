# Deployment Guide

## Prerequisites
- Python 3.10+
- Dependencies: `pandas`, `numpy`, `requests`, `pyyaml`, `structlog`, `pytz`.

## Configuration
- Adjust `configs/foundry.yaml` for risk limits and capital.
- Update `configs/instrument_map.yaml` for symbol mappings.

## Automation
- The `run_hourly.py` script is designed to run via Cron or GitHub Actions.
- Ensure the runner has internet access to fetch data.

## Consuming Signals
- The system outputs `packages/strategy_foundry/results/live_signal.json`.
- Downstream systems should poll this file or trigger off its update.
- The signal contains `champion_id`, `instrument`, `signal` (1=Long, 0=Flat/Short depending on logic), and `timestamp`.

## Safety
- **Gate**: High performance thresholds required for a strategy to be "Live Eligible".
- **Failsafe**: If data is stale or market is closed, `status` will be `SKIPPED`.
