"""Data validation and quality checks for collected orderbook data."""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np


class OrderbookDataValidator:
    """Validate collected CSV data for quality and consistency."""
    
    @staticmethod
    def validate_csv(filepath: Path) -> Dict:
        """Validate a single market CSV file."""
        
        try:
            df = pd.read_csv(filepath)
        except Exception as e:
            return {"status": "FAIL", "error": f"Cannot read CSV: {e}"}
        
        results = {
            "file": filepath.name,
            "rows": len(df),
            "checks": {}
        }
        
        # Check 1: Required columns
        required_cols = ["timestamp_ms", "bid_price_1", "ask_price_1", "spread", "mid_price"]
        missing_cols = [c for c in required_cols if c not in df.columns]
        results["checks"]["columns"] = "PASS" if not missing_cols else f"FAIL: missing {missing_cols}"
        
        if missing_cols:
            return results
        
        # Check 2: Data types
        df["timestamp_ms"] = pd.to_numeric(df["timestamp_ms"], errors="coerce")
        df["bid_price_1"] = pd.to_numeric(df["bid_price_1"], errors="coerce")
        df["ask_price_1"] = pd.to_numeric(df["ask_price_1"], errors="coerce")
        
        nulls = df[required_cols].isnull().sum().sum()
        results["checks"]["nulls"] = f"PASS ({nulls} nulls)" if nulls < len(df) * 0.01 else f"FAIL ({nulls} nulls)"
        
        # Check 3: Price ranges
        bid_valid = ((df["bid_price_1"] > 0) & (df["bid_price_1"] < 1)).sum()
        ask_valid = ((df["ask_price_1"] > 0) & (df["ask_price_1"] < 1)).sum()
        
        results["checks"]["price_range"] = "PASS" if (bid_valid > len(df) * 0.9 and ask_valid > len(df) * 0.9) else "FAIL"
        
        # Check 4: Bid/ask ordering
        crossed = (df["bid_price_1"] > df["ask_price_1"]).sum()
        results["checks"]["bid_ask_spread"] = f"PASS ({crossed} crossed)" if crossed < len(df) * 0.05 else f"FAIL ({crossed} crossed)"
        
        # Check 5: Timestamp monotonicity
        df_sorted = df.sort_values("timestamp_ms")
        dup_times = (df_sorted["timestamp_ms"].diff() <= 0).sum()
        results["checks"]["timestamp_order"] = f"PASS ({dup_times} duplicates)" if dup_times < len(df) * 0.1 else f"FAIL"
        
        # Check 6: Spread sanity
        avg_spread = df["spread"].mean()
        results["checks"]["spread_sanity"] = f"PASS (avg: {avg_spread:.4f})" if (avg_spread > 0.001 and avg_spread < 0.5) else f"WARN (avg: {avg_spread:.4f})"
        
        # Check 7: Mid price consistency
        mid_calculated = (df["bid_price_1"] + df["ask_price_1"]) / 2
        mid_diff = abs(df["mid_price"] - mid_calculated).mean()
        results["checks"]["mid_price_accuracy"] = f"PASS (diff: {mid_diff:.6f})" if mid_diff < 0.01 else f"WARN (diff: {mid_diff:.6f})"
        
        # Summary
        fails = sum(1 for v in results["checks"].values() if "FAIL" in str(v))
        results["status"] = "PASS" if fails == 0 else f"FAIL ({fails} checks)"
        
        return results
    
    @staticmethod
    def validate_directory(data_dir: Path) -> List[Dict]:
        """Validate all CSV files in directory."""
        
        csv_files = list(data_dir.glob("*.csv"))
        results = []
        
        for csv_file in csv_files:
            result = OrderbookDataValidator.validate_csv(csv_file)
            results.append(result)
        
        return results
    
    @staticmethod
    def print_report(results: List[Dict]):
        """Print validation report."""
        
        print("\n" + "="*80)
        print("ORDERBOOK DATA VALIDATION REPORT")
        print("="*80 + "\n")
        
        passes = 0
        fails = 0
        
        for result in results:
            status = result.get("status", "UNKNOWN")
            file = result.get("file", "unknown")
            rows = result.get("rows", 0)
            
            symbol = "✅" if "PASS" in status else "❌"
            print(f"{symbol} {file} ({rows} rows) - {status}")
            
            for check, result_text in result.get("checks", {}).items():
                print(f"    {check}: {result_text}")
            
            print()
            
            if "PASS" in status:
                passes += 1
            else:
                fails += 1
        
        print("="*80)
        print(f"Summary: {passes} PASS, {fails} FAIL out of {len(results)} files")
        print("="*80)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        data_dir = Path(sys.argv[1])
    else:
        data_dir = Path("data/live")
    
    if not data_dir.exists():
        print(f"Data directory not found: {data_dir}")
        sys.exit(1)
    
    results = OrderbookDataValidator.validate_directory(data_dir)
    OrderbookDataValidator.print_report(results)
