#!/usr/bin/env python3
"""
Polyberg Terminal: Real-time Polymarket data fetcher.
Pulls only ACTIVE markets with real volume.
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
        
    def fetch_markets(self):
        """Fetch active markets with real trading volume"""
        try:
            # Get markets sorted by volume descending
            response = requests.get(
                "https://gamma-api.polymarket.com/markets",
                params={
                    "active": "true",
                    "limit": 100,
                    "sort": "volume24h"
                },
                timeout=15
            )
            
            if response.status_code == 200:
                markets = response.json()
                # Filter: only markets with actual volume/liquidity
                active = []
                for m in markets:
                    vol = float(m.get("volume24h", 0))
                    liq = float(m.get("liquidity", 0))
                    
                    # Only include if has real activity
                    if vol > 100 or liq > 10:
                        bid = float(m.get("bestBid", 0))
                        ask = float(m.get("bestAsk", 1))
                        spread = ask - bid if (bid + ask) > 0 else 0
                        spread_pct = (spread / ((bid + ask) / 2) * 100) if (bid + ask) > 0 else 0
                        
                        active.append({
                            "id": m.get("id"),
                            "name": m.get("question", ""),
                            "bid": bid,
                            "ask": ask,
                            "spread": spread_pct,
                            "volume_24h": vol,
                            "volume_7d": float(m.get("volume7d", 0)),
                            "liquidity": liq,
                        })
                
                return sorted(active, key=lambda x: x.get("volume_24h", 0), reverse=True)[:50]
        except Exception as e:
            print(f"Market fetch error: {e}")
        
        return []
    
    def fetch_whale_wallets(self):
        """Fetch top winning wallets"""
        whales = []
        try:
            response = requests.get(
                "https://gamma-api.polymarket.com/users",
                params={
                    "limit": 50,
                    "sort": "pnl",
                    "period": "30d"
                },
                timeout=15
            )
            
            if response.status_code == 200:
                users = response.json()
                for user in users[:20]:
                    try:
                        address = user.get("address")
                        if address:
                            whales.append({
                                "address": address,
                                "trades": user.get("trade_count", 0),
                                "win_rate": min(1.0, float(user.get("win_rate", 0))),
                                "pnl_30d": float(user.get("pnl_30d", 0)),
                                "pnl_7d": float(user.get("pnl_7d", 0)),
                            })
                    except (ValueError, TypeError, KeyError):
                        continue
        except Exception as e:
            print(f"Whale fetch error: {e}")
        
        return whales
    
    def save_data(self, markets, whales):
        """Save to JSON file"""
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "markets": markets,
            "whales": whales,
        }
        with open(self.data_file, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"✓ {len(markets)} active markets | {len(whales)} top whales")
        return True
    
    def update(self):
        """Run update cycle"""
        print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] Fetching Polymarket data...")
        markets = self.fetch_markets()
        whales = self.fetch_whale_wallets()
        self.save_data(markets, whales)

if __name__ == "__main__":
    terminal = PolybergTerminal()
    terminal.update()
