"""Analysis and pattern detection."""

import json
from datetime import datetime
from typing import Dict, List, Optional

class MarketAnalyzer:
    def __init__(self):
        self.findings = []
    
    def detect_settlement_misprice(self, market: Dict) -> Optional[Dict]:
        """
        Detect if a closed market has mispriced outcomes.
        Settlement arbitrage: catch markets with inefficient pricing.
        """
        if not market.get("closed"):
            return None
        
        # Look for markets that just closed but still accepting orders (lag)
        tokens = market.get("tokens", [])
        if len(tokens) < 2:
            return None
        
        # Check outcome token prices
        prices = [float(t.get("price", 0)) for t in tokens]
        
        # If winner marked but other outcomes still have significant price, inefficient
        for i, token in enumerate(tokens):
            if token.get("winner"):  # This is the resolved outcome
                # Check if losers still have >5% price
                for j, other_token in enumerate(tokens):
                    if i != j and float(other_token.get("price", 0)) > 0.05:
                        return {
                            "type": "settlement_misprice",
                            "market_id": market.get("condition_id"),
                            "winner": token.get("outcome"),
                            "stale_loser": other_token.get("outcome"),
                            "stale_price": float(other_token.get("price", 0)),
                            "timestamp": datetime.now().isoformat()
                        }
        
        return None
    
    def detect_retail_flow(self, trades: List[Dict], market: Dict) -> Optional[Dict]:
        """
        Detect retail flow patterns: markets with many small bets.
        Use volume and minimum order size as proxy.
        """
        # Look for markets actively trading (accepting orders) with low minimums
        if not market.get("accepting_orders"):
            return None
        
        min_order = market.get("minimum_order_size", 15)
        
        # If minimum order is very low, indicates retail-friendly market
        # Combined with active trading = potential retail flow
        if min_order <= 10 and market.get("active"):
            volume_proxy = len(market.get("tokens", []))  # proxy for activity
            
            # Check spread (bid-ask like behavior)
            tokens = market.get("tokens", [])
            if len(tokens) == 2:
                price_diff = abs(float(tokens[0].get("price", 0.5)) - 0.5)
                
                # Tight markets around 50-50 with low minimums = retail arbing
                if price_diff < 0.15 and min_order < 10:
                    return {
                        "type": "retail_flow_detected",
                        "market_id": market.get("condition_id"),
                        "min_order_size": min_order,
                        "price_proximity_to_50": price_diff,
                        "timestamp": datetime.now().isoformat()
                    }
        
        return None
    
    def detect_price_momentum(self, market: Dict, recent_trades: List[Dict]) -> Optional[Dict]:
        """
        Detect price imbalance: if one outcome is significantly more expensive.
        Indicates strong directional bias.
        """
        tokens = market.get("tokens", [])
        if len(tokens) < 2:
            return None
        
        # Get prices for binary market
        if len(tokens) == 2:
            price1 = float(tokens[0].get("price", 0.5))
            price2 = float(tokens[1].get("price", 0.5))
            
            # Extreme prices (>70% or <30%) indicate strong momentum
            if price1 > 0.70:
                return {
                    "type": "price_momentum",
                    "market_id": market.get("condition_id"),
                    "momentum": "bullish_outcome_1",
                    "price": price1,
                    "outcome": tokens[0].get("outcome"),
                    "timestamp": datetime.now().isoformat()
                }
            elif price1 < 0.30:
                return {
                    "type": "price_momentum",
                    "market_id": market.get("condition_id"),
                    "momentum": "bullish_outcome_2",
                    "price": price1,
                    "outcome": tokens[1].get("outcome"),
                    "timestamp": datetime.now().isoformat()
                }
        
        return None
    
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
