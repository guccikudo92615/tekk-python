#!/usr/bin/env python3
"""
Test script for the Universal Code Graph Generator.
"""

import sys
import json
from pathlib import Path

# Add the tools directory to the path
sys.path.append(str(Path(__file__).parent / "tools"))

from universal_code_graph import UniversalCodeGraphGenerator, create_code_graph

def main():
    """Test the universal code graph generator on the test repository."""
    print("🧪 Testing Universal Code Graph Generator on test-repo...")
    
    # Test with the convenience function (similar to python-code-graph API)
    print("\n📊 Creating code graph...")
    code_graph = create_code_graph("test-repo", "test_repo_universal_graph.json")
    
    # Print summary
    print("\n" + "="*60)
    print("📊 CODE GRAPH SUMMARY")
    print("="*60)
    print(f"Repository: {code_graph.name}")
    print(f"Language: {code_graph.language}")
    print(f"Total Files: {code_graph.total_files}")
    print(f"Total Functions: {code_graph.total_functions}")
    print(f"Total Classes: {code_graph.total_classes}")
    print(f"Total Variables: {code_graph.total_variables}")
    print(f"Packages: {len(code_graph.packages)}")
    
    # Print package details
    print("\n" + "="*60)
    print("📦 PACKAGE DETAILS")
    print("="*60)
    
    for i, package in enumerate(code_graph.packages[:5]):  # Show first 5 packages
        print(f"\n{i+1}. {package.name}")
        print(f"   Files: {len(package.files)}")
        print(f"   Dependencies: {len(package.dependencies)}")
        print(f"   Exports: {len(package.exports)}")
        
        # Show sample files
        if package.files:
            sample_files = package.files[:3]
            print(f"   Sample files:")
            for file_info in sample_files:
                print(f"     - {file_info.path}")
                print(f"       Functions: {len(file_info.functions)}")
                print(f"       Classes: {len(file_info.types)}")
                print(f"       Variables: {len(file_info.variables)}")
                if file_info.functions:
                    print(f"       Sample functions: {[f.name for f in file_info.functions[:3]]}")
                if file_info.types:
                    print(f"       Sample classes: {[c.name for c in file_info.types[:3]]}")
    
    # Show detailed function information
    print("\n" + "="*60)
    print("🔍 DETAILED FUNCTION ANALYSIS")
    print("="*60)
    
    function_count = 0
    for package in code_graph.packages:
        for file_info in package.files:
            for func in file_info.functions[:2]:  # Show first 2 functions per file
                if function_count >= 10:  # Limit to 10 functions total
                    break
                
                print(f"\nFunction: {func.name}")
                print(f"  File: {func.file_name}")
                print(f"  Location: Line {func.start_line} (Length: {func.length})")
                if func.parameters:
                    print(f"  Parameters: {func.parameters}")
                if func.calls_to:
                    print(f"  Calls: {func.calls_to[:5]}{'...' if len(func.calls_to) > 5 else ''}")
                if func.docstring:
                    print(f"  Docstring: {func.docstring[:100]}{'...' if len(func.docstring) > 100 else ''}")
                
                function_count += 1
            
            if function_count >= 10:
                break
        if function_count >= 10:
            break
    
    print(f"\n📁 Universal code graph exported to: test_repo_universal_graph.json")
    print(f"📊 Analysis complete!")
    
    return code_graph

def compare_with_python_code_graph():
    """Compare with python-code-graph if available."""
    try:
        from python_code_graph import create_code_graph as py_create_code_graph
        print("\n🔄 Comparing with python-code-graph...")
        
        # Test python-code-graph on the same repository
        py_graph = py_create_code_graph("test-repo", "test_repo_python_graph.json")
        print(f"✅ python-code-graph found {len(py_graph.get('packages', []))} packages")
        
        # Load and compare the JSON outputs
        with open("test_repo_universal_graph.json", 'r') as f:
            universal_data = json.load(f)
        
        # Check if python-code-graph created a file
        if Path("test_repo_python_graph.json").exists():
            with open("test_repo_python_graph.json", 'r') as f:
                python_data = json.load(f)
        else:
            python_data = {"packages": []}
        
        print(f"📊 Comparison:")
        print(f"  Universal Graph: {universal_data['total_files']} files, {universal_data['total_functions']} functions")
        print(f"  Python Graph: {len(python_data.get('packages', []))} packages")
        
    except ImportError:
        print("\n⚠️  python-code-graph not available for comparison")
        print("   Install with: pip install python-code-graph")

if __name__ == "__main__":
    try:
        code_graph = main()
        compare_with_python_code_graph()
        print("\n✅ Test completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
