#!/usr/bin/env python3
"""
Test script for the AST-aware chunker.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from tools.ast_chunker import ASTChunker

def main():
    """Test the AST chunker."""
    print("🧪 Testing AST-Aware Chunker")
    print("=" * 40)
    
    # Initialize chunker
    chunker = ASTChunker(
        size_threshold=100_000,  # 100KB for testing
        token_threshold=25_000,  # 25k tokens for testing
        prelude_lines=50,
        unit_max_tokens=1000
    )
    
    # Test with the test repository
    repo_path = "test-repo"
    
    print(f"📁 Chunking repository: {repo_path}")
    print()
    
    try:
        # Run chunking
        result = chunker.chunk_repository(repo_path)
        
        # Display results
        print("📊 CHUNKING RESULTS:")
        print("=" * 25)
        
        stats = result['chunking_stats']
        print(f"Total Files: {stats['total_files']}")
        print(f"Total Chunks: {stats['total_chunks']}")
        print(f"Languages: {', '.join(stats['languages_detected'])}")
        print(f"Chunks by Type: {stats['chunks_by_type']}")
        
        print(f"\n🗺️ TRAVERSAL ORDER:")
        print("=" * 20)
        for i, path in enumerate(result['traversal_order'][:10]):  # Show first 10
            print(f"{i+1:2d}. {path}")
        if len(result['traversal_order']) > 10:
            print(f"    ... and {len(result['traversal_order']) - 10} more files")
        
        print(f"\n🔍 SAMPLE CHUNKS:")
        print("=" * 15)
        for i, chunk in enumerate(result['chunks'][:5]):  # Show first 5 chunks
            print(f"{i+1}. {chunk['type'].upper()} - {chunk['path']}")
            print(f"   Language: {chunk['lang']}")
            print(f"   Summary: {chunk['summary']}")
            if chunk.get('unit'):
                unit = chunk['unit']
                print(f"   Unit: {unit['kind']} {unit['name']}")
            if chunk.get('neighbors'):
                neighbors = chunk['neighbors']
                if neighbors.get('prev') or neighbors.get('next'):
                    print(f"   Context: ", end="")
                    if neighbors.get('prev'):
                        print(f"Prev: {neighbors['prev']} ", end="")
                    if neighbors.get('next'):
                        print(f"Next: {neighbors['next']}", end="")
                    print()
            print()
        
        print("✅ AST chunker test completed successfully!")
        print("\n💡 Key Features Demonstrated:")
        print("   - Language detection and AST-aware splitting")
        print("   - Prelude extraction (imports, constants)")
        print("   - Neighbors context for better understanding")
        print("   - Intelligent traversal order (entry points first)")
        print("   - Hierarchical chunk organization")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
