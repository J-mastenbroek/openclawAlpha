#!/usr/bin/env python3
"""
Polyberg: Comprehensive Polymarket Data Fetcher
- Fetches ALL markets with pagination
- Categorizes markets intelligently
- Tracks price history
- No API keys required
"""

import asyncio
import json
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import time

GAMMA_URL = "https://gamma-api.polymarket.com"
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

class MarketCategorizer:
    """Intelligent market categorization based on title analysis"""
    
    CATEGORIES = {
        "crypto": ["bitcoin", "ethereum", "solana", "xrp", "cardano", "dogecoin", "ripple", "btc", "eth", "sol", "ada", "doge", "cryptocurrency", "crypto", "altcoin", "token", "coin"],
        "sports": ["nfl", "nba", "mlb", "nhl", "soccer", "football", "basketball", "baseball", "hockey", "tennis", "wimbledon", "super bowl", "world cup", "olympics", "championship", "playoff", "game", "match", "score"],
        "politics": ["election", "president", "congress", "senate", "candidate", "democrat", "republican", "parliament", "parliament", "vote", "impeach", "trump", "biden", "harris", "harris", "governor", "poll"],
        "macro": ["gdp", "inflation", "fed", "interest rate", "recession", "unemployment", "stock market", "s&p", "nasdaq", "dow", "vix", "federal reserve", "fomc", "cpi", "economic"],
        "weather": ["temperature", "snow", "rain", "hurricane", "tornado", "weather", "celsius", "fahrenheit", "storm"],
        "celebrity": ["actor", "singer", "musician", "celebrity", "death", "health", "scandal", "movie", "show"],
        "tech": ["ai", "gpt", "chatgpt", "openai", "google", "apple", "meta", "microsoft", "tech", "startup", "ipo", "software"],
        "finance": ["stock", "company", "earnings", "revenue", "bankruptcy", "merger", "acquisition", "ipo", "bank"],
    }
    
    @classmethod
    def categorize(cls, title: str) -> str:
        """Categorize a market by its title"""
        title_lower = title.lower()
        
        # Check each category
        category_scores = defaultdict(int)
        for category, keywords in cls.CATEGORIES.items():
            for keyword in keywords:
                if keyword in title_lower:
                    category_scores[category] += 1
        
        if category_scores:
            return max(category_scores, key=category_scores.get)
        return "other"

class PriceHistoryTracker:
    """Track bid/ask history over time"""
    
    def __init__(self):
        self.history_file = DATA_DIR / "price_history.json"
        self.history = self._load_history()
    
    def _load_history(self) -> Dict:
        """Load existing price history"""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def record(self, market_id: str, bid: float, ask: float, timestamp: str = None):
        """Record current bid/ask for a market"""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()
        
        if market_id not in self.history:
            self.history[market_id] = {"bids": [], "asks": [], "timestamps": []}
        
        # Keep last 100 data points per market
        if len(self.history[market_id]["bids"]) >= 100:
            self.history[market_id]["bids"].pop(0)
            self.history[market_id]["asks"].pop(0)
            self.history[market_id]["timestamps"].pop(0)
        
        self.history[market_id]["bids"].append(bid)
        self.history[market_id]["asks"].append(ask)
        self.history[market_id]["timestamps"].append(timestamp)
    
    def save(self):
        """Persist history to disk"""
        with open(self.history_file, "w") as f:
            json.dump(self.history, f)
    
    def get_history(self, market_id: str) -> Dict:
        """Get history for a market"""
        return self.history.get(market_id, {})

class PolymarketFullFetcher:
    """Fetch all Polymarket markets with pagination and categorization"""
    
    def __init__(self):
        self.base_url = GAMMA_URL.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Polyberg/1.0",
        })
        self.price_tracker = PriceHistoryTracker()
        self.categorizer = MarketCategorizer()
    
    def _get(self, endpoint: str, params: dict = None) -> list:
        """Make API request with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                url = f"{self.base_url}/{endpoint.lstrip('/')}"
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"Failed to fetch {endpoint}: {e}")
                    return []
                time.sleep(1)
        return []
    
    def fetch_all_markets(self) -> List[Dict]:
        """Fetch all Polymarket markets with pagination"""
        all_markets = []
        offset = 0
        limit = 200  # Gamma API max per request
        consecutive_empty = 0
        
        print("[Markets] Fetching all Polymarket markets...")
        
        while consecutive_empty < 2:  # Stop after 2 empty responses
            try:
                data = self._get("markets", {
                    "limit": limit,
                    "offset": offset,
                    "closed": "false",
                })
                
                if not data or len(data) == 0:
                    consecutive_empty += 1
                    if consecutive_empty >= 2:
                        break
                    offset += limit
                    continue
                
                consecutive_empty = 0
                
                for market in data:
                    try:
                        market_id = market.get("id")
                        title = market.get("title", market.get("slug", "Unknown"))
                        
                        best_bid = float(market.get("bestBid", 0))
                        best_ask = float(market.get("bestAsk", 1))
                        
                        # Filter out dead markets
                        if best_bid == 0 and best_ask == 1:
                            continue
                        if best_bid >= best_ask:
                            continue
                        
                        # Calculate spread
                        spread = 0
                        if (best_bid + best_ask) > 0:
                            spread = ((best_ask - best_bid) / ((best_bid + best_ask) / 2)) * 100
                        
                        # Get expiry time
                        end_time = market.get("endTime", market.get("closesTime"))
                        
                        market_entry = {
                            "id": market_id,
                            "title": title,
                            "slug": market.get("slug", ""),
                            "bid": round(best_bid, 4),
                            "ask": round(best_ask, 4),
                            "spread": round(spread, 2),
                            "volume_24h": float(market.get("volume24h", 0)),
                            "volume_7d": float(market.get("volume7d", 0)),
                            "liquidity": float(market.get("liquidity", 0)),
                            "category": self.categorizer.categorize(title),
                            "end_time": end_time,
                        }
                        
                        # Track price history
                        self.price_tracker.record(market_id, best_bid, best_ask)
                        
                        all_markets.append(market_entry)
                    
                    except (ValueError, TypeError, KeyError) as e:
                        continue
                
                print(f"  [{offset:5d}] Fetched {len(data)} markets, total: {len(all_markets)}")
                offset += limit
                
            except Exception as e:
                print(f"Error fetching markets: {e}")
                break
        
        # Save price history
        self.price_tracker.save()
        
        # Sort by volume and liquidity
        all_markets = sorted(
            all_markets,
            key=lambda x: (x.get("volume_24h", 0), x.get("liquidity", 0)),
            reverse=True
        )
        
        print(f"[Markets] Total unique markets found: {len(all_markets)}")
        return all_markets
    
    def get_market_price_history(self, market_id: str) -> Dict:
        """Get price history for a specific market"""
        return self.price_tracker.get_history(market_id)
    
    def fetch_and_save(self) -> Dict:
        """Fetch all data and save to live_data.json"""
        markets = self.fetch_all_markets()
        
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "market_count": len(markets),
            "markets": markets,
        }
        
        output_file = DATA_DIR / "live_data.json"
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"✓ Saved {len(markets)} markets to {output_file}")
        return data

if __name__ == "__main__":
    fetcher = PolymarketFullFetcher()
    fetcher.fetch_and_save()
