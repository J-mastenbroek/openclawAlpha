#!/usr/bin/env python3
"""
Polyberg: Live Polymarket data fetcher.
Pulls ONLY open, live markets with real current prices.
"""

import json
import requests
from datetime import datetime
from pathlib import Path

class PolybergTerminal:
    def __init__(self):
        self.repo_root = Path(__file__).parent.parent
        self.data_file = self.repo_root / "data" / "live_data.json"
        self.data_file.parent.mkdir(exist_ok=True)
        
    def fetch_live_markets(self):
        """Fetch only OPEN, LIVE markets from Polymarket"""
        markets = []
        
        try:
            # Try Polymarket Gamma API - get all markets
            response = requests.get(
                "https://gamma-api.polymarket.com/markets",
                timeout=15
            )
            
            if response.status_code == 200:
                all_markets = response.json()
                
                for m in all_markets:
                    try:
                        # Filter: only markets that are OPEN (not resolved/closed)
                        status = m.get("status", "").lower()
                        if status not in ["active", "open"] and status != "":
                            continue  # Skip closed/resolved markets
                        
                        # Check for real data: bid/ask exist and aren't both 0 or 1
                        bid = float(m.get("bestBid", 0))
                        ask = float(m.get("bestAsk", 1))
                        
                        # Skip broken/unrealistic prices
                        if bid == 0 and ask == 1:
                            continue
                        if bid >= ask:
                            continue
                        
                        volume = float(m.get("volume24h", 0))
                        liquidity = float(m.get("liquidity", 0))
                        
                        # Only include if has recent activity
                        if volume > 0 or liquidity > 10:
                            markets.append({
                                "id": m.get("id", ""),
                                "name": m.get("question", ""),
                                "bid": bid,
                                "ask": ask,
                                "spread": ((ask - bid) / ((bid + ask) / 2) * 100) if (bid + ask) > 0 else 0,
                                "volume_24h": volume,
                                "volume_7d": float(m.get("volume7d", 0)),
                                "liquidity": liquidity,
                            })
                    except (ValueError, TypeError, KeyError):
                        continue
                
                print(f"✓ Found {len(markets)} open markets")
                
                # Sort by volume descending
                markets = sorted(markets, key=lambda x: x.get("volume_24h", 0), reverse=True)[:50]
                return markets
        
        except Exception as e:
            print(f"API error: {e}")
        
        return markets
    
    def fetch_whale_wallets(self):
        """Fetch most profitable wallets"""
        whales = []
        
        try:
            response = requests.get(
                "https://gamma-api.polymarket.com/users",
                params={"limit": 100},
                timeout=15
            )
            
            if response.status_code == 200:
                users = response.json()
                
                # Get profitable users
                for user in users[:50]:
                    try:
                        address = user.get("address")
                        if not address:
                            continue
                        
                        trades = int(user.get("trade_count", 0))
                        if trades < 5:  # Filter out low-activity wallets
                            continue
                        
                        whales.append({
                            "address": address,
                            "trades": trades,
                            "win_rate": float(user.get("win_rate", 0)) / 100,
                            "pnl_30d": float(user.get("profit_30d", 0)),
                            "pnl_7d": float(user.get("profit_7d", 0)),
                        })
                    except (ValueError, TypeError, KeyError):
                        continue
                
                print(f"✓ Found {len(whales)} active wallets")
        except Exception as e:
            print(f"Whale fetch error: {e}")
        
        return whales[:20]
    
    def fetch_news(self):
        """Fetch recent crypto news"""
        news = []
        
        try:
            response = requests.get(
                "https://api.coingecko.com/api/v3/news",
                timeout=15
            )
            
            if response.status_code == 200:
                items = response.json().get("data", [])
                
                for item in items[:20]:
                    try:
                        news.append({
                            "title": item.get("title", ""),
                            "source": item.get("sources", [{}])[0].get("title", "News"),
                            "url": item.get("url", ""),
                            "time": item.get("published_at", datetime.utcnow().isoformat()),
                        })
                    except (IndexError, KeyError, TypeError):
                        continue
                
                print(f"✓ Found {len(news)} news items")
        except Exception as e:
            print(f"News fetch error: {e}")
        
        return news[:15]
    
    def save_data(self, markets, whales, news):
        """Save to live data file"""
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "markets": markets,
            "whales": whales,
            "news": news,
        }
        
        with open(self.data_file, "w") as f:
            json.dump(data, f, indent=2)
        
        return len(markets), len(whales), len(news)
    
    def update(self):
        """Run full update"""
        print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] Fetching live Polymarket data...")
        
        markets = self.fetch_live_markets()
        whales = self.fetch_whale_wallets()
        news = self.fetch_news()
        
        m, w, n = self.save_data(markets, whales, news)
        print(f"Updated: {m} markets | {w} whales | {n} news")

if __name__ == "__main__":
    terminal = PolybergTerminal()
    terminal.update()
