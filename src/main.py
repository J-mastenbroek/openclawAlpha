"""Main orchestrator for autonomous monitoring."""

import json
import time
from datetime import datetime
from src.polymarket import PolymarketClient
from src.analysis import MarketAnalyzer
from src.filter import SignalFilter

class AlphaMonitor:
    def __init__(self):
        self.client = PolymarketClient()
        self.analyzer = MarketAnalyzer()
        self.query_count = 0
        self.findings_log = []
    
    def run_scan(self):
        """Single scan cycle."""
        print(f"\n[{datetime.now().isoformat()}] Starting scan...")
        self.query_count += 1
        
        # Fetch active markets
        markets = self.client.get_markets(limit=100)
        if not markets:
            print("No markets fetched.")
            return
        
        print(f"Fetched {len(markets)} markets")
        
        findings = []
        for market in markets:
            # Analyze market data directly (prices, status, etc)
            # Don't need to fetch trades separately if prices are in market data
            market_findings = self.analyzer.analyze_market(market, [])
            if market_findings:
                findings.extend(market_findings)
                condition_id = market.get("condition_id", "unknown")
                print(f"  → {condition_id[:16]}...: {len(market_findings)} findings")
        
        if findings:
            self.findings_log.extend(findings)
            self.report_findings(findings)
        else:
            print("  No alpha signals detected.")
    
    def report_findings(self, findings: list):
        """Generate report of findings."""
        # Filter for quality signals
        high_quality = SignalFilter.filter_signals(findings, min_score=0.7)
        deduplicated = SignalFilter.deduplicate_signals(high_quality)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_signals": len(findings),
            "high_quality": len(deduplicated),
            "signals": deduplicated[:10],  # Top 10 only
            "total_queries": self.query_count
        }
        
        # Save to file
        with open("findings.jsonl", "a") as f:
            f.write(json.dumps(report) + "\n")
        
        # Print summary
        print(f"\n📊 FINDINGS Summary:")
        print(f"  Total signals: {len(findings)}")
        print(f"  High quality (score>0.7): {len(deduplicated)}")
        
        if deduplicated:
            print(f"\n🎯 Top signals:")
            for sig in deduplicated[:5]:
                score = sig.get("_score", 0)
                sig_type = sig.get("type")
                outcome = sig.get("outcome", "N/A")
                price = sig.get("price", "N/A")
                print(f"  [{score:.2f}] {sig_type}: {outcome} @ {price}")

if __name__ == "__main__":
    monitor = AlphaMonitor()
    monitor.run_scan()
