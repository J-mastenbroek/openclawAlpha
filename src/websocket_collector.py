"""Reliable WebSocket collector for Polymarket CLOB data.

Captures real-time orderbook updates and writes to CSV with validation.
"""

import asyncio
import json
import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import aiohttp
import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PolymarketWebSocketCollector:
    """Collect real-time Polymarket orderbook data via WebSocket."""
    
    def __init__(self, output_dir: Path = Path("data/live")):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.websocket_url = "wss://ws-clob.polymarket.com"
        self.markets = {}  # {market_id: market_data}
        self.orderbook = {}  # {market_id: {bids: [], asks: []}}
        
        # Data validation
        self.validation_stats = {
            "total_updates": 0,
            "valid_updates": 0,
            "invalid_updates": 0,
            "validation_errors": []
        }
        
        self.csv_writers = {}  # {market_id: csv_writer}
        self.csv_files = {}    # {market_id: file_handle}
    
    async def connect(self):
        """Connect to Polymarket WebSocket and start collecting."""
        
        try:
            async with websockets.connect(self.websocket_url) as websocket:
                logger.info("✅ Connected to Polymarket WebSocket")
                
                # Subscribe to market updates
                await websocket.send(json.dumps({
                    "type": "subscribe",
                    "channel": "orderbook",
                    "markets": []  # Empty = all markets
                }))
                
                # Collect data
                while True:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30)
                    await self.process_message(message)
                    
        except asyncio.TimeoutError:
            logger.warning("WebSocket timeout, reconnecting...")
            await asyncio.sleep(5)
            await self.connect()
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await asyncio.sleep(10)
            await self.connect()
    
    async def process_message(self, message: str):
        """Process incoming WebSocket message."""
        
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "market":
                await self.handle_market_update(data)
            elif msg_type == "orderbook":
                await self.handle_orderbook_update(data)
            elif msg_type == "trade":
                await self.handle_trade(data)
                
        except json.JSONDecodeError as e:
            self.validation_stats["invalid_updates"] += 1
            self.validation_stats["validation_errors"].append(f"JSON parse: {e}")
    
    async def handle_market_update(self, data: Dict):
        """Handle market metadata update."""
        
        market_id = data.get("market_id")
        self.markets[market_id] = data
    
    async def handle_orderbook_update(self, data: Dict):
        """Handle orderbook snapshot or delta."""
        
        self.validation_stats["total_updates"] += 1
        
        market_id = data.get("market_id")
        bids = data.get("bids", [])
        asks = data.get("asks", [])
        timestamp_ms = data.get("timestamp_ms")
        
        # Validation
        if not self.validate_orderbook(market_id, bids, asks, timestamp_ms):
            self.validation_stats["invalid_updates"] += 1
            return
        
        self.validation_stats["valid_updates"] += 1
        
        # Write to CSV
        await self.write_orderbook_csv(market_id, bids, asks, timestamp_ms)
    
    def validate_orderbook(
        self,
        market_id: Optional[str],
        bids: list,
        asks: list,
        timestamp_ms: Optional[int]
    ) -> bool:
        """Validate orderbook data."""
        
        # Required fields
        if not market_id or not timestamp_ms:
            self.validation_stats["validation_errors"].append("Missing market_id or timestamp")
            return False
        
        # Bids/asks structure
        if not isinstance(bids, list) or not isinstance(asks, list):
            self.validation_stats["validation_errors"].append("Bids/asks not lists")
            return False
        
        # Price sanity checks
        for bid in bids:
            if not isinstance(bid, (list, tuple)) or len(bid) < 2:
                return False
            price, size = bid[0], bid[1]
            if not (0 < price < 1) or not (size > 0):
                return False
        
        for ask in asks:
            if not isinstance(ask, (list, tuple)) or len(ask) < 2:
                return False
            price, size = ask[0], ask[1]
            if not (0 < price < 1) or not (size > 0):
                return False
        
        # Bid/ask ordering
        if bids and asks:
            best_bid = max(b[0] for b in bids)
            best_ask = min(a[0] for a in asks)
            if best_bid >= best_ask:
                # Crossed book (unusual but valid in fast markets)
                pass
        
        return True
    
    async def write_orderbook_csv(
        self,
        market_id: str,
        bids: list,
        asks: list,
        timestamp_ms: int
    ):
        """Write orderbook to CSV file."""
        
        # Open or create CSV file
        csv_path = self.output_dir / f"{market_id}.csv"
        
        if market_id not in self.csv_files:
            self.csv_files[market_id] = open(csv_path, "a", newline="")
            self.csv_writers[market_id] = csv.writer(self.csv_files[market_id])
            
            # Write header if new file
            if csv_path.stat().st_size == 0:
                self.csv_writers[market_id].writerow([
                    "timestamp_ms", "timestamp_iso",
                    "bid_price_1", "bid_size_1",
                    "ask_price_1", "ask_size_1",
                    "spread", "mid_price",
                    "market_id"
                ])
        
        # Extract top of book
        bid_price_1 = max(b[0] for b in bids) if bids else 0.5
        bid_size_1 = next(b[1] for b in bids if b[0] == bid_price_1) if bids else 0
        
        ask_price_1 = min(a[0] for a in asks) if asks else 0.5
        ask_size_1 = next(a[1] for a in asks if a[0] == ask_price_1) if asks else 0
        
        spread = ask_price_1 - bid_price_1 if (bid_price_1 and ask_price_1) else 0
        mid_price = (bid_price_1 + ask_price_1) / 2 if (bid_price_1 and ask_price_1) else 0.5
        
        timestamp_iso = datetime.fromtimestamp(timestamp_ms / 1000).isoformat()
        
        # Write row
        self.csv_writers[market_id].writerow([
            timestamp_ms,
            timestamp_iso,
            bid_price_1,
            bid_size_1,
            ask_price_1,
            ask_size_1,
            spread,
            mid_price,
            market_id
        ])
        
        # Flush periodically
        if self.validation_stats["valid_updates"] % 100 == 0:
            self.csv_files[market_id].flush()
    
    async def handle_trade(self, data: Dict):
        """Handle trade execution."""
        # Can add trade logging here if needed
        pass
    
    def get_stats(self) -> Dict:
        """Get collection statistics."""
        return {
            "total_updates": self.validation_stats["total_updates"],
            "valid_updates": self.validation_stats["valid_updates"],
            "invalid_updates": self.validation_stats["invalid_updates"],
            "markets_tracked": len(self.markets),
            "validation_errors": self.validation_stats["validation_errors"][-10:]  # Last 10
        }
    
    async def run(self):
        """Main loop."""
        while True:
            try:
                await self.connect()
            except Exception as e:
                logger.error(f"Fatal error: {e}")
                await asyncio.sleep(30)


if __name__ == "__main__":
    collector = PolymarketWebSocketCollector()
    
    try:
        asyncio.run(collector.run())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        print("\n=== Collection Stats ===")
        print(json.dumps(collector.get_stats(), indent=2))
