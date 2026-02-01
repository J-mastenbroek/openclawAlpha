"""Polymarket data ingestion and analysis."""

import requests
import json
from datetime import datetime
from typing import Optional, Dict, List

POLYMARKET_API = "https://clob.polymarket.com"

class PolymarketClient:
    def __init__(self):
        self.base_url = POLYMARKET_API
        self.session = requests.Session()
    
    def get_markets(self, limit: int = 100) -> List[Dict]:
        """Fetch active markets."""
        try:
            resp = self.session.get(
                f"{self.base_url}/markets",
                params={"limit": limit, "active": True},
                timeout=10
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Error fetching markets: {e}")
            return []
    
    def get_market(self, market_id: str) -> Optional[Dict]:
        """Fetch single market."""
        try:
            resp = self.session.get(
                f"{self.base_url}/markets/{market_id}",
                timeout=10
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Error fetching market {market_id}: {e}")
            return None
    
    def get_orderbook(self, market_id: str) -> Optional[Dict]:
        """Fetch orderbook for market."""
        try:
            resp = self.session.get(
                f"{self.base_url}/orderbook/{market_id}",
                timeout=10
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Error fetching orderbook {market_id}: {e}")
            return None
    
    def get_trades(self, market_id: str, limit: int = 50) -> List[Dict]:
        """Fetch recent trades for market."""
        try:
            resp = self.session.get(
                f"{self.base_url}/trades/{market_id}",
                params={"limit": limit},
                timeout=10
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Error fetching trades {market_id}: {e}")
            return []
