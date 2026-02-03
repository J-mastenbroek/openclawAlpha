#!/usr/bin/env python3
"""
Continuous live feed updater for Polymarket terminal.
Runs every 5 minutes: pulls real data, updates HTML.
"""

import json
import os
from datetime import datetime, timedelta
import requests
from pathlib import Path

class PolymarketTerminal:
    def __init__(self):
        self.repo_root = Path(__file__).parent.parent
        self.data_file = self.repo_root / "data" / "live_data.json"
        self.data_file.parent.mkdir(exist_ok=True)
        
    def fetch_polymarket_data(self):
        """Fetch real Polymarket market data from API"""
        try:
            # Polymarket API endpoint
            response = requests.get(
                "https://gamma-api.polymarket.com/markets?active=true&limit=50",
                timeout=10
            )
            if response.status_code == 200:
                markets = response.json()
                return self._format_markets(markets)
        except Exception as e:
            print(f"Error fetching Polymarket data: {e}")
        return []
    
    def _format_markets(self, markets):
        """Format Polymarket API response into useful structure"""
        formatted = []
        for market in markets[:10]:  # Top 10 markets
            try:
                formatted.append({
                    "id": market.get("id"),
                    "name": market.get("question"),
                    "bid": float(market.get("bestBid", 0)),
                    "ask": float(market.get("bestAsk", 1)),
                    "spread": abs(float(market.get("bestAsk", 1)) - float(market.get("bestBid", 0))),
                    "volume_24h": float(market.get("volume24h", 0)),
                    "liquidity": float(market.get("liquidity", 0)),
                })
            except (ValueError, KeyError):
                continue
        return formatted
    
    def fetch_crypto_news(self):
        """Fetch real crypto news"""
        news = []
        try:
            # CoinGecko API (free, no key required)
            response = requests.get(
                "https://api.coingecko.com/api/v3/news",
                timeout=10
            )
            if response.status_code == 200:
                items = response.json().get("data", [])[:10]
                for item in items:
                    news.append({
                        "title": item.get("title"),
                        "source": item.get("source"),
                        "published_at": item.get("published_at"),
                        "url": item.get("url"),
                    })
        except Exception as e:
            print(f"Error fetching news: {e}")
        return news
    
    def fetch_whale_activity(self):
        """Fetch whale wallet activity from Polymarket"""
        whales = []
        try:
            # Polymarket user endpoint (top wallets)
            response = requests.get(
                "https://gamma-api.polymarket.com/users?limit=20&sort=pnl&period=7d",
                timeout=10
            )
            if response.status_code == 200:
                users = response.json()
                for user in users[:10]:
                    whales.append({
                        "wallet": user.get("address"),
                        "trades": user.get("trade_count", 0),
                        "win_rate": user.get("win_rate", 0),
                        "pnl_7d": user.get("pnl_7d", 0),
                        "last_trade": user.get("last_trade_at"),
                    })
        except Exception as e:
            print(f"Error fetching whale data: {e}")
        return whales
    
    def save_live_data(self, markets, news, whales):
        """Save live data to JSON file"""
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "markets": markets,
            "news": news,
            "whales": whales,
        }
        with open(self.data_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Updated live data: {len(markets)} markets, {len(news)} news, {len(whales)} whales")
    
    def update(self):
        """Run full update cycle"""
        print(f"[{datetime.utcnow().isoformat()}] Updating live feed...")
        
        markets = self.fetch_polymarket_data()
        news = self.fetch_crypto_news()
        whales = self.fetch_whale_activity()
        
        self.save_live_data(markets, news, whales)
        
        return {
            "status": "ok",
            "markets_updated": len(markets),
            "news_updated": len(news),
            "whales_updated": len(whales),
        }

if __name__ == "__main__":
    terminal = PolymarketTerminal()
    result = terminal.update()
    print(f"Result: {result}")
