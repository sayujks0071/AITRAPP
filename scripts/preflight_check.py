#!/usr/bin/env python3
import os, sys, json, subprocess
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'requests'])
    import requests

API_BASE = os.getenv('API_BASE', 'http://localhost:8000')
GREEN, RED, YELLOW, BLUE, NC = '\033[0;32m', '\033[0;31m', '\033[1;33m', '\033[0;34m', '\033[0m'

print('='*60)
print('🚀 PRE-FLIGHT CHECKLIST FOR PAPER TRADING')
print('='*60)
print(f'Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")}')
print()

passed, failed, warnings = [], [], []

def p(msg): 
    print(f'{GREEN}✅{NC} {msg}')
    passed.append(msg)
def f(msg): 
    print(f'{RED}❌{NC} {msg}')
    failed.append(msg)
def w(msg): 
    print(f'{YELLOW}⚠️{NC} {msg}')
    warnings.append(msg)

# 1. Docker
print('1. INFRASTRUCTURE CHECKS')
print('-'*60)
try:
    r = subprocess.run(['docker', 'ps'], capture_output=True, timeout=5)
    if r.returncode == 0:
        out = r.stdout.decode()
        if 'postgres' in out.lower() or 'redis' in out.lower():
            p('Docker containers running')
        else:
            w('Docker running but containers may not be up')
    else:
        f('Docker not running')
except Exception as e:
    w(f'Docker check skipped: {e}')

# 2. Config
print('\n2. CONFIGURATION')
print('-'*60)
if Path('.env').exists():
    p('.env file exists')
    with open(".env") as env_file:
        env = env_file.read()
        if 'KITE_API_KEY' in env:
            p('KITE_API_KEY configured')
        else:
            f('KITE_API_KEY missing')
else:
    f('.env file missing')

if Path('configs/app.yaml').exists():
    p('configs/app.yaml exists')
    with open(".env") as env_file:
        cfg = env_file.read()
        if 'mode: PAPER' in cfg or 'mode:PAPER' in cfg.replace(' ', ''):
            p('Mode is PAPER')
        else:
            w('Mode may not be PAPER')
else:
    f('configs/app.yaml missing')

# 3. API
print('\n3. API & BACKEND')
print('-'*60)
try:
    r = requests.get(f'{API_BASE}/health', timeout=3)
    if r.status_code == 200:
        h = r.json()
        p(f'API running - Mode: {h.get("mode")}, Status: {h.get("status")}')
        if h.get('is_paused'):
            w('System is PAUSED')
    else:
        f(f'API returned {r.status_code}')
except Exception as e:
    f('API not running')
    print(f'   Start: source venv/bin/activate && uvicorn apps.api.main:app --host 0.0.0.0 --port 8000')

# 4. Strategies
print('\n4. STRATEGIES')
print('-'*60)
try:
    r = requests.get(f'{API_BASE}/strategies', timeout=3)
    if r.status_code == 200:
        strats = r.json()
        enabled = [s for s in strats if s.get('enabled')] if isinstance(strats, list) else []
        p(f'Strategies loaded: {len(strats) if isinstance(strats, list) else 0}')
        p(f'Enabled: {len(enabled)}')
        if enabled:
            for s in enabled[:5]:
                print(f'   - {s.get("name")}')
except:
    w('Could not fetch strategies')

# 5. Positions
print('\n5. RISK & POSITIONS')
print('-'*60)
try:
    r = requests.get(f'{API_BASE}/positions', timeout=3)
    if r.status_code == 200:
        pos = r.json()
        count = pos.get('count', 0) if isinstance(pos, dict) else len(pos) if isinstance(pos, list) else 0
        if count == 0:
            p(f'Open positions: {count} (flat)')
        else:
            w(f'Open positions: {count}')
except:
    w('Could not fetch positions')

# Summary
print('\n' + '='*60)
print('📊 SUMMARY')
print('='*60)
print(f'{GREEN}✅ Passed: {len(passed)}{NC}')
print(f'{RED}❌ Failed: {len(failed)}{NC}')
print(f'{YELLOW}⚠️  Warnings: {len(warnings)}{NC}')
print()

if len(failed) == 0:
    print(f'{GREEN}✅ GO: Ready for paper trading{NC}')
    sys.exit(0)
else:
    print(f'{RED}❌ NO-GO: Fix issues above{NC}')
    sys.exit(1)
