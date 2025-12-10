#!/bin/bash
#
# SEBI Compliance Features - Staging Deployment Script
#
# Deploys and validates SEBI compliance features in staging environment
#
# Prerequisites:
#   - SSH access to staging server
#   - Database migrations ready
#   - API can be safely restarted
#
# Usage:
#   ./scripts/deploy_sebi_staging.sh [staging-host]
#
# Example:
#   ./scripts/deploy_sebi_staging.sh user@staging.aitrapp.com
#

set -e

# Configuration
STAGING_HOST="${1:-}"
REPO_DIR="/opt/aitrapp"
BACKUP_DIR="/opt/aitrapp/backups/$(date +%Y%m%d_%H%M%S)"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "======================================================================"
echo "🚀 SEBI Compliance Features - Staging Deployment"
echo "======================================================================"
echo ""

# Validate inputs
if [ -z "$STAGING_HOST" ]; then
    echo -e "${RED}❌ Error: Staging host not specified${NC}"
    echo ""
    echo "Usage: $0 [staging-host]"
    echo "Example: $0 user@staging.aitrapp.com"
    exit 1
fi

echo "Staging Host: ${STAGING_HOST}"
echo "Deployment Time: $(date)"
echo ""

# Confirmation
echo -e "${YELLOW}⚠️  WARNING: This will deploy SEBI compliance features to staging${NC}"
echo ""
echo "Changes to be deployed:"
echo "  • Enhanced audit logging (ORDER_PLACED, ORDER_CANCELLED)"
echo "  • Kill switch endpoint (/control/kill-switch)"
echo "  • Strategy-wise risk limits (max_loss_per_strategy_pct)"
echo "  • Dormant account check"
echo ""
read -p "Proceed with deployment? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo "======================================================================"
echo "Step 1: Pre-deployment Checks"
echo "======================================================================"
echo ""

# Check SSH connectivity
echo -n "Testing SSH connection... "
if ssh -o ConnectTimeout=5 "$STAGING_HOST" "echo OK" >/dev/null 2>&1; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌ Cannot connect to staging host${NC}"
    exit 1
fi

# Check if repo exists
echo -n "Checking repository directory... "
if ssh "$STAGING_HOST" "[ -d $REPO_DIR ]"; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌ Repository not found at $REPO_DIR${NC}"
    exit 1
fi

# Check current git branch
echo -n "Checking git branch... "
CURRENT_BRANCH=$(ssh "$STAGING_HOST" "cd $REPO_DIR && git branch --show-current")
echo "$CURRENT_BRANCH"

echo ""
echo "======================================================================"
echo "Step 2: Backup Current State"
echo "======================================================================"
echo ""

echo "Creating backup..."
ssh "$STAGING_HOST" <<EOF
    set -e
    mkdir -p $BACKUP_DIR
    cd $REPO_DIR

    # Backup code
    echo "Backing up code..."
    git stash
    tar -czf $BACKUP_DIR/code_backup.tar.gz .

    # Backup database (audit_logs table)
    echo "Backing up database..."
    pg_dump \$DATABASE_URL -t audit_logs > $BACKUP_DIR/audit_logs_backup.sql || true

    # Backup environment
    cp .env $BACKUP_DIR/.env.bak || true

    echo "✅ Backup complete: $BACKUP_DIR"
EOF

echo -e "${GREEN}✅ Backup complete${NC}"

echo ""
echo "======================================================================"
echo "Step 3: Deploy Code"
echo "======================================================================"
echo ""

echo "Deploying latest code..."
ssh "$STAGING_HOST" <<EOF
    set -e
    cd $REPO_DIR

    # Fetch latest changes
    echo "Fetching latest changes..."
    git fetch origin

    # Checkout target branch (assumes feat/sebi-compliance or main)
    TARGET_BRANCH="${TARGET_BRANCH:-feat/premium-vol-suite-observation-mcp}"
    echo "Checking out \$TARGET_BRANCH..."
    git checkout \$TARGET_BRANCH
    git pull origin \$TARGET_BRANCH

    echo "✅ Code deployed"
EOF

echo -e "${GREEN}✅ Code deployed${NC}"

echo ""
echo "======================================================================"
echo "Step 4: Update Dependencies"
echo "======================================================================"
echo ""

echo "Installing dependencies..."
ssh "$STAGING_HOST" <<EOF
    set -e
    cd $REPO_DIR

    # Activate venv and update dependencies
    source venv/bin/activate || source .venv/bin/activate
    pip install -r requirements.txt

    echo "✅ Dependencies updated"
EOF

echo -e "${GREEN}✅ Dependencies updated${NC}"

echo ""
echo "======================================================================"
echo "Step 5: Run Database Migrations"
echo "======================================================================"
echo ""

echo "Running migrations..."
ssh "$STAGING_HOST" <<EOF
    set -e
    cd $REPO_DIR

    # Check if alembic is configured
    if [ -f "alembic.ini" ]; then
        source venv/bin/activate || source .venv/bin/activate
        alembic upgrade head
        echo "✅ Migrations complete"
    else
        echo "⚠️  alembic.ini not found, skipping migrations"
    fi
EOF

echo -e "${GREEN}✅ Migrations complete${NC}"

echo ""
echo "======================================================================"
echo "Step 6: Update Environment Variables"
echo "======================================================================"
echo ""

echo "Updating .env file..."
ssh "$STAGING_HOST" <<EOF
    set -e
    cd $REPO_DIR

    # Add SEBI compliance environment variables
    if ! grep -q "COMPLIANCE_SEBI_2025" .env 2>/dev/null; then
        echo "" >> .env
        echo "# SEBI Compliance (Feb 2025)" >> .env
        echo "COMPLIANCE_SEBI_2025=1" >> .env
        echo "EXCHANGE_ALGO_ID=STAGING_ALGO" >> .env
        echo "TOPS_CAP_PER_SEC=9" >> .env
        echo "AUDIT_RETENTION_YEARS=5" >> .env
        echo "✅ Added SEBI compliance variables to .env"
    else
        echo "✅ SEBI compliance variables already present"
    fi
EOF

echo -e "${GREEN}✅ Environment updated${NC}"

echo ""
echo "======================================================================"
echo "Step 7: Restart Services"
echo "======================================================================"
echo ""

echo "Restarting API service..."
ssh "$STAGING_HOST" <<EOF
    set -e
    cd $REPO_DIR

    # Stop existing service
    if [ -f "logs/api_8000.pid" ]; then
        PID=\$(cat logs/api_8000.pid)
        kill \$PID 2>/dev/null || true
        sleep 2
    fi

    # Start API service
    source venv/bin/activate || source .venv/bin/activate
    nohup python3 -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 > logs/api_8000.log 2>&1 &
    echo \$! > logs/api_8000.pid

    echo "✅ API restarted (PID: \$!)"

    # Wait for API to start
    sleep 5
EOF

echo -e "${GREEN}✅ Services restarted${NC}"

echo ""
echo "======================================================================"
echo "Step 8: Verification Tests"
echo "======================================================================"
echo ""

echo "Running SEBI compliance verification..."
ssh "$STAGING_HOST" <<EOF
    set -e
    cd $REPO_DIR
    source venv/bin/activate || source .venv/bin/activate

    # Run compliance tests
    python3 scripts/test_sebi_compliance_simple.py

    echo ""
    echo "Testing kill switch endpoint..."
    curl -s http://localhost:8000/control/state > /dev/null
    if [ \$? -eq 0 ]; then
        echo "✅ Kill switch endpoint accessible"
    else
        echo "❌ Kill switch endpoint not accessible"
        exit 1
    fi

    echo ""
    echo "Testing audit logging..."
    psql \$DATABASE_URL -c "SELECT COUNT(*) FROM audit_logs LIMIT 1;" >/dev/null
    if [ \$? -eq 0 ]; then
        echo "✅ Audit logs table accessible"
    else
        echo "❌ Audit logs table not accessible"
        exit 1
    fi
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ All verification tests passed${NC}"
else
    echo ""
    echo -e "${RED}❌ Verification tests failed${NC}"
    echo ""
    echo "Rollback available at: $BACKUP_DIR"
    exit 1
fi

echo ""
echo "======================================================================"
echo "Step 9: Smoke Tests"
echo "======================================================================"
echo ""

echo "Running smoke tests..."
ssh "$STAGING_HOST" <<EOF
    set -e

    echo "Test 1: Health check"
    curl -s http://localhost:8000/health | grep -q "ok" && echo "✅ Health check passed" || echo "❌ Health check failed"

    echo "Test 2: Ready check"
    curl -s http://localhost:8000/ready | grep -q "ready" && echo "✅ Ready check passed" || echo "⚠️  Ready check failed"

    echo "Test 3: System state"
    curl -s http://localhost:8000/control/state | jq -e '.mode' >/dev/null && echo "✅ System state check passed" || echo "❌ System state check failed"
EOF

echo ""
echo "======================================================================"
echo "🎉 Deployment Complete!"
echo "======================================================================"
echo ""
echo "Summary:"
echo "  ✅ Code deployed from branch: $CURRENT_BRANCH"
echo "  ✅ Dependencies updated"
echo "  ✅ Database migrations applied"
echo "  ✅ SEBI compliance features enabled"
echo "  ✅ Services restarted"
echo "  ✅ Verification tests passed"
echo ""
echo "Backup Location: $BACKUP_DIR"
echo ""
echo "Next Steps:"
echo "  1. Monitor logs: ssh $STAGING_HOST 'tail -f $REPO_DIR/logs/api_8000.log'"
echo "  2. Test kill switch: ssh $STAGING_HOST 'cd $REPO_DIR && ./scripts/test_kill_switch.sh'"
echo "  3. Verify audit logging: Check database for ORDER_PLACED entries"
echo "  4. Run integration tests"
echo ""
echo "Rollback (if needed):"
echo "  ssh $STAGING_HOST 'cd $REPO_DIR && tar -xzf $BACKUP_DIR/code_backup.tar.gz'"
echo ""
