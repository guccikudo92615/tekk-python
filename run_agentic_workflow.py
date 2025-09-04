#!/usr/bin/env python3
"""
Simple orchestrator to run the complete agentic security workflow.
Uses existing tools: llm_scanner, report_writer, ticket_writer
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from tools.llm_scanner import LLMScanner
from tools.report_writer import ReportWriter
from tools.ticket_writer import TicketWriter


def run_complete_workflow(repo_path: str, output_dir: str = "reports"):
    """Run the complete agentic security analysis workflow."""
    
    print("🚀 Starting Complete Agentic Security Workflow")
    print("=" * 60)
    print(f"📁 Repository: {repo_path}")
    print(f"💾 Output Directory: {output_dir}")
    print()
    
    # Step 1: Run AST-aware security analysis
    print("🔍 STEP 1: AST-Aware Security Analysis")
    print("-" * 40)
    scanner = LLMScanner()
    security_results = scanner.analyze_repository(repo_path, output_dir)
    print(f"✅ Security analysis complete: {len(security_results.get('findings', []))} findings")
    print()
    
    # Step 2: Generate comprehensive report
    print("📝 STEP 2: Generate Comprehensive Report")
    print("-" * 40)
    report_writer = ReportWriter()
    
    # Prepare report data
    report_data = {
        "repository": repo_path,
        "findings": security_results.get('findings', []),
        "metadata": security_results.get('analysis_metadata', {}),
        "summary": security_results.get('summary', {}),
        "timestamp": datetime.now().isoformat()
    }
    
    # Generate report
    report_file = Path(output_dir) / "comprehensive_security_report.json"
    report_writer.write_to_file(report_data, str(report_file))
    print(f"✅ Report generated: {report_file}")
    print()
    
    # Step 3: Generate security tickets
    print("🎫 STEP 3: Generate Security Tickets")
    print("-" * 40)
    ticket_writer = TicketWriter()
    
    # Generate tickets from findings
    tickets = ticket_writer.convert_findings_to_tickets(security_results)
    tickets_file = Path(output_dir) / "security_tickets.json"
    ticket_writer.write_tickets_to_file(tickets, str(tickets_file))
    print(f"✅ Tickets generated: {tickets_file}")
    print()
    
    # Step 4: Summary
    print("🎉 AGENTIC WORKFLOW COMPLETE!")
    print("=" * 60)
    print(f"🔍 Security Findings: {len(security_results.get('findings', []))}")
    print(f"📝 Report: {report_file}")
    print(f"🎫 Tickets: {tickets_file}")
    
    # Show severity breakdown
    severity = security_results.get('summary', {}).get('severity_breakdown', {})
    if severity:
        print(f"\n📊 Severity Breakdown:")
        for level, count in severity.items():
            print(f"   {level}: {count}")
    
    return {
        "security_results": security_results,
        "report_file": report_file,
        "tickets_file": tickets_file
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Complete Agentic Security Workflow")
    parser.add_argument("repo_path", help="Path to the repository to analyze")
    parser.add_argument("--output-dir", default="reports", help="Output directory for results")
    
    args = parser.parse_args()
    
    # Run the complete workflow
    results = run_complete_workflow(args.repo_path, args.output_dir)
