#!/usr/bin/env python3
"""
Polyberg Master Updater
Runs all data fetchers and aggregators
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from polymarket_full_fetcher import PolymarketFullFetcher
from news_scraper import NewsAggregator
from whale_tracker import WhaleTracker

def main():
    print("\n" + "="*60)
    print("POLYBERG DASHBOARD DATA UPDATE")
    print("="*60 + "\n")
    
    start_time = datetime.now(timezone.utc)
    
    # 1. Fetch all markets
    print("[1/3] Fetching Polymarket data...")
    print("-" * 60)
    try:
        fetcher = PolymarketFullFetcher()
        market_data = fetcher.fetch_and_save()
        print(f"✓ Markets: {market_data['market_count']} total\n")
    except Exception as e:
        print(f"✗ Market fetch failed: {e}\n")
        return False
    
    # 2. Scrape news
    print("[2/3] Scraping news from public sources...")
    print("-" * 60)
    try:
        aggregator = NewsAggregator()
        news = aggregator.aggregate()
        aggregator.save_news(news)
        print(f"✓ News: {len(news)} articles\n")
    except Exception as e:
        print(f"✗ News scraping failed: {e}\n")
    
    # 3. Track whales
    print("[3/3] Tracking whale activity...")
    print("-" * 60)
    try:
        tracker = WhaleTracker()
        whale_data = tracker.track_and_save()
        print(f"✓ Whales: {len(whale_data['top_whales'])} tracked\n")
    except Exception as e:
        print(f"✗ Whale tracking failed: {e}\n")
    
    # Summary
    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    print("="*60)
    print(f"✓ UPDATE COMPLETE ({elapsed:.1f}s)")
    print("="*60 + "\n")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
