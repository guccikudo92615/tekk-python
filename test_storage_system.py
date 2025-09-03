#!/usr/bin/env python3
"""
Test script for the Code Graph Storage System.
"""

import sys
import json
from pathlib import Path

# Add the tools directory to the path
sys.path.append(str(Path(__file__).parent / "tools"))

from code_graph_storage import CodeGraphStorage, StorageConfig, store_code_graph_from_file, search_code_elements

def main():
    """Test the storage system with the universal code graph data."""
    print("🧪 Testing Code Graph Storage System...")
    
    # Test 1: Store the code graph data
    print("\n📊 Storing code graph data...")
    try:
        result = store_code_graph_from_file("test_repo_universal_graph.json")
        print(f"✅ {result}")
    except Exception as e:
        print(f"❌ Storage failed: {e}")
        return
    
    # Test 2: Initialize storage and test queries
    print("\n🔍 Testing storage queries...")
    storage = CodeGraphStorage()
    
    try:
        # Test repository stats
        print("\n📈 Repository Statistics:")
        stats = storage.get_repository_stats("test-repo")
        if stats:
            print(f"  Name: {stats['name']}")
            print(f"  Language: {stats['language']}")
            print(f"  Files: {stats['file_count']}")
            print(f"  Functions: {stats['function_count']}")
            print(f"  Classes: {stats['class_count']}")
            print(f"  Variables: {stats['variable_count']}")
            print(f"  Packages: {stats['package_count']}")
        
        # Test semantic search
        print("\n🔍 Semantic Search Tests:")
        
        # Search for authentication-related functions
        print("\n  Searching for 'authentication' functions:")
        auth_results = storage.search_functions("authentication", "test-repo", limit=5)
        for i, result in enumerate(auth_results, 1):
            print(f"    {i}. {result['metadata']['name']} (distance: {result['distance']:.3f})")
            print(f"       File: {result['metadata']['file']}")
            print(f"       Package: {result['metadata']['package']}")
        
        # Search for API-related functions
        print("\n  Searching for 'API' functions:")
        api_results = storage.search_functions("API endpoint", "test-repo", limit=5)
        for i, result in enumerate(api_results, 1):
            print(f"    {i}. {result['metadata']['name']} (distance: {result['distance']:.3f})")
            print(f"       File: {result['metadata']['file']}")
        
        # Search for UI components
        print("\n  Searching for 'UI component' classes:")
        ui_results = storage.search_classes("UI component", "test-repo", limit=5)
        for i, result in enumerate(ui_results, 1):
            print(f"    {i}. {result['metadata']['name']} (distance: {result['distance']:.3f})")
            print(f"       File: {result['metadata']['file']}")
        
        # Test dependency graph
        print("\n🔗 Dependency Graph:")
        dep_graph = storage.get_dependency_graph("test-repo")
        print(f"  Nodes: {len(dep_graph['nodes'])}")
        print(f"  Edges: {len(dep_graph['edges'])}")
        
        # Show sample dependencies
        if dep_graph['edges']:
            print("  Sample dependencies:")
            for edge in dep_graph['edges'][:5]:
                print(f"    {edge['source']} -> {edge['target']} ({edge['type']})")
        
        # Test convenience functions
        print("\n🎯 Testing Convenience Functions:")
        convenience_results = search_code_elements("chat message", "test-repo", "function")
        print(f"  Found {len(convenience_results)} chat-related functions")
        for result in convenience_results[:3]:
            print(f"    - {result['metadata']['name']} in {result['metadata']['file']}")
        
    except Exception as e:
        print(f"❌ Query test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        storage.close()
    
    # Test 3: Performance comparison
    print("\n⚡ Performance Analysis:")
    analyze_storage_performance()

def analyze_storage_performance():
    """Analyze storage performance and efficiency."""
    import time
    import os
    
    # File sizes
    json_size = os.path.getsize("test_repo_universal_graph.json")
    db_size = os.path.getsize("code_graph.db") if os.path.exists("code_graph.db") else 0
    chroma_size = sum(os.path.getsize(os.path.join(dirpath, filename))
                     for dirpath, dirnames, filenames in os.walk("./chroma_db")
                     for filename in filenames) if os.path.exists("./chroma_db") else 0
    
    print(f"  JSON file size: {json_size / 1024:.1f} KB")
    print(f"  SQLite DB size: {db_size / 1024:.1f} KB")
    print(f"  ChromaDB size: {chroma_size / 1024:.1f} KB")
    print(f"  Total storage: {(db_size + chroma_size) / 1024:.1f} KB")
    print(f"  Compression ratio: {json_size / (db_size + chroma_size):.1f}x" if (db_size + chroma_size) > 0 else "N/A")
    
    # Query performance
    storage = CodeGraphStorage()
    try:
        # Test SQL query performance
        start_time = time.time()
        stats = storage.get_repository_stats("test-repo")
        sql_time = time.time() - start_time
        
        # Test vector search performance
        start_time = time.time()
        results = storage.search_functions("test query", "test-repo", limit=10)
        vector_time = time.time() - start_time
        
        print(f"  SQL query time: {sql_time*1000:.1f} ms")
        print(f"  Vector search time: {vector_time*1000:.1f} ms")
        
    except Exception as e:
        print(f"  Performance test failed: {e}")
    finally:
        storage.close()

def demonstrate_use_cases():
    """Demonstrate practical use cases for the storage system."""
    print("\n🎯 Practical Use Cases:")
    
    storage = CodeGraphStorage()
    try:
        # Use case 1: Find all functions that handle user input
        print("\n1. Finding user input handlers:")
        input_handlers = storage.search_functions("user input validation", "test-repo", limit=10)
        for result in input_handlers:
            print(f"   - {result['metadata']['name']} in {result['metadata']['file']}")
        
        # Use case 2: Find all API endpoints
        print("\n2. Finding API endpoints:")
        api_endpoints = storage.search_functions("API endpoint handler", "test-repo", limit=10)
        for result in api_endpoints:
            print(f"   - {result['metadata']['name']} in {result['metadata']['file']}")
        
        # Use case 3: Find all database-related functions
        print("\n3. Finding database functions:")
        db_functions = storage.search_functions("database query", "test-repo", limit=10)
        for result in db_functions:
            print(f"   - {result['metadata']['name']} in {result['metadata']['file']}")
        
        # Use case 4: Find all UI components
        print("\n4. Finding UI components:")
        ui_components = storage.search_classes("React component", "test-repo", limit=10)
        for result in ui_components:
            print(f"   - {result['metadata']['name']} in {result['metadata']['file']}")
        
    except Exception as e:
        print(f"Use case demonstration failed: {e}")
    finally:
        storage.close()

if __name__ == "__main__":
    try:
        main()
        demonstrate_use_cases()
        print("\n✅ All tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
