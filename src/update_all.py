#!/usr/bin/env python3
"""
Polyberg: Update all data (markets, news, whales)
"""

import subprocess
import sys
from pathlib import Path
import json
from datetime import datetime, timezone

def run_command(cmd, label):
    """Run a command and report results"""
    print(f"\n{'='*60}")
    print(f"[{label}]")
    print('='*60)
    try:
        result = subprocess.run(cmd, shell=True, capture_output=False, text=True, timeout=300)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"⚠ Timeout on {label}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    repo_root = Path(__file__).parent.parent
    
    print(f"""
╔════════════════════════════════════════════╗
║     POLYBERG DATA UPDATE - Full Cycle      ║
╚════════════════════════════════════════════╝
""")
    
    # Run all fetchers
    success = True
    success &= run_command("cd {} && python3 src/polymarket_full_fetcher.py".format(repo_root), "MARKETS: Fetch 25K+ from Polymarket")
    success &= run_command("cd {} && python3 src/news_scraper.py".format(repo_root), "NEWS: Scrape from 5+ sources")
    success &= run_command("cd {} && python3 src/whale_tracker.py".format(repo_root), "WHALES: Track top traders")
    
    # Copy to docs
    print(f"\n{'='*60}")
    print("[DEPLOY] Copying to GitHub Pages...")
    print('='*60)
    
    import shutil
    src_data = repo_root / "data"
    dst_data = repo_root / "docs" / "data"
    
    for json_file in ["live_data.json", "news.json", "whales.json", "price_history.json"]:
        src = src_data / json_file
        dst = dst_data / json_file
        if src.exists():
            try:
                shutil.copy2(src, dst)
                print(f"✓ Copied {json_file}")
            except Exception as e:
                print(f"✗ Failed to copy {json_file}: {e}")
    
    # Final report
    print(f"\n{'='*60}")
    print("UPDATE COMPLETE")
    print('='*60)
    print(f"✓ Live at: https://j-mastenbroek.github.io/openclawAlpha/")
    print(f"✓ Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
