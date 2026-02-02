"""Fair value pricing model for prediction markets.

Based on lognormal pricing with Chainlink oracle ground truth.
For 15-min crypto up/down markets.
"""

import math
from typing import Dict, Optional
from scipy.stats import norm

class PricingModel:
    """
    Fair value pricing for YES/NO prediction markets.
    
    Market resolves YES if oracle price at T > strike K
    Fair value = NormalCDF(z-score)
    """
    
    @staticmethod
    def compute_fair_value(
        current_price: float,
        strike_price: float,
        volatility_1m: float,
        minutes_remaining: float
    ) -> Dict:
        """
        Compute fair value probability for YES outcome.
        
        Args:
            current_price: Current oracle price (S_t)
            strike_price: Strike price for market (K)
            volatility_1m: 1-minute volatility (annualized or per-minute?)
            minutes_remaining: Time to expiry
        
        Returns:
            {
                'fair_value_yes': float (0-1),
                'fair_value_no': float (0-1),
                'z_score': float,
                'distance': float (log scale),
                'sigma_remaining': float
            }
        """
        
        # Safety checks
        if current_price <= 0 or strike_price <= 0:
            return {"error": "Invalid prices"}
        
        if minutes_remaining <= 0:
            # Market expired
            if current_price > strike_price:
                return {"fair_value_yes": 1.0, "fair_value_no": 0.0}
            else:
                return {"fair_value_yes": 0.0, "fair_value_no": 1.0}
        
        # Distance in log returns
        distance = math.log(current_price / strike_price)
        
        # Sigma scaled by square root of time
        sigma_remaining = volatility_1m * math.sqrt(minutes_remaining)
        
        if sigma_remaining == 0:
            sigma_remaining = 0.001  # Prevent division by zero
        
        # Z-score: how many sigma moves away from strike
        z_score = distance / sigma_remaining
        
        # Fair value from normal CDF
        fair_value_yes = norm.cdf(z_score)
        fair_value_no = 1.0 - fair_value_yes
        
        return {
            "fair_value_yes": fair_value_yes,
            "fair_value_no": fair_value_no,
            "z_score": z_score,
            "distance": distance,
            "sigma_remaining": sigma_remaining
        }
    
    @staticmethod
    def find_misprice(
        market_price_yes: float,
        fair_value_yes: float,
        min_edge: float = 0.05
    ) -> Optional[Dict]:
        """
        Identify misprice opportunity.
        
        Edge exists if |market - fair| > min_edge
        """
        
        if market_price_yes < 0 or market_price_yes > 1:
            return None
        
        edge = abs(market_price_yes - fair_value_yes)
        
        if edge < min_edge:
            return None  # No edge
        
        if market_price_yes > fair_value_yes:
            # Market overpricing YES
            return {
                "type": "overpriced_yes",
                "market_price": market_price_yes,
                "fair_value": fair_value_yes,
                "edge": edge,
                "action": "short_yes (buy_no)"
            }
        else:
            # Market underpricing YES
            return {
                "type": "underpriced_yes",
                "market_price": market_price_yes,
                "fair_value": fair_value_yes,
                "edge": edge,
                "action": "long_yes"
            }
    
    @staticmethod
    def estimate_vol_from_prices(price_history: list) -> float:
        """
        Estimate 1-minute volatility from price history.
        
        Returns std dev of 1-minute log returns.
        """
        
        if len(price_history) < 2:
            return 0.01  # Default small vol
        
        # Calculate 1-minute log returns
        returns = []
        for i in range(1, len(price_history)):
            if price_history[i] > 0 and price_history[i-1] > 0:
                ret = math.log(price_history[i] / price_history[i-1])
                returns.append(ret)
        
        if not returns:
            return 0.01
        
        # Standard deviation of returns
        mean_ret = sum(returns) / len(returns)
        variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
        vol = math.sqrt(variance)
        
        return vol
