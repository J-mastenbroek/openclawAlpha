"""Template detector for Alpha Hunt tournament.

Copy this to agents/{your_name}/detector.py and implement your strategy.
"""

from typing import Dict, Optional


class Detector:
    """Your detection strategy for Polymarket arbitrage."""
    
    def detect(self, market: Dict) -> Optional[Dict]:
        """
        Analyze a market and return a signal if you find alpha.
        
        Args:
            market: Market data with prices, times, oracle data
        
        Returns:
            {
                "action": "long" or "short" or None,
                "edge": float (0-1, your confidence in edge size),
                "entry_price": float,
                "exit_price": float or target,
                "confidence": float (0-1)
            }
            
            Or None if no signal.
        """
        
        # Your implementation here
        
        # Example: detect settlement misprice
        tokens = market.get("tokens", [])
        if len(tokens) < 2:
            return None
        
        yes_price = float(tokens[0].get("price", 0.5))
        
        # If YES is extremely mispriced (0.95+ but market just closed)
        if market.get("closed") and 0.85 < yes_price < 0.95:
            return {
                "action": "short",  # Market is overpricing
                "edge": 0.10,
                "entry_price": yes_price,
                "exit_price": 0.70,  # Expect reversion to 70%
                "confidence": 0.75
            }
        
        return None
