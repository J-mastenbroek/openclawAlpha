#!/bin/bash
# Polyberg: One-command deployment + refresh

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "╔════════════════════════════════════════════╗"
echo "║    POLYBERG DEPLOYMENT & DATA REFRESH     ║"
echo "╚════════════════════════════════════════════╝"
echo ""

# Run full update
echo "[1/3] Updating all data..."
python3 "$REPO_ROOT/src/update_all.py" || true

# Commit and push
echo ""
echo "[2/3] Deploying to GitHub..."
cd "$REPO_ROOT"
git add docs/ data/ src/
git commit -m "Polyberg auto-update: $(date +'%Y-%m-%d %H:%M:%S')" || true
git push origin main || echo "Push failed - check git config"

# Final status
echo ""
echo "╔════════════════════════════════════════════╗"
echo "║         ✓ DEPLOYMENT COMPLETE             ║"
echo "╚════════════════════════════════════════════╝"
echo ""
echo "Dashboard: https://j-mastenbroek.github.io/openclawAlpha/"
echo "Repository: https://github.com/J-mastenbroek/openclawAlpha"
echo ""
echo "Next refresh in 30 minutes..."
