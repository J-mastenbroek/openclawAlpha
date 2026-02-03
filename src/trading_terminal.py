"""
Trading Terminal - CLI interface for Polymarket trading with market intelligence
"""

import asyncio
import json
from typing import Dict, List, Optional
from datetime import datetime
import aiohttp
from dataclasses import dataclass


@dataclass
class MarketInfo:
    market_id: str
    title: str
    bid: float
    ask: float
    liquidity: float
    volume_24h: float
    outcomes: List[str]


class TradingTerminal:
    """Interactive trading terminal for Polymarket"""
    
    def __init__(self):
        self.session = None
        self.portfolio: Dict[str, float] = {}
        self.open_positions: List[Dict] = []
        self.market_cache: Dict[str, MarketInfo] = {}
    
    async def start(self):
        self.session = aiohttp.ClientSession()
    
    async def stop(self):
        if self.session:
            await self.session.close()
    
    async def fetch_markets(self) -> List[MarketInfo]:
        """Fetch all active markets from Polymarket"""
        try:
            url = "https://polymarket.com/api/markets"
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    markets = []
                    
                    for market in data.get("data", [])[:50]:  # Top 50 markets
                        market_info = MarketInfo(
                            market_id=market.get("id", ""),
                            title=market.get("title", ""),
                            bid=market.get("bid_price", 0),
                            ask=market.get("ask_price", 0),
                            liquidity=market.get("liquidity", 0),
                            volume_24h=market.get("volume_24h", 0),
                            outcomes=market.get("outcomes", [])
                        )
                        markets.append(market_info)
                        self.market_cache[market_info.market_id] = market_info
                    
                    return markets
        except Exception as e:
            print(f"Error fetching markets: {e}")
        
        return []
    
    async def place_order(self, market_id: str, outcome: str, amount: float, price: float) -> Dict:
        """Place a trade order"""
        try:
            payload = {
                "market_id": market_id,
                "outcome": outcome,
                "amount": amount,
                "price": price,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add to positions
            self.open_positions.append({
                **payload,
                "status": "pending",
                "pnl": 0
            })
            
            return {
                "status": "success",
                "order_id": f"order_{len(self.open_positions)}",
                "details": payload
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def close_position(self, position_id: int) -> Dict:
        """Close an open position"""
        if position_id < len(self.open_positions):
            pos = self.open_positions[position_id]
            pos["status"] = "closed"
            pos["closed_at"] = datetime.now().isoformat()
            
            return {
                "status": "success",
                "position": pos
            }
        
        return {"status": "error", "message": "Position not found"}
    
    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary"""
        total_value = sum(pos.get("amount", 0) * pos.get("price", 0) 
                         for pos in self.open_positions if pos.get("status") == "open")
        
        open_count = sum(1 for pos in self.open_positions if pos.get("status") == "open")
        closed_count = sum(1 for pos in self.open_positions if pos.get("status") == "closed")
        
        return {
            "total_positions": len(self.open_positions),
            "open": open_count,
            "closed": closed_count,
            "total_value": total_value,
            "portfolio": self.portfolio
        }
    
    def get_market_info(self, market_id: str) -> Optional[Dict]:
        """Get detailed market information"""
        market = self.market_cache.get(market_id)
        if market:
            spread = market.ask - market.bid
            spread_pct = (spread / market.bid * 100) if market.bid > 0 else 0
            
            return {
                "id": market.market_id,
                "title": market.title,
                "bid": market.bid,
                "ask": market.ask,
                "spread": spread,
                "spread_pct": spread_pct,
                "liquidity": market.liquidity,
                "volume_24h": market.volume_24h,
                "outcomes": market.outcomes
            }
        return None
    
    async def display_markets(self, limit: int = 10):
        """Display top markets"""
        markets = await self.fetch_markets()
        
        print("\n" + "="*100)
        print(f"{'MARKET':<40} {'BID':>8} {'ASK':>8} {'SPREAD':>8} {'24H VOL':>15} {'LIQUIDITY':>15}")
        print("="*100)
        
        for market in markets[:limit]:
            spread = market.ask - market.bid
            spread_pct = (spread / market.bid * 100) if market.bid > 0 else 0
            
            print(f"{market.title[:38]:<40} {market.bid:>8.4f} {market.ask:>8.4f} {spread_pct:>7.2f}% ${market.volume_24h:>13,.0f} ${market.liquidity:>13,.0f}")
        
        print("="*100 + "\n")


async def main():
    """Demo terminal"""
    terminal = TradingTerminal()
    await terminal.start()
    
    # Display markets
    await terminal.display_markets(10)
    
    # Get summary
    print(terminal.get_portfolio_summary())
    
    await terminal.stop()


if __name__ == "__main__":
    asyncio.run(main())
