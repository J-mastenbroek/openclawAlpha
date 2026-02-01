"""Analysis and pattern detection."""

import json
from datetime import datetime
from typing import Dict, List, Optional

class MarketAnalyzer:
    def __init__(self):
        self.findings = []
    
    def detect_settlement_misprice(self, market: Dict) -> Optional[Dict]:
        """
        Detect if a settled/resolving market has mispriced outcomes.
        Settlement arbitrage: catch the cleanup phase where prices haven't synced.
        """
        if market.get("status") != "resolved":
            return None
        
        # Check if there are still active orders at stale prices
        resolved_outcome = market.get("resolvedOutcome")
        if not resolved_outcome:
            return None
        
        # Quick heuristic: if winning outcome still has losers at >10% odds
        # that's inefficient cleanup phase
        outcome_prices = market.get("outcomeTokens", {})
        
        for outcome_id, price in outcome_prices.items():
            if outcome_id != resolved_outcome and float(price) > 0.1:
                return {
                    "type": "settlement_misprice",
                    "market_id": market.get("id"),
                    "resolved_outcome": resolved_outcome,
                    "stale_price": float(price),
                    "stale_outcome": outcome_id,
                    "timestamp": datetime.now().isoformat()
                }
        
        return None
    
    def detect_retail_flow(self, trades: List[Dict], market: Dict) -> Optional[Dict]:
        """
        Detect retail flow patterns: small, frequent orders from many addresses.
        """
        if not trades:
            return None
        
        # Retail signature: many small orders, rapid succession
        order_sizes = [float(t.get("size", 0)) for t in trades]
        order_count = len(trades)
        
        if order_count < 5:
            return None
        
        avg_size = sum(order_sizes) / order_count
        
        # Heuristic: if average order <$100 and many orders, likely retail
        if avg_size < 100 and order_count > 10:
            return {
                "type": "retail_flow_detected",
                "market_id": market.get("id"),
                "order_count": order_count,
                "avg_order_size": avg_size,
                "total_volume": sum(order_sizes),
                "timestamp": datetime.now().isoformat()
            }
        
        return None
    
    def detect_price_momentum(self, market: Dict, recent_trades: List[Dict]) -> Optional[Dict]:
        """
        Detect price momentum: if price has moved significantly in one direction.
        """
        if not recent_trades or len(recent_trades) < 2:
            return None
        
        # Get directional bias from recent trades
        yes_trades = sum(1 for t in recent_trades if t.get("side") == "yes")
        no_trades = len(recent_trades) - yes_trades
        
        if yes_trades > no_trades * 1.5:
            momentum = "bullish_yes"
            ratio = yes_trades / len(recent_trades)
        elif no_trades > yes_trades * 1.5:
            momentum = "bullish_no"
            ratio = no_trades / len(recent_trades)
        else:
            return None
        
        return {
            "type": "price_momentum",
            "market_id": market.get("id"),
            "momentum": momentum,
            "directional_ratio": ratio,
            "timestamp": datetime.now().isoformat()
        }
    
    def analyze_market(self, market: Dict, trades: List[Dict]) -> List[Dict]:
        """Run all analyses on a market."""
        findings = []
        
        settlement = self.detect_settlement_misprice(market)
        if settlement:
            findings.append(settlement)
        
        retail = self.detect_retail_flow(trades, market)
        if retail:
            findings.append(retail)
        
        momentum = self.detect_price_momentum(market, trades)
        if momentum:
            findings.append(momentum)
        
        return findings
