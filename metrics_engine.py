#!/usr/bin/env python3
"""
Real-time metrics engine for Alpha Hunt leaderboard.
Companion system that demonstrates system reliability and data integrity.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from collections import defaultdict

class MetricsEngine:
    """Generate real-time metrics for leaderboard and system health."""
    
    def __init__(self, findings_path: str = "findings.jsonl"):
        self.findings_path = Path(findings_path)
        self.records = self._load_findings()
    
    def _load_findings(self) -> List[Dict]:
        """Load and parse findings data."""
        records = []
        
        if not self.findings_path.exists():
            return records
        
        try:
            with open(self.findings_path) as f:
                for line in f:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"⚠️ Error loading findings: {e}")
        
        return records
    
    def compute_detection_stats(self) -> Dict:
        """Compute statistics on detection patterns."""
        
        if not self.records:
            return {
                "total_detections": 0,
                "unique_markets": 0,
                "unique_signals": 0,
                "signal_types": {},
            }
        
        df = pd.DataFrame(self.records)
        
        signal_types = defaultdict(int)
        for record in self.records:
            if "signal_type" in record:
                signal_types[record["signal_type"]] += 1
        
        return {
            "total_detections": len(self.records),
            "unique_markets": df.get("market_id", pd.Series()).nunique() if "market_id" in df else 0,
            "unique_signals": len(signal_types),
            "signal_types": dict(signal_types),
            "first_detection": df.get("timestamp", pd.Series()).min() if "timestamp" in df else None,
            "last_detection": df.get("timestamp", pd.Series()).max() if "timestamp" in df else None,
        }
    
    def compute_signal_quality(self) -> Dict:
        """Assess quality of detected signals."""
        
        if not self.records:
            return {
                "high_confidence": 0,
                "medium_confidence": 0,
                "low_confidence": 0,
                "avg_quality_score": 0,
                "signal_distribution": {},
            }
        
        quality_bins = {"high": 0, "medium": 0, "low": 0}
        scores = []
        distribution = defaultdict(int)
        
        for record in self.records:
            # Extract quality score if available
            score = record.get("quality_score", 0.5)
            scores.append(score)
            
            if score > 0.7:
                quality_bins["high"] += 1
            elif score > 0.4:
                quality_bins["medium"] += 1
            else:
                quality_bins["low"] += 1
            
            signal_type = record.get("signal_type", "unknown")
            distribution[signal_type] += 1
        
        return {
            "high_confidence": quality_bins["high"],
            "medium_confidence": quality_bins["medium"],
            "low_confidence": quality_bins["low"],
            "avg_quality_score": np.mean(scores) if scores else 0,
            "signal_distribution": dict(distribution),
            "quality_distribution": {
                "high": f"{100*quality_bins['high']/len(self.records) if self.records else 0:.1f}%",
                "medium": f"{100*quality_bins['medium']/len(self.records) if self.records else 0:.1f}%",
                "low": f"{100*quality_bins['low']/len(self.records) if self.records else 0:.1f}%",
            }
        }
    
    def compute_market_coverage(self) -> Dict:
        """Assess which markets are being monitored."""
        
        if not self.records:
            return {"monitored_markets": 0, "coverage_percent": 0}
        
        df = pd.DataFrame(self.records)
        unique_markets = df.get("market_id", pd.Series()).nunique() if "market_id" in df else 0
        
        # Estimate Polymarket has 100+ active markets
        total_markets_estimate = 100
        coverage = min(100, (unique_markets / total_markets_estimate) * 100)
        
        return {
            "monitored_markets": unique_markets,
            "coverage_percent": f"{coverage:.1f}%",
            "estimated_total_markets": total_markets_estimate,
        }
    
    def compute_system_health(self) -> Dict:
        """Overall system health check."""
        
        checks = {
            "has_findings_data": len(self.records) > 0,
            "detector_template_exists": Path("agents/TEMPLATE/detector.py").exists(),
            "backtest_runner_exists": Path("backtest/runner.py").exists(),
            "leaderboard_exists": Path("LEADERBOARD.md").exists(),
            "validation_report_exists": Path("VALIDATION_REPORT.md").exists(),
        }
        
        passed = sum(1 for v in checks.values() if v)
        total = len(checks)
        
        return {
            "system_health": {
                "passed_checks": passed,
                "total_checks": total,
                "health_percent": f"{100*passed/total:.0f}%",
            },
            "component_status": checks,
        }
    
    def generate_dashboard(self) -> str:
        """Generate markdown dashboard of system metrics."""
        
        detection_stats = self.compute_detection_stats()
        signal_quality = self.compute_signal_quality()
        market_coverage = self.compute_market_coverage()
        system_health = self.compute_system_health()
        
        dashboard = []
        dashboard.append("\n" + "="*80)
        dashboard.append("ALPHA HUNT SYSTEM METRICS DASHBOARD")
        dashboard.append(f"Generated: {datetime.now().isoformat()}")
        dashboard.append("="*80 + "\n")
        
        # Detection Stats
        dashboard.append("## Detection Statistics")
        dashboard.append(f"- **Total Detections:** {detection_stats['total_detections']}")
        dashboard.append(f"- **Unique Markets:** {detection_stats['unique_markets']}")
        dashboard.append(f"- **Signal Types:** {detection_stats['unique_signals']}")
        if detection_stats['signal_types']:
            for sig_type, count in detection_stats['signal_types'].items():
                dashboard.append(f"  - {sig_type}: {count}")
        dashboard.append(f"- **Detection Window:** {detection_stats['first_detection']} to {detection_stats['last_detection']}")
        dashboard.append("")
        
        # Signal Quality
        dashboard.append("## Signal Quality")
        dashboard.append(f"- **Average Quality Score:** {signal_quality['avg_quality_score']:.2f}/1.0")
        dashboard.append(f"- **High Confidence Signals:** {signal_quality['high_confidence']} ({signal_quality['quality_distribution']['high']})")
        dashboard.append(f"- **Medium Confidence Signals:** {signal_quality['medium_confidence']} ({signal_quality['quality_distribution']['medium']})")
        dashboard.append(f"- **Low Confidence Signals:** {signal_quality['low_confidence']} ({signal_quality['quality_distribution']['low']})")
        dashboard.append("")
        
        # Market Coverage
        dashboard.append("## Market Coverage")
        dashboard.append(f"- **Monitored Markets:** {market_coverage['monitored_markets']}/{market_coverage['estimated_total_markets']}")
        dashboard.append(f"- **Coverage:** {market_coverage['coverage_percent']}")
        dashboard.append("")
        
        # System Health
        health = system_health['system_health']
        dashboard.append("## System Health")
        dashboard.append(f"- **Overall Health:** {health['health_percent']}")
        dashboard.append(f"- **Components Verified:** {health['passed_checks']}/{health['total_checks']}")
        dashboard.append("- **Component Status:**")
        for component, status in system_health['component_status'].items():
            symbol = "✅" if status else "❌"
            dashboard.append(f"  - {symbol} {component}")
        dashboard.append("")
        
        dashboard.append("="*80)
        dashboard.append("END OF REPORT")
        dashboard.append("="*80 + "\n")
        
        return "\n".join(dashboard)
    
    def save_dashboard(self, output_path: str = "METRICS.md"):
        """Save dashboard to file."""
        dashboard = self.generate_dashboard()
        
        with open(output_path, "w") as f:
            f.write(dashboard)
        
        print(f"✅ Metrics dashboard saved: {output_path}")
        return dashboard

def main():
    """Generate and display metrics."""
    engine = MetricsEngine()
    dashboard = engine.save_dashboard("METRICS.md")
    print(dashboard)

if __name__ == "__main__":
    main()
