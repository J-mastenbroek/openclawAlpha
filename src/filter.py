"""Signal filtering and quality scoring."""

from typing import Dict, Optional, List
from datetime import datetime

class SignalFilter:
    """Filter and score market signals for quality."""
    
    @staticmethod
    def score_momentum_signal(signal: Dict) -> float:
        """
        Score price momentum signal.
        Higher = better opportunity.
        """
        if signal.get("type") != "price_momentum":
            return 0.0
        
        price = signal.get("price", 0.5)
        
        # Extreme prices (0 or 1) are mostly resolved/certain
        # Sweet spot: 0.2-0.8 range shows active disagreement
        # Best signals: close to extremes but not quite there (0.15-0.25 or 0.75-0.85)
        
        if price < 0.01 or price > 0.99:
            return 0.0  # Resolved, no opportunity
        
        if 0.3 < price < 0.7:
            return 0.3  # 50-50 markets have less edge
        
        # Markets approaching extremes but not quite there
        if (0.15 < price < 0.25) or (0.75 < price < 0.85):
            return 0.8  # Good signals
        
        if (0.05 < price < 0.15) or (0.85 < price < 0.95):
            return 0.6  # Moderate signals
        
        return 0.4
    
    @staticmethod
    def score_settlement_signal(signal: Dict) -> float:
        """Score settlement misprice opportunity."""
        if signal.get("type") != "settlement_misprice":
            return 0.0
        
        stale_price = signal.get("stale_price", 0)
        
        # Only care if stale price is material (>2%)
        if stale_price < 0.02:
            return 0.0
        
        # Higher stale price = better opportunity
        if stale_price > 0.20:
            return 0.9
        
        if stale_price > 0.10:
            return 0.7
        
        return 0.4
    
    @staticmethod
    def score_signal(signal: Dict) -> float:
        """Score any signal (0-1, higher = better)."""
        signal_type = signal.get("type")
        
        if signal_type == "price_momentum":
            return SignalFilter.score_momentum_signal(signal)
        elif signal_type == "settlement_misprice":
            return SignalFilter.score_settlement_signal(signal)
        elif signal_type == "retail_flow_detected":
            return 0.4  # Placeholder
        else:
            return 0.0
    
    @staticmethod
    def filter_signals(signals: List[Dict], min_score: float = 0.7) -> List[Dict]:
        """Filter signals by quality score."""
        scored = []
        
        for signal in signals:
            score = SignalFilter.score_signal(signal)
            if score >= min_score:
                signal['_score'] = score
                scored.append(signal)
        
        # Sort by score descending
        return sorted(scored, key=lambda x: x['_score'], reverse=True)
    
    @staticmethod
    def deduplicate_signals(signals: List[Dict]) -> List[Dict]:
        """Remove duplicate signals for same market."""
        seen = {}
        unique = []
        
        for signal in signals:
            market_id = signal.get("market_id")
            signal_type = signal.get("type")
            key = (market_id, signal_type)
            
            if key not in seen:
                seen[key] = True
                unique.append(signal)
        
        return unique
