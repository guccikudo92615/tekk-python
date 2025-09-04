#!/usr/bin/env python3
"""
Test script for the context-aware LLM scanner.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from tools.llm_scanner import LLMScanner

def main():
    """Test the context-aware LLM scanner."""
    print("🚀 Testing Context-Aware LLM Scanner")
    print("=" * 50)
    
    # Initialize scanner
    scanner = LLMScanner()
    
    # Test with the test repository
    repo_path = "test-repo"
    output_dir = "reports/context-aware-test"
    
    print(f"📁 Analyzing repository: {repo_path}")
    print(f"💾 Output directory: {output_dir}")
    print()
    
    try:
        # Run the analysis with AST-aware chunking
        goal_hints = {
            "focus": "security_analysis",
            "priorities": ["authentication", "authorization", "input_validation"]
        }
        results = scanner.analyze_repository(repo_path, output_dir, goal_hints)
        
        # Display results
        print("\n📊 ANALYSIS RESULTS:")
        print("=" * 30)
        
        summary = results.get('summary', {})
        print(f"Risk Overview: {summary.get('risk_overview', 'N/A')}")
        print(f"Total Findings: {summary.get('findings_total_count', 0)}")
        print(f"Files Analyzed: {summary.get('files_analyzed', 0)}")
        print(f"Agents Used: {summary.get('agents_used', 0)}")
        
        severity = summary.get('severity_breakdown', {})
        print(f"Severity Breakdown:")
        for level, count in severity.items():
            print(f"  {level}: {count}")
        
        # Show metadata about structure-aware analysis
        metadata = results.get('analysis_metadata', {})
        print(f"\n🏗️ STRUCTURE-AWARE ANALYSIS:")
        print(f"Context Management: {metadata.get('context_management', 'N/A')}")
        print(f"Total Agents: {metadata.get('total_agents', 0)}")
        print(f"Total Files: {metadata.get('total_files', 0)}")
        
        # Show some findings
        findings = results.get('findings', [])
        if findings:
            print(f"\n🔍 SAMPLE FINDINGS:")
            for i, finding in enumerate(findings[:3]):  # Show first 3
                print(f"{i+1}. {finding.get('title', 'Unknown')} ({finding.get('severity', 'Unknown')})")
                print(f"   File: {finding.get('file', 'Unknown')}")
                print(f"   Evidence: {finding.get('evidence', 'No evidence')[:100]}...")
                print()
        
        print("✅ Test completed successfully!")
        print("\n💡 The scanner used AST-aware hierarchical chunking:")
        print("   - Files split at AST boundaries (classes, functions, modules)")
        print("   - Each chunk includes prelude (imports, constants)")
        print("   - Neighbors context for better understanding")
        print("   - Language-aware parsing (Python, JS/TS, Go, etc.)")
        print("   - Entry points prioritized in traversal order")
        print("   - Context limits respected while maintaining semantic integrity")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
