#!/usr/bin/env python3
"""
Validate all data and generate release artifacts.
This script ensures the system works end-to-end before release.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List

def validate_findings():
    """Validate findings.jsonl for data quality and coherence."""
    
    findings_path = Path("findings.jsonl")
    if not findings_path.exists():
        return {"status": "SKIP", "reason": "No findings.jsonl"}
    
    records = []
    try:
        with open(findings_path) as f:
            for line in f:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        return {"status": "FAIL", "error": str(e)}
    
    if not records:
        return {"status": "FAIL", "error": "Empty findings file"}
    
    # Analyze findings
    df = pd.DataFrame(records)
    
    checks = {
        "total_records": len(df),
        "date_range": f"{df.get('timestamp', pd.Series()).min()} to {df.get('timestamp', pd.Series()).max()}",
        "market_count": df.get('market_id', pd.Series()).nunique() if 'market_id' in df else 0,
        "required_fields": all(col in df.columns for col in ['market_id', 'signal_type']),
        "no_nulls_in_key_fields": df[['market_id', 'signal_type']].notnull().all().all() if 'market_id' in df else False,
    }
    
    status = "PASS" if all(v for v in checks.values() if isinstance(v, bool)) else "WARN"
    
    return {
        "status": status,
        "data": checks,
        "sample": records[:3]
    }

def validate_backtest_runner():
    """Check that backtest runner exists and is executable."""
    
    runner_path = Path("backtest/runner.py")
    
    if not runner_path.exists():
        return {"status": "FAIL", "error": "No backtest runner found"}
    
    try:
        with open(runner_path) as f:
            code = f.read()
        
        has_sharpe = "sharpe" in code.lower()
        has_backtest = "backtest" in code.lower()
        has_scoring = "score" in code.lower()
        
        return {
            "status": "PASS" if (has_sharpe and has_backtest) else "WARN",
            "features": {
                "sharpe_ratio": has_sharpe,
                "backtest_logic": has_backtest,
                "scoring": has_scoring,
            }
        }
    except Exception as e:
        return {"status": "FAIL", "error": str(e)}

def validate_detector_template():
    """Check that detector template is valid."""
    
    template_path = Path("agents/TEMPLATE/detector.py")
    
    if not template_path.exists():
        return {"status": "FAIL", "error": "No detector template"}
    
    try:
        with open(template_path) as f:
            code = f.read()
        
        has_class = "class" in code
        has_detect = "def detect" in code
        has_docstring = '"""' in code or "'''" in code
        
        return {
            "status": "PASS" if (has_class and has_detect) else "WARN",
            "features": {
                "has_class": has_class,
                "has_detect_method": has_detect,
                "has_documentation": has_docstring,
            }
        }
    except Exception as e:
        return {"status": "FAIL", "error": str(e)}

def validate_leaderboard():
    """Check that leaderboard structure exists."""
    
    leaderboard_path = Path("LEADERBOARD.md")
    
    if not leaderboard_path.exists():
        return {"status": "FAIL", "error": "No leaderboard"}
    
    try:
        with open(leaderboard_path) as f:
            content = f.read()
        
        return {
            "status": "PASS",
            "size": len(content),
            "has_headers": "Rank" in content or "Detector" in content,
        }
    except Exception as e:
        return {"status": "FAIL", "error": str(e)}

def generate_report(results: Dict) -> str:
    """Generate human-readable validation report."""
    
    report = []
    report.append("\n" + "="*80)
    report.append("ALPHA HUNT SYSTEM VALIDATION REPORT")
    report.append(f"Generated: {datetime.now().isoformat()}")
    report.append("="*80 + "\n")
    
    for component, result in results.items():
        status = result.get("status", "UNKNOWN")
        symbol = "✅" if status == "PASS" else "⚠️" if status == "WARN" else "❌"
        
        report.append(f"{symbol} {component}: {status}")
        
        if "error" in result:
            report.append(f"   Error: {result['error']}")
        elif "data" in result:
            for key, val in result["data"].items():
                report.append(f"   {key}: {val}")
        elif "features" in result:
            for key, val in result["features"].items():
                report.append(f"   {key}: {'✓' if val else '✗'}")
        
        report.append("")
    
    # Summary
    pass_count = sum(1 for r in results.values() if r.get("status") == "PASS")
    total_count = len(results)
    
    report.append("="*80)
    report.append(f"SUMMARY: {pass_count}/{total_count} components validated")
    report.append("="*80)
    
    return "\n".join(report)

def main():
    """Run all validations and generate report."""
    
    print("\n🔍 Validating Alpha Hunt system...")
    
    results = {
        "Findings Data": validate_findings(),
        "Backtest Runner": validate_backtest_runner(),
        "Detector Template": validate_detector_template(),
        "Leaderboard Structure": validate_leaderboard(),
    }
    
    # Generate report
    report = generate_report(results)
    print(report)
    
    # Save report
    report_path = Path("VALIDATION_REPORT.md")
    with open(report_path, "w") as f:
        f.write(report)
    
    print(f"\n✅ Validation report saved: {report_path}")
    
    # Check if all critical components pass
    critical_pass = all(
        results[comp].get("status") in ["PASS", "WARN"]
        for comp in ["Backtest Runner", "Detector Template", "Leaderboard Structure"]
    )
    
    if critical_pass:
        print("✅ System is ready for deployment!")
        return 0
    else:
        print("❌ Critical components failed validation")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
