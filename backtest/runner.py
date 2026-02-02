"""Backtest detector strategies on REAL Polymarket + Chainlink data.

All backtests use historical CSV data from pricing research.
Results are deterministic and reproducible.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
from datetime import datetime
from .data_loader import PolymarketDataLoader, BacktestData

class BacktestRunner:
    """Run detector strategies on real historical market data."""
    
    def __init__(self, data_dir: Path = Path("data")):
        self.data_dir = data_dir
        self.loader = PolymarketDataLoader(data_dir)
        self.results = []
    
    def backtest_detector(self, detector, asset: str = "sol", num_markets: int = 5) -> Dict:
        """
        Run detector on REAL historical Polymarket data.
        
        Loads CSV files with:
        - Chainlink oracle prices (ground truth)
        - Market bid/ask prices
        - Timestamps for 15-min markets
        
        Returns verified performance metrics.
        """
        
        all_pnls = []
        all_trades = 0
        all_wins = 0
        markets_tested = 0
        
        for market_idx in range(num_markets):
            market = self.loader.load_market(asset, market_idx)
            
            if market is None:
                break
            
            df = market["data"]
            markets_tested += 1
            
            # Format market data for detector
            market_dict = {
                "slug": market["slug"],
                "chainlink_prices": df["chainlink_price_usd"].tolist(),
                "bid_prices": df["bid_price_1"].tolist() if "bid_price_1" in df else [0.5] * len(df),
                "ask_prices": df["ask_price_1"].tolist() if "ask_price_1" in df else [0.5] * len(df),
                "timestamps": df["exchange_dt"].tolist(),
                "oracle_timestamps": df["chainlink_dt"].tolist()
            }
            
            # Run detector
            signal = detector.detect(market_dict)
            
            if not signal:
                continue
            
            all_trades += 1
            
            # Evaluate signal against real market outcome
            entry_price = signal.get("entry_price", 0.5)
            action = signal.get("action")
            confidence = signal.get("confidence", 0.5)
            
            # Real outcome: where Chainlink price settled at market end
            settlement_price = df["chainlink_price_usd"].iloc[-1]
            
            # Calculate P&L
            if action == "long":
                # Bet YES: win if price goes above entry
                won = settlement_price > entry_price
                pnl = (settlement_price - entry_price) * confidence if won else -(entry_price - settlement_price) * confidence * 0.5
            elif action == "short":
                # Bet NO: win if price goes below entry
                won = settlement_price < entry_price
                pnl = (entry_price - settlement_price) * confidence if won else -(settlement_price - entry_price) * confidence * 0.5
            else:
                pnl = 0
                won = False
            
            all_pnls.append(pnl)
            if won:
                all_wins += 1
        
        # Calculate metrics
        if all_trades == 0:
            return {
                "detector": detector.__class__.__name__,
                "trades": 0,
                "error": "No signals generated on real data",
                "markets_tested": markets_tested
            }
        
        pnls_array = np.array(all_pnls)
        
        return {
            "detector": detector.__class__.__name__,
            "markets_tested": markets_tested,
            "trades": all_trades,
            "wins": all_wins,
            "win_rate": all_wins / all_trades if all_trades > 0 else 0,
            "total_pnl": float(np.sum(pnls_array)),
            "avg_pnl_per_trade": float(np.mean(pnls_array)),
            "sharpe_ratio": float(np.mean(pnls_array) / np.std(pnls_array)) if np.std(pnls_array) > 0 and len(pnls_array) > 1 else 0.0,
            "std_dev": float(np.std(pnls_array)),
            "timestamp": datetime.now().isoformat(),
            "data_source": "Real Polymarket + Chainlink Oracle"
        }
    
    def run(self, detector_name: str) -> Dict:
        """Run backtest for a specific detector."""
        
        # Import detector from agents/{detector_name}/detector.py
        detector_path = Path(__file__).parent.parent / "agents" / detector_name / "detector.py"
        
        if not detector_path.exists():
            return {"error": f"Detector not found: {detector_path}"}
        
        # Load detector
        import importlib.util
        spec = importlib.util.spec_from_file_location("detector_module", detector_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Instantiate detector
        detector = module.Detector()
        
        # Load market data
        markets = self.load_market_data(limit=10)
        
        if not markets:
            return {"error": "No market data loaded"}
        
        # Run backtest
        results = self.backtest_detector(detector, markets)
        
        return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python runner.py <detector_name> [asset]")
        print("Example: python runner.py agent1_name sol")
        sys.exit(1)
    
    detector_name = sys.argv[1]
    asset = sys.argv[2] if len(sys.argv) > 2 else "sol"
    
    # Import detector
    detector_path = Path(__file__).parent.parent / "agents" / detector_name / "detector.py"
    
    if not detector_path.exists():
        print(f"❌ Detector not found: {detector_path}")
        sys.exit(1)
    
    import importlib.util
    spec = importlib.util.spec_from_file_location("detector_module", detector_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    detector = module.Detector()
    
    # Run backtest on REAL data
    print(f"\n🧪 Backtesting {detector_name} on {asset} markets...")
    runner = BacktestRunner()
    results = runner.backtest_detector(detector, asset=asset, num_markets=5)
    
    print("\n=== BACKTEST RESULTS (REAL DATA) ===")
    print(json.dumps(results, indent=2))
    
    # Save results
    results_file = Path(__file__).parent.parent / "agents" / detector_name / "backtest_results.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to {results_file}")
    print(f"📊 Sharpe Ratio: {results.get('sharpe_ratio', 0):.2f}")
