"""Template detector for Alpha Hunt tournament.

Copy this to agents/{your_name}/detector.py and implement your strategy.

Your detector will be tested against REAL Polymarket historical data:
- Chainlink oracle prices (ground truth)
- Market bid/ask prices
- 15-minute prediction markets

Backtests are reproducible and verifiable.
"""

from typing import Dict, Optional
import numpy as np
from scipy.stats import norm


class Detector:
    """Your detection strategy for Polymarket arbitrage."""
    
    def detect(self, market: Dict) -> Optional[Dict]:
        """
        Analyze a market and return a signal if you find alpha.
        
        Args:
            market: Real market data with:
                - slug: market identifier
                - chainlink_prices: list of oracle prices (ground truth)
                - bid_prices, ask_prices: market prices
                - timestamps: when prices occurred
        
        Returns:
            {
                "action": "long" or "short" (or None if no signal),
                "edge": float (your estimated edge, 0-1),
                "entry_price": float (market price you'd enter at),
                "confidence": float (0-1, how confident you are)
            }
            
            Or None if no alpha detected.
        """
        
        # Extract data
        prices = market.get("chainlink_prices", [])
        bids = market.get("bid_prices", [0.5])
        asks = market.get("ask_prices", [0.5])
        
        if len(prices) < 10:
            return None  # Not enough data
        
        # Example: Settlement misprice detection
        # =========================================
        # If market just opened, bid/ask might not reflect true probability
        
        # Current oracle price
        current_oracle = prices[-1]
        opening_oracle = prices[0]
        
        # Current market prices
        current_bid = float(bids[-1]) if bids[-1] > 0 else 0.5
        current_ask = float(asks[-1]) if asks[-1] > 0 else 0.5
        
        # If market is overpricing YES
        # (bid is too high relative to oracle movement)
        if current_bid > 0.75 and current_oracle < opening_oracle * 1.02:
            # Oracle hasn't moved much, but market priced in big move
            # Opportunity: short YES (buy NO)
            return {
                "action": "short",
                "edge": 0.12,  # 12% edge estimate
                "entry_price": current_bid,
                "confidence": 0.68
            }
        
        # If market is underpricing YES
        # (ask is too low relative to oracle movement)
        if current_ask < 0.25 and current_oracle > opening_oracle * 1.05:
            # Oracle moved up, but market hasn't caught up
            # Opportunity: long YES
            return {
                "action": "long",
                "edge": 0.15,
                "entry_price": current_ask,
                "confidence": 0.72
            }
        
        return None
