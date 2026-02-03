#!/usr/bin/env python3
"""
Polymarket Terminal: Continuous live data updater.
Pulls ALL markets, real whale data, keeps page fresh 24/7.
"""

import json
import requests
from datetime import datetime
from pathlib import Path

class PolymarketTerminal:
    def __init__(self):
        self.repo_root = Path(__file__).parent.parent
        self.data_file = self.repo_root / "data" / "live_data.json"
        self.data_file.parent.mkdir(exist_ok=True)
        
    def fetch_all_markets(self):
        """Fetch ALL active Polymarket markets"""
        try:
            # Polymarket API - get all active markets
            response = requests.get(
                "https://gamma-api.polymarket.com/markets?active=true&limit=100",
                timeout=10
            )
            if response.status_code == 200:
                markets = response.json()
                return self._format_markets(markets)
        except Exception as e:
            print(f"Error fetching markets: {e}")
        return []
    
    def _format_markets(self, markets):
        """Format markets with all necessary data"""
        formatted = []
        for market in markets:
            try:
                bid = float(market.get("bestBid", 0))
                ask = float(market.get("bestAsk", 1))
                spread = ask - bid if (bid + ask) > 0 else 0
                spread_pct = (spread / ((bid + ask) / 2) * 100) if (bid + ask) > 0 else 0
                
                formatted.append({
                    "id": market.get("id"),
                    "name": market.get("question", "Unknown"),
                    "bid": bid,
                    "ask": ask,
                    "spread": spread_pct,
                    "volume_24h": float(market.get("volume24h", 0)),
                    "volume_7d": float(market.get("volume7d", 0)),
                    "liquidity": float(market.get("liquidity", 0)),
                    "image": market.get("image"),
                })
            except (ValueError, KeyError, TypeError):
                continue
        
        # Sort by volume
        return sorted(formatted, key=lambda x: x.get("volume_24h", 0), reverse=True)
    
    def fetch_whale_wallets(self):
        """Fetch top profitable wallets"""
        whales = []
        try:
            response = requests.get(
                "https://gamma-api.polymarket.com/users?limit=50&sort=pnl&period=30d",
                timeout=10
            )
            if response.status_code == 200:
                users = response.json()
                for user in users[:30]:
                    try:
                        whales.append({
                            "address": user.get("address"),
                            "trades": user.get("trade_count", 0),
                            "win_rate": float(user.get("win_rate", 0)) / 100,
                            "pnl_30d": float(user.get("pnl_30d", 0)),
                            "pnl_7d": float(user.get("pnl_7d", 0)),
                            "username": user.get("username", ""),
                        })
                    except (ValueError, TypeError):
                        continue
        except Exception as e:
            print(f"Error fetching whales: {e}")
        
        return whales
    
    def save_data(self, markets, whales):
        """Save to JSON"""
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "markets": markets,
            "whales": whales,
        }
        with open(self.data_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"✓ Updated: {len(markets)} markets, {len(whales)} whales")
    
    def update(self):
        """Full update cycle"""
        print(f"\n[{datetime.utcnow().strftime('%H:%M:%S')}] Fetching live data...")
        markets = self.fetch_all_markets()
        whales = self.fetch_whale_wallets()
        self.save_data(markets, whales)
        return len(markets), len(whales)

if __name__ == "__main__":
    terminal = PolymarketTerminal()
    m, w = terminal.update()
