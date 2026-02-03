#!/usr/bin/env python3
"""
Polyberg: Real-time Polymarket terminal data fetcher.
Integrates Hans's production Polymarket capturer with Polyberg terminal.
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from polymarket_capturer import GammaClient, PriceCache, OrderBook, rtds_prices_listener, utc_now
import requests

class PolybergLiveFeeder:
    def __init__(self):
        self.repo_root = Path(__file__).parent.parent
        self.data_file = self.repo_root / "data" / "live_data.json"
        self.gamma = GammaClient()
        self.price_cache = PriceCache()
        
    def get_live_markets(self) -> list:
        """Fetch current 15-minute markets from Gamma API"""
        try:
            events = self.gamma.scan_15m_events()
            
            markets = []
            for e in events:
                try:
                    slug = e.get("slug")
                    asset = self.gamma.extract_asset(e)
                    market_list = e.get("markets", [])
                    
                    if not market_list:
                        continue
                    
                    m = market_list[0]
                    bid = float(m.get("bestBid", 0))
                    ask = float(m.get("bestAsk", 1))
                    
                    # Skip dead markets
                    if bid == 0 and ask == 1:
                        continue
                    if bid >= ask:
                        continue
                    
                    markets.append({
                        "id": m.get("id", ""),
                        "name": e.get("title") or e.get("slug", "Unknown"),
                        "bid": bid,
                        "ask": ask,
                        "spread": ((ask - bid) / ((bid + ask) / 2) * 100) if (bid + ask) > 0 else 0,
                        "volume_24h": float(m.get("volume24h", 0)),
                        "volume_7d": float(m.get("volume7d", 0)),
                        "liquidity": float(m.get("liquidity", 0)),
                    })
                except (ValueError, TypeError, KeyError):
                    continue
            
            # Sort by volume
            markets = sorted(markets, key=lambda x: x.get("volume_24h", 0), reverse=True)[:50]
            print(f"✓ Live markets: {len(markets)}")
            return markets
        
        except Exception as e:
            print(f"Market fetch error: {e}")
            return []
    
    def get_whale_wallets(self) -> list:
        """Fetch top wallets from Gamma API"""
        whales = []
        try:
            users = self.gamma.get("users", {"limit": 50})
            
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
            
            print(f"✓ Whale wallets: {len(whales)}")
        except Exception as e:
            print(f"Whale fetch error: {e}")
        
        return whales
    
    def get_news(self) -> list:
        """Fetch crypto news from CoinGecko"""
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
                            "time": item.get("published_at", datetime.now(timezone.utc).isoformat()),
                        })
                    except:
                        continue
            
            print(f"✓ News items: {len(news)}")
        except Exception as e:
            print(f"News error: {e}")
        
        return news
    
    def save_data(self, markets: list, whales: list, news: list):
        """Save all data to live_data.json"""
        data = {
            "timestamp": utc_now().isoformat(),
            "markets": markets,
            "whales": whales,
            "news": news,
        }
        
        with open(self.data_file, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"✓ Saved: {len(markets)} markets | {len(whales)} whales | {len(news)} news")
    
    def update(self):
        """Full update cycle"""
        print(f"[{utc_now().strftime('%H:%M:%S')}] Fetching live Polymarket data...")
        
        markets = self.get_live_markets()
        whales = self.get_whale_wallets()
        news = self.get_news()
        
        self.save_data(markets, whales, news)

if __name__ == "__main__":
    feeder = PolybergLiveFeeder()
    feeder.update()
