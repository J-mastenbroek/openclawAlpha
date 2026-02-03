#!/bin/bash
# Polyberg Deployment Script
# Updates dashboard data and deploys to GitHub Pages

set -e

echo "================================================"
echo "POLYBERG DEPLOYMENT SCRIPT"
echo "================================================"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to repo directory
cd "$SCRIPT_DIR"

# 1. Update all data
echo "[1/3] Updating all data sources..."
echo "-----------------------------------------------"
python3 src/update_all.py

# 2. Copy data to docs
echo ""
echo "[2/3] Copying data to GitHub Pages..."
echo "-----------------------------------------------"
mkdir -p docs/data
cp data/live_data.json docs/data/
cp data/news.json docs/data/
cp data/whales.json docs/data/
echo "✓ Data copied to docs/data/"

# 3. Git commit and push
echo ""
echo "[3/3] Committing and pushing to GitHub..."
echo "-----------------------------------------------"

# Only commit if there are changes
if git diff --quiet --exit-code; then
    echo "No changes to commit"
else
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    git add -A
    git commit -m "Polyberg update: $timestamp"
    git push origin main
    echo "✓ Pushed to GitHub"
    echo ""
    echo "Dashboard updated: https://j-mastenbroek.github.io/openclawAlpha/"
fi

echo ""
echo "================================================"
echo "✓ DEPLOYMENT COMPLETE"
echo "================================================"
