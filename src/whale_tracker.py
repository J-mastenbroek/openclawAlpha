"""
Whale Tracker - Monitor large wallet movements on Polymarket
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import aiohttp
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class WhaleTrade:
    """Represents a large whale transaction"""
    timestamp: str
    wallet: str
    market_id: str
    action: str  # "buy" or "sell"
    outcome: str
    amount: float
    price: float
    position_size: float
    market_impact: float  # estimated %


class WhaleTracker:
    """Track whale movements across Polymarket"""
    
    def __init__(self, min_position_usd: float = 10000):
        """
        Args:
            min_position_usd: Minimum position size to track as "whale"
        """
        self.min_position_usd = min_position_usd
        self.whale_positions: Dict[str, List[WhaleTrade]] = defaultdict(list)
        self.market_whales: Dict[str, List[str]] = defaultdict(set)
        self.session = None
    
    async def start(self):
        """Initialize async session"""
        self.session = aiohttp.ClientSession()
    
    async def stop(self):
        """Cleanup"""
        if self.session:
            await self.session.close()
    
    async def fetch_market_trades(self, market_id: str, limit: int = 100) -> List[Dict]:
        """Fetch recent trades for a market from Polymarket API"""
        try:
            url = f"https://polymarket.com/api/market/{market_id}/trades"
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            print(f"Error fetching trades for {market_id}: {e}")
        return []
    
    def detect_whale_trades(self, trades: List[Dict]) -> List[WhaleTrade]:
        """Identify whale trades from transaction list"""
        whale_trades = []
        
        for trade in trades:
            # Extract trade data
            amount_usd = trade.get("amount", 0)
            
            # Flag as whale if above threshold
            if amount_usd >= self.min_position_usd:
                whale_trade = WhaleTrade(
                    timestamp=trade.get("timestamp", datetime.now().isoformat()),
                    wallet=trade.get("user", "unknown"),
                    market_id=trade.get("market_id", ""),
                    action=trade.get("action", "unknown"),
                    outcome=trade.get("outcome", ""),
                    amount=amount_usd,
                    price=trade.get("price", 0),
                    position_size=trade.get("position_size", 0),
                    market_impact=self._estimate_market_impact(trade)
                )
                whale_trades.append(whale_trade)
        
        return whale_trades
    
    def _estimate_market_impact(self, trade: Dict) -> float:
        """Estimate market impact percentage"""
        amount = trade.get("amount", 0)
        market_liquidity = trade.get("liquidity", 100000)
        
        if market_liquidity == 0:
            return 0
        
        return (amount / market_liquidity) * 100
    
    async def track_market(self, market_id: str):
        """Track a specific market for whale activity"""
        trades = await self.fetch_market_trades(market_id)
        whales = self.detect_whale_trades(trades)
        
        for whale in whales:
            self.whale_positions[whale.wallet].append(whale)
            self.market_whales[market_id].add(whale.wallet)
        
        return whales
    
    def get_whale_positions(self, wallet: Optional[str] = None) -> Dict:
        """Get whale positions, optionally filtered by wallet"""
        if wallet:
            trades = self.whale_positions.get(wallet, [])
            return {
                "wallet": wallet,
                "trades": [asdict(t) for t in trades],
                "total_positions": len(trades),
                "total_value": sum(t.amount for t in trades)
            }
        
        return {
            "total_whales": len(self.whale_positions),
            "active_markets": len(self.market_whales),
            "positions": {
                wallet: {
                    "count": len(trades),
                    "total_value": sum(t.amount for t in trades),
                    "markets": list(set(t.market_id for t in trades))
                }
                for wallet, trades in self.whale_positions.items()
            }
        }
    
    def get_market_whales(self, market_id: str) -> Dict:
        """Get all whales active in a market"""
        whales = self.market_whales.get(market_id, set())
        return {
            "market_id": market_id,
            "whale_count": len(whales),
            "whales": list(whales)
        }


async def main():
    """Demo whale tracking"""
    tracker = WhaleTracker(min_position_usd=5000)
    await tracker.start()
    
    # Example: track a market
    # market_id = "0x1234..."
    # whales = await tracker.track_market(market_id)
    # print(tracker.get_whale_positions())
    
    await tracker.stop()


if __name__ == "__main__":
    asyncio.run(main())
