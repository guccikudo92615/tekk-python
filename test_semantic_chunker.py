#!/usr/bin/env python3
"""
Test script for the Semantic Chunker on the test repository.
"""

import sys
import json
from pathlib import Path

# Add the tools directory to the path
sys.path.append(str(Path(__file__).parent / "tools"))

from semantic_chunker import SemanticChunker

def main():
    """Test the semantic chunker on the test repository."""
    print("🧪 Testing Semantic Chunker on test-repo...")
    
    # Check if test-repo exists
    test_repo_path = Path("test-repo")
    if not test_repo_path.exists():
        print(f"❌ test-repo directory not found at {test_repo_path.absolute()}")
        return None, None
    
    print(f"✅ Found test-repo at {test_repo_path.absolute()}")
    
    # Initialize the chunker
    chunker = SemanticChunker("test-repo")
    
    # Debug: Check what files are being found
    print("\n🔍 Debugging file discovery...")
    extensions = ['*.ts', '*.tsx', '*.js', '*.jsx', '*.py', '*.java', '*.go', '*.rs']
    all_files = []
    for ext in extensions:
        all_files.extend(test_repo_path.rglob(ext))
    
    print(f"Found {len(all_files)} code files:")
    for f in all_files[:10]:  # Show first 10
        print(f"  - {f}")
    if len(all_files) > 10:
        print(f"  ... and {len(all_files) - 10} more")
    
    # Analyze the repository
    print("\n📊 Analyzing repository structure...")
    modules = chunker.analyze_repository()
    
    print(f"✅ Found {len(modules)} semantic modules")
    
    # Get repository insights
    print("\n🔍 Generating repository insights...")
    insights = chunker.get_repository_insights()
    
    # Export the graph
    print("\n📁 Exporting graph data...")
    chunker.export_graph("test_repo_graph.json")
    
    # Get prioritized chunks
    print("\n📋 Getting prioritized chunks...")
    prioritized = chunker.get_prioritized_chunks()
    
    # Print results
    print("\n" + "="*60)
    print("📊 REPOSITORY INSIGHTS")
    print("="*60)
    print(json.dumps(insights, indent=2))
    
    print("\n" + "="*60)
    print("🧩 SEMANTIC MODULES")
    print("="*60)
    for i, (name, module) in enumerate(prioritized[:10]):  # Show first 10
        print(f"\n{i+1}. {name}")
        print(f"   Type: {module.module_type.category} - {module.module_type.subcategory}")
        print(f"   Confidence: {module.module_type.confidence:.2f}")
        print(f"   Files: {len(module.files)}")
        print(f"   Size: {module.size:,} characters")
        print(f"   Description: {module.description}")
        if module.files:
            print(f"   Sample files: {module.files[:3]}{'...' if len(module.files) > 3 else ''}")
    
    print(f"\n📁 Graph data exported to: test_repo_graph.json")
    print(f"📊 Total modules analyzed: {len(modules)}")
    
    return insights, modules

if __name__ == "__main__":
    try:
        insights, modules = main()
        print("\n✅ Test completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
