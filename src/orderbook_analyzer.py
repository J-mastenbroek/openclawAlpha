"""
Orderbook Analyzer - Detect irregular orderbook behavior and anomalies
"""

import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from statistics import stdev, mean
import aiohttp


@dataclass
class OrderbookAnomaly:
    """Represents an orderbook anomaly"""
    timestamp: str
    market_id: str
    anomaly_type: str  # "spread_spike", "volume_surge", "bid_ask_imbalance"
    severity: float  # 0-1
    description: str
    data: Dict


class OrderbookAnalyzer:
    """Analyze orderbook patterns and detect anomalies"""
    
    def __init__(self, history_window: int = 100):
        """
        Args:
            history_window: Number of orderbook snapshots to track for baseline
        """
        self.history_window = history_window
        self.orderbook_history: Dict[str, List[Dict]] = {}
        self.anomalies: List[OrderbookAnomaly] = []
        self.session = None
    
    async def start(self):
        self.session = aiohttp.ClientSession()
    
    async def stop(self):
        if self.session:
            await self.session.close()
    
    async def fetch_orderbook(self, market_id: str) -> Dict:
        """Fetch current orderbook from Polymarket API"""
        try:
            url = f"https://polymarket.com/api/market/{market_id}/orderbook"
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            print(f"Error fetching orderbook for {market_id}: {e}")
        return {}
    
    def analyze_orderbook(self, market_id: str, orderbook: Dict) -> List[OrderbookAnomaly]:
        """Analyze orderbook and detect anomalies"""
        anomalies = []
        
        # Store in history
        if market_id not in self.orderbook_history:
            self.orderbook_history[market_id] = []
        
        self.orderbook_history[market_id].append(orderbook)
        if len(self.orderbook_history[market_id]) > self.history_window:
            self.orderbook_history[market_id].pop(0)
        
        # Check for spread spike
        spread_anomaly = self._check_spread_spike(market_id, orderbook)
        if spread_anomaly:
            anomalies.append(spread_anomaly)
        
        # Check for volume surge
        volume_anomaly = self._check_volume_surge(market_id, orderbook)
        if volume_anomaly:
            anomalies.append(volume_anomaly)
        
        # Check for bid-ask imbalance
        imbalance_anomaly = self._check_bid_ask_imbalance(market_id, orderbook)
        if imbalance_anomaly:
            anomalies.append(imbalance_anomaly)
        
        self.anomalies.extend(anomalies)
        return anomalies
    
    def _check_spread_spike(self, market_id: str, orderbook: Dict) -> Optional[OrderbookAnomaly]:
        """Detect unusual bid-ask spreads"""
        history = self.orderbook_history.get(market_id, [])
        
        if len(history) < 10:
            return None
        
        # Calculate spreads
        spreads = []
        for ob in history:
            bid = ob.get("bids", [[0]])[0][0] if ob.get("bids") else 0
            ask = ob.get("asks", [[1]])[0][0] if ob.get("asks") else 1
            if bid > 0 and ask > 0:
                spreads.append((ask - bid) / bid)
        
        if len(spreads) < 5:
            return None
        
        current_spread = spreads[-1]
        baseline_spread = mean(spreads[:-1])
        stdev_spread = stdev(spreads[:-1]) if len(spreads) > 1 else 0
        
        # Alert if spread is 2+ std devs above mean
        if stdev_spread > 0 and current_spread > baseline_spread + (2 * stdev_spread):
            severity = min(1.0, (current_spread - baseline_spread) / (2 * stdev_spread))
            
            return OrderbookAnomaly(
                timestamp=datetime.now().isoformat(),
                market_id=market_id,
                anomaly_type="spread_spike",
                severity=severity,
                description=f"Spread spike: {current_spread:.4f} vs baseline {baseline_spread:.4f}",
                data={
                    "current": current_spread,
                    "baseline": baseline_spread,
                    "stdev": stdev_spread
                }
            )
        
        return None
    
    def _check_volume_surge(self, market_id: str, orderbook: Dict) -> Optional[OrderbookAnomaly]:
        """Detect unusual trading volume"""
        history = self.orderbook_history.get(market_id, [])
        
        if len(history) < 10:
            return None
        
        # Calculate volumes
        volumes = []
        for ob in history:
            bid_vol = sum(item[1] for item in ob.get("bids", []))
            ask_vol = sum(item[1] for item in ob.get("asks", []))
            volumes.append(bid_vol + ask_vol)
        
        current_volume = volumes[-1]
        baseline_volume = mean(volumes[:-1])
        stdev_volume = stdev(volumes[:-1]) if len(volumes) > 1 else 0
        
        # Alert if volume is 2.5x baseline
        if baseline_volume > 0 and current_volume > baseline_volume * 2.5:
            severity = min(1.0, (current_volume - baseline_volume) / baseline_volume)
            
            return OrderbookAnomaly(
                timestamp=datetime.now().isoformat(),
                market_id=market_id,
                anomaly_type="volume_surge",
                severity=severity,
                description=f"Volume surge: {current_volume:.0f} vs baseline {baseline_volume:.0f}",
                data={
                    "current": current_volume,
                    "baseline": baseline_volume,
                    "ratio": current_volume / baseline_volume if baseline_volume > 0 else 0
                }
            )
        
        return None
    
    def _check_bid_ask_imbalance(self, market_id: str, orderbook: Dict) -> Optional[OrderbookAnomaly]:
        """Detect bid-ask imbalance"""
        history = self.orderbook_history.get(market_id, [])
        
        if len(history) < 5:
            return None
        
        # Calculate imbalances
        imbalances = []
        for ob in history:
            bid_vol = sum(item[1] for item in ob.get("bids", []))
            ask_vol = sum(item[1] for item in ob.get("asks", []))
            total = bid_vol + ask_vol
            
            if total > 0:
                imbalance = (bid_vol - ask_vol) / total
                imbalances.append(imbalance)
        
        if len(imbalances) < 3:
            return None
        
        current_imbalance = abs(imbalances[-1])
        baseline_imbalance = mean([abs(x) for x in imbalances[:-1]])
        
        # Alert if imbalance is severe
        if current_imbalance > 0.6:
            direction = "bid-heavy" if imbalances[-1] > 0 else "ask-heavy"
            severity = min(1.0, current_imbalance)
            
            return OrderbookAnomaly(
                timestamp=datetime.now().isoformat(),
                market_id=market_id,
                anomaly_type="bid_ask_imbalance",
                severity=severity,
                description=f"Severe {direction} imbalance: {current_imbalance:.2%}",
                data={
                    "current": current_imbalance,
                    "baseline": baseline_imbalance,
                    "direction": direction
                }
            )
        
        return None
    
    def get_anomalies(self, market_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get anomalies, optionally filtered by market"""
        anomalies = self.anomalies
        
        if market_id:
            anomalies = [a for a in anomalies if a.market_id == market_id]
        
        # Return most recent
        return [asdict(a) for a in sorted(anomalies, key=lambda x: x.timestamp, reverse=True)[:limit]]


async def main():
    """Demo orderbook analysis"""
    analyzer = OrderbookAnalyzer()
    await analyzer.start()
    
    # Example usage would go here
    # orderbook = await analyzer.fetch_orderbook("market_id")
    # anomalies = analyzer.analyze_orderbook("market_id", orderbook)
    
    await analyzer.stop()


if __name__ == "__main__":
    asyncio.run(main())
