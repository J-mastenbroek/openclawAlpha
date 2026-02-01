"""Main orchestrator for autonomous monitoring."""

import json
import time
from datetime import datetime
from src.polymarket import PolymarketClient
from src.analysis import MarketAnalyzer
from src.filter import SignalFilter
from src.trader import PaperTrader

class AlphaMonitor:
    def __init__(self):
        self.client = PolymarketClient()
        self.analyzer = MarketAnalyzer()
        self.trader = PaperTrader(initial_capital=25.0)  # Start with available budget
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
        
        # Paper trade on top signals
        for sig in deduplicated[:3]:  # Only trade top 3 to preserve capital
            if self.trader.capital > 5.0:  # Only if we have capital
                result = self.trader.execute_signal(sig, size=5.0)
                if result["status"] == "accepted":
                    print(f"  📍 Opened position {result['position_id']}: {sig.get('outcome')}")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_signals": len(findings),
            "high_quality": len(deduplicated),
            "signals": deduplicated[:10],
            "total_queries": self.query_count,
            "trading": {
                "capital": self.trader.capital,
                "positions": len(self.trader.positions),
                "stats": self.trader.get_stats()
            }
        }
        
        # Save to file
        with open("findings.jsonl", "a") as f:
            f.write(json.dumps(report) + "\n")
        
        # Print summary
        print(f"\n📊 FINDINGS Summary:")
        print(f"  Total signals: {len(findings)}")
        print(f"  High quality (score>0.7): {len(deduplicated)}")
        print(f"  Capital: ${self.trader.capital:.2f}")
        
        if deduplicated:
            print(f"\n🎯 Top signals:")
            for sig in deduplicated[:5]:
                score = sig.get("_score", 0)
                sig_type = sig.get("type")
                outcome = sig.get("outcome", "N/A")
                price = sig.get("price", "N/A")
                print(f"  [{score:.2f}] {sig_type}: {outcome} @ {price}")
        
        # Print trading stats
        stats = self.trader.get_stats()
        if stats["total_trades"] > 0:
            print(f"\n📈 Trading Stats:")
            print(f"  Trades: {stats['total_trades']} ({stats['wins']} wins, {stats['losses']} losses)")
            print(f"  Win rate: {stats['win_rate']*100:.1f}%")
            print(f"  Total PnL: ${stats['total_pnl']:.2f}")
            print(f"  Capital: ${stats['capital']:.2f}")

if __name__ == "__main__":
    monitor = AlphaMonitor()
    monitor.run_scan()
