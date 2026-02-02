"""Load real Polymarket + Chainlink price data for backtesting.

Uses historical CSV data from pricing research.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
import json


class PolymarketDataLoader:
    """Load real market data with Chainlink oracle ground truth."""
    
    def __init__(self, data_dir: Path = Path("data")):
        self.data_dir = data_dir
    
    def load_market(self, asset: str, market_num: int = 0) -> Optional[Dict]:
        """
        Load real market data from CSV.
        
        CSV format (from pricing.ipynb):
        - exchange_timestamp_ms: when order happened
        - chainlink_timestamp_ms: oracle update time
        - chainlink_price_usd: Chainlink oracle price (ground truth)
        - bid_price_1, ask_price_1: market prices
        - slug: market identifier
        """
        
        # Find CSV files for asset
        csv_files = sorted(self.data_dir.glob(f"{asset}-*.csv"))
        
        if market_num >= len(csv_files):
            return None
        
        filepath = csv_files[market_num]
        
        try:
            # Parse metadata from header
            meta = {}
            with open(filepath) as f:
                for line in f:
                    if line.startswith("#"):
                        parts = line[1:].strip().split(":", 1)
                        if len(parts) == 2:
                            key, val = parts
                            meta[key.strip()] = val.strip()
                    else:
                        break
            
            # Load CSV
            df = pd.read_csv(filepath, comment="#")
            
            # Convert timestamps
            df["exchange_dt"] = pd.to_datetime(
                df["exchange_timestamp_ms"], 
                unit="ms", 
                utc=True,
                errors="coerce"
            )
            df["chainlink_dt"] = pd.to_datetime(
                df["chainlink_timestamp_ms"],
                unit="ms",
                utc=True,
                errors="coerce"
            )
            
            # Keep only rows with oracle data
            df = df.dropna(subset=["chainlink_price_usd", "exchange_dt"])
            
            if len(df) == 0:
                return None
            
            return {
                "slug": meta.get("slug", filepath.stem),
                "asset": asset,
                "data": df,
                "metadata": meta
            }
        
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
            return None
    
    def get_strike_price(self, df: pd.DataFrame) -> float:
        """
        Extract strike price (opening price at market start).
        
        From pricing.ipynb: K = first chainlink price
        """
        
        first_price = df["chainlink_price_usd"].iloc[0]
        return float(first_price)
    
    def get_market_prices(self, df: pd.DataFrame) -> tuple:
        """
        Get market YES/NO prices for a market.
        
        Returns: (bid_yes, ask_yes) from market
        """
        
        bid = df["bid_price_1"].dropna()
        ask = df["ask_price_1"].dropna()
        
        if len(bid) == 0 or len(ask) == 0:
            return None, None
        
        # Return last known prices
        return float(bid.iloc[-1]), float(ask.iloc[-1])
    
    def calculate_fair_value(self, df: pd.DataFrame) -> float:
        """
        Calculate fair value using chainlink prices + 1m volatility.
        
        From pricing.ipynb:
        - sigma_1m = rolling 120-min std of log returns
        - minutes_left = time to expiry
        - z = log(current / strike) / (sigma_remaining)
        - fair_yes = NormalCDF(z)
        """
        
        from scipy.stats import norm
        import numpy as np
        
        # Get strike (opening price)
        K = self.get_strike_price(df)
        
        # Get current price (last known)
        current_price = df["chainlink_price_usd"].iloc[-1]
        
        # Calculate 1-min volatility from log returns
        prices = df["chainlink_price_usd"].dropna()
        log_returns = np.log(prices / prices.shift(1)).dropna()
        
        if len(log_returns) < 2:
            return 0.5  # Default to 50/50
        
        sigma_1m = log_returns.std()
        
        # Assume 15-min market, calculate time remaining
        # For backtest: assume we're at entry point
        minutes_left = 7.5  # Mid-market
        
        sigma_remaining = sigma_1m * np.sqrt(minutes_left)
        
        if sigma_remaining == 0:
            sigma_remaining = 0.001
        
        # Z-score
        distance = np.log(current_price / K)
        z = distance / sigma_remaining
        
        # Fair value
        fair_yes = norm.cdf(z)
        
        return fair_yes
    
    def simulate_trade(self, entry_price: float, exit_price: float) -> float:
        """Calculate P&L from entry to exit."""
        
        if entry_price <= 0 or exit_price < 0:
            return 0
        
        # If YES, profit when price goes up
        # If NO, profit when price goes down
        
        pnl = (exit_price - entry_price) / max(entry_price, 0.01)
        
        return pnl


class BacktestData:
    """Standardized format for agents' backtests."""
    
    @staticmethod
    def from_signals(
        market_slug: str,
        signals: List[Dict],
        real_outcomes: List[float]
    ) -> Dict:
        """
        Generate reproducible backtest results.
        
        signals: List of detector outputs (entry_price, action, confidence)
        real_outcomes: Actual settlement prices (from Chainlink)
        """
        
        trades = 0
        wins = 0
        pnls = []
        
        for signal, real_price in zip(signals, real_outcomes):
            if signal is None:
                continue
            
            trades += 1
            action = signal.get("action")
            entry = signal.get("entry_price", 0.5)
            confidence = signal.get("confidence", 0.5)
            
            # Determine if trade won
            if action == "long":
                won = real_price > entry
                pnl = (real_price - entry) * confidence if won else -(entry - real_price) * confidence
            elif action == "short":
                won = real_price < entry
                pnl = (entry - real_price) * confidence if won else -(real_price - entry) * confidence
            else:
                continue
            
            if won:
                wins += 1
            
            pnls.append(pnl)
        
        # Calculate metrics
        import numpy as np
        if not pnls:
            return {"trades": 0, "error": "No signals"}
        
        pnls_array = np.array(pnls)
        
        return {
            "market": market_slug,
            "trades": trades,
            "wins": wins,
            "win_rate": wins / trades if trades > 0 else 0,
            "total_pnl": float(np.sum(pnls_array)),
            "avg_pnl_per_trade": float(np.mean(pnls_array)),
            "sharpe_ratio": float(np.mean(pnls_array) / np.std(pnls_array)) if np.std(pnls_array) > 0 else 0,
            "std_dev": float(np.std(pnls_array))
        }
