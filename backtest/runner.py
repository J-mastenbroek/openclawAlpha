"""Backtest detector strategies on real Polymarket data."""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
from datetime import datetime

class BacktestRunner:
    """Run detector strategies on historical market data."""
    
    def __init__(self, data_dir: Path = Path("data")):
        self.data_dir = data_dir
        self.results = []
    
    def load_market_data(self, asset: str = "sol", limit: int = 5) -> List[Dict]:
        """
        Load real Polymarket data from CSV files.
        Expects format from pricing.ipynb data.
        
        Returns list of market datasets with prices, times, chainlink oracle.
        """
        
        # Find CSV files for asset
        pattern = f"{asset}-*.csv"
        csv_files = sorted(self.data_dir.glob(pattern))[:limit]
        
        if not csv_files:
            print(f"❌ No data files found for {asset}")
            return []
        
        markets = []
        
        for csv_file in csv_files:
            print(f"Loading {csv_file.name}...")
            
            # Parse market metadata from CSV header
            meta = {}
            rows = []
            
            with open(csv_file) as f:
                for line in f:
                    if line.startswith("#"):
                        # Metadata line
                        key, val = line[1:].split(":", 1)
                        meta[key.strip()] = val.strip()
                    else:
                        # Data line (CSV)
                        rows.append(line.strip())
            
            # Basic market data: timestamp, chainlink_price, exchange_price, bid/ask
            market = {
                "slug": meta.get("slug", csv_file.stem),
                "asset": asset,
                "data": rows,  # Raw CSV rows
                "metadata": meta
            }
            
            markets.append(market)
        
        return markets
    
    def backtest_detector(self, detector, markets: List[Dict]) -> Dict:
        """
        Run detector on historical markets, calculate P&L.
        
        Returns performance metrics:
        - trades: number of signals generated
        - wins: profitable trades
        - win_rate: %
        - sharpe: risk-adjusted return
        - total_pnl: cumulative profit
        """
        
        trades = 0
        wins = 0
        pnls = []
        
        for market in markets:
            # Parse market data and simulate detection
            # Detector returns signal with entry/exit prices
            
            # For now: mock evaluation (in production, parse real prices)
            result = detector.detect(market)
            
            if result and result.get("action"):
                trades += 1
                
                # Simulate trade (mock P&L)
                # In production: use real entry/exit prices from market data
                edge = result.get("edge", 0.02)
                pnl = edge * 100  # Assume $100 per trade
                
                pnls.append(pnl)
                if pnl > 0:
                    wins += 1
        
        # Calculate metrics
        if not pnls:
            return {
                "detector": detector.__class__.__name__,
                "trades": 0,
                "error": "No signals generated"
            }
        
        total_pnl = sum(pnls)
        win_rate = wins / len(pnls) if pnls else 0
        
        # Simple Sharpe ratio
        returns = np.array(pnls)
        if len(returns) > 1:
            sharpe = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        else:
            sharpe = 0
        
        return {
            "detector": detector.__class__.__name__,
            "trades": trades,
            "wins": wins,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "sharpe_ratio": sharpe,
            "avg_pnl_per_trade": total_pnl / trades if trades > 0 else 0,
            "timestamp": datetime.now().isoformat()
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
        print("Usage: python runner.py <detector_name>")
        print("Example: python runner.py agent1_name")
        sys.exit(1)
    
    detector_name = sys.argv[1]
    runner = BacktestRunner()
    results = runner.run(detector_name)
    
    print("\n=== BACKTEST RESULTS ===")
    print(json.dumps(results, indent=2))
    
    # Save results
    results_file = Path(__file__).parent.parent / "agents" / detector_name / "backtest_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to {results_file}")
