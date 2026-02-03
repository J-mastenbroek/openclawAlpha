#!/usr/bin/env python3
"""
Polyberg: Real Polymarket data via Gamma API.
Fetches LIVE markets only (filtering out dead/resolved ones).
Uses proper filtering to get current trading markets.
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
        """Fetch LIVE markets from Gamma API"""
        markets = []
        
        try:
            print("Fetching live markets from Gamma API...")
            
            # Get markets - correct approach with pagination
            response = requests.get(
                "https://gamma-api.polymarket.com/markets",
                params={
                    "limit": 100,
                    "offset": 0,
                },
                timeout=15
            )
            
            if response.status_code == 200:
                all_markets = response.json()
                print(f"Got {len(all_markets)} markets from API")
                
                # Filter for LIVE markets only
                # Live = has real prices + volume/liquidity
                for m in all_markets:
                    try:
                        bid = float(m.get("bestBid", 0))
                        ask = float(m.get("bestAsk", 1))
                        volume = float(m.get("volume24h", 0))
                        
                        # Skip:
                        # - Markets with fake prices (0 bid, 1 ask = dead)
                        # - Markets with no liquidity
                        if bid == 0 and ask == 1:
                            continue
                        if bid >= ask:  # Invalid spread
                            continue
                        if volume == 0 and float(m.get("liquidity", 0)) < 20:
                            continue
                        
                        # This is a live market
                        markets.append({
                            "id": m.get("id", ""),
                            "name": m.get("question", ""),
                            "bid": bid,
                            "ask": ask,
                            "spread": ((ask - bid) / ((bid + ask) / 2) * 100) if (bid + ask) > 0 else 0,
                            "volume_24h": volume,
                            "volume_7d": float(m.get("volume7d", 0)),
                            "liquidity": float(m.get("liquidity", 0)),
                        })
                    except (ValueError, TypeError, KeyError):
                        continue
                
                print(f"✓ Found {len(markets)} LIVE markets (filtered)")
                return sorted(markets, key=lambda x: x.get("volume_24h", 0), reverse=True)[:100]
        
        except Exception as e:
            print(f"API error: {e}")
        
        return []
    
    def fetch_whale_wallets(self):
        """Fetch top wallets"""
        whales = []
        try:
            response = requests.get(
                "https://gamma-api.polymarket.com/users",
                params={"limit": 50},
                timeout=15
            )
            
            if response.status_code == 200:
                users = response.json()
                
                for user in users[:25]:
                    try:
                        address = user.get("address")
                        if address:
                            whales.append({
                                "address": address,
                                "trades": int(user.get("trade_count", 0)),
                                "win_rate": float(user.get("win_rate", 0)) / 100,
                                "pnl_30d": float(user.get("profit_30d", 0)),
                                "pnl_7d": float(user.get("profit_7d", 0)),
                            })
                    except:
                        continue
        except Exception as e:
            print(f"Whale fetch error: {e}")
        
        return whales
    
    def fetch_news(self):
        """Fetch crypto news"""
        news = []
        try:
            response = requests.get(
                "https://api.coingecko.com/api/v3/news",
                timeout=15
            )
            
            if response.status_code == 200:
                items = response.json().get("data", [])[:12]
                for item in items:
                    try:
                        news.append({
                            "title": item.get("title", ""),
                            "source": item.get("sources", [{}])[0].get("title", "News"),
                            "url": item.get("url", ""),
                            "time": item.get("published_at", datetime.utcnow().isoformat()),
                        })
                    except:
                        continue
        except Exception as e:
            print(f"News error: {e}")
        
        return news
    
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
        
        print(f"✓ Saved: {len(markets)} live markets | {len(whales)} whales | {len(news)} news")
    
    def update(self):
        """Full update"""
        print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] Updating Polyberg...")
        
        markets = self.fetch_live_markets()
        whales = self.fetch_whale_wallets()
        news = self.fetch_news()
        
        self.save_data(markets, whales, news)

if __name__ == "__main__":
    terminal = PolybergTerminal()
    terminal.update()
