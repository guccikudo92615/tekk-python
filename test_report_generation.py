#!/usr/bin/env python3
"""
Quick test of report and ticket generation using existing security analysis results.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from tools.report_writer import ReportWriter
from tools.ticket_writer import TicketWriter


def test_report_and_ticket_generation():
    """Test report and ticket generation with sample data."""
    
    print("🧪 Testing Report and Ticket Generation")
    print("=" * 50)
    
    # Use the existing security analysis results from the previous run
    existing_report_path = "reports/complete-workflow-test/security-analysis-report.json"
    
    if Path(existing_report_path).exists():
        print(f"📁 Using existing security analysis: {existing_report_path}")
        with open(existing_report_path, 'r') as f:
            security_results = json.load(f)
    else:
        print("📝 Creating sample security data for testing...")
        # Create sample data if no existing results
        security_results = {
            "summary": {
                "risk_overview": "Sample security analysis of test repository",
                "findings_total_count": 5,
                "severity_breakdown": {"Critical": 1, "High": 2, "Medium": 1, "Low": 1}
            },
            "findings": [
                {
                    "title": "Missing Security Headers",
                    "severity": "High",
                    "category": "configuration",
                    "file": "index.html",
                    "line": 1,
                    "evidence": "No Content-Security-Policy header found",
                    "description": "Missing security headers in HTML",
                    "impact": "Potential XSS attacks",
                    "recommendation": "Add CSP headers"
                },
                {
                    "title": "Hardcoded API Key",
                    "severity": "Critical",
                    "category": "secrets_management",
                    "file": "src/config.ts",
                    "line": 15,
                    "evidence": "const API_KEY = 'sk-1234567890'",
                    "description": "API key hardcoded in source code",
                    "impact": "API key exposure",
                    "recommendation": "Use environment variables"
                },
                {
                    "title": "No Input Validation",
                    "severity": "Medium",
                    "category": "input_validation",
                    "file": "src/api.ts",
                    "line": 42,
                    "evidence": "No validation on user input",
                    "description": "Missing input validation",
                    "impact": "Potential injection attacks",
                    "recommendation": "Add input validation"
                }
            ],
            "analysis_metadata": {
                "total_agents": 3,
                "total_files": 50,
                "context_management": "enabled"
            }
        }
    
    print(f"📊 Found {len(security_results.get('findings', []))} security findings")
    print()
    
    # Test Report Generation
    print("📝 Testing Report Generation")
    print("-" * 30)
    report_writer = ReportWriter()
    
    # Prepare report data
    report_data = {
        "repository": "test-repo",
        "findings": security_results.get('findings', []),
        "metadata": security_results.get('analysis_metadata', {}),
        "summary": security_results.get('summary', {}),
        "timestamp": datetime.now().isoformat()
    }
    
    # Generate report
    report_file = Path("reports/test-report-generation") / "comprehensive_security_report.json"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_writer.write_to_file(report_data, str(report_file))
    print(f"✅ Report generated: {report_file}")
    print()
    
    # Test Ticket Generation
    print("🎫 Testing Ticket Generation")
    print("-" * 30)
    ticket_writer = TicketWriter()
    
    # Generate tickets from findings
    tickets = ticket_writer.convert_findings_to_tickets(security_results)
    tickets_file = Path("reports/test-report-generation") / "security_tickets.json"
    ticket_writer.write_tickets_to_file(tickets, str(tickets_file))
    print(f"✅ Tickets generated: {tickets_file}")
    print()
    
    # Show summary
    print("📊 SUMMARY")
    print("=" * 20)
    print(f"🔍 Security Findings: {len(security_results.get('findings', []))}")
    print(f"📝 Report: {report_file}")
    print(f"🎫 Tickets: {tickets_file}")
    
    # Show severity breakdown
    severity = security_results.get('summary', {}).get('severity_breakdown', {})
    if severity:
        print(f"\n📈 Severity Breakdown:")
        for level, count in severity.items():
            print(f"   {level}: {count}")
    
    # Show sample findings
    findings = security_results.get('findings', [])
    if findings:
        print(f"\n🔍 Sample Findings:")
        for i, finding in enumerate(findings[:3]):
            print(f"   {i+1}. {finding.get('title', 'Unknown')} ({finding.get('severity', 'Unknown')})")
    
    print(f"\n✅ Report and ticket generation test completed successfully!")
    
    return {
        "report_file": report_file,
        "tickets_file": tickets_file,
        "findings_count": len(findings)
    }


if __name__ == "__main__":
    test_report_and_ticket_generation()
