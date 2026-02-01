"""Main orchestrator for autonomous monitoring."""

import json
import time
from datetime import datetime
from src.polymarket import PolymarketClient
from src.analysis import MarketAnalyzer

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
        report = {
            "timestamp": datetime.now().isoformat(),
            "finding_count": len(findings),
            "findings": findings,
            "total_queries": self.query_count
        }
        
        # Save to file
        with open("findings.jsonl", "a") as f:
            f.write(json.dumps(report) + "\n")
        
        # Print summary
        print(f"\n📊 FINDINGS ({len(findings)} signals):")
        for f in findings:
            print(f"  - {f['type']}: {f.get('market_id')}")

if __name__ == "__main__":
    monitor = AlphaMonitor()
    monitor.run_scan()
