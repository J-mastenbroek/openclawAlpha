"""Autonomous 24/7 scanner with persistent scheduling."""

import schedule
import time
import subprocess
from datetime import datetime
import json

def run_scan():
    """Execute a single scan."""
    print(f"\n{'='*60}")
    print(f"[{datetime.now().isoformat()}] SCAN STARTED")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            ["python", "-m", "src.main"],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        print(f"[{datetime.now().isoformat()}] SCAN COMPLETED")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    """Run scheduler."""
    print("🤖 AlphaMonitor: Starting autonomous 24/7 scanner...")
    
    # Schedule scan every 4 hours
    schedule.every(4).hours.do(run_scan)
    
    # Run once immediately
    run_scan()
    
    # Keep scheduler running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()
