"""
Efficient Storage System for Code Graph Data
Hybrid approach using SQL for structured data and vector DB for semantic search
"""

import json
import sqlite3
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import numpy as np
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

@dataclass
class StorageConfig:
    """Configuration for code graph storage."""
    sqlite_path: str = "code_graph.db"
    chroma_path: str = "./chroma_db"
    embedding_model: str = "all-MiniLM-L6-v2"  # Lightweight, fast model
    batch_size: int = 100

class CodeGraphStorage:
    """Efficient storage system for code graph data."""
    
    def __init__(self, config: StorageConfig = None):
        self.config = config or StorageConfig()
        self.embedding_model = SentenceTransformer(self.config.embedding_model)
        self.chroma_client = None
        self._init_storage()
    
    def _init_storage(self):
        """Initialize SQLite and ChromaDB storage."""
        # Initialize SQLite
        self._init_sqlite()
        
        # Initialize ChromaDB
        self._init_chroma()
    
    def _init_sqlite(self):
        """Initialize SQLite database with optimized schema."""
        self.conn = sqlite3.connect(self.config.sqlite_path)
        self.conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
        self.conn.execute("PRAGMA synchronous=NORMAL")  # Faster writes
        self.conn.execute("PRAGMA cache_size=10000")  # Larger cache
        
        # Create optimized tables
        self.conn.executescript("""
            -- Repositories table
            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                language TEXT NOT NULL,
                total_files INTEGER NOT NULL,
                total_functions INTEGER NOT NULL,
                total_classes INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Packages table
            CREATE TABLE IF NOT EXISTS packages (
                id INTEGER PRIMARY KEY,
                repository_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                dependencies TEXT,  -- JSON array
                exports TEXT,       -- JSON array
                FOREIGN KEY (repository_id) REFERENCES repositories(id),
                UNIQUE(repository_id, name)
            );
            
            -- Files table
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY,
                package_id INTEGER NOT NULL,
                path TEXT NOT NULL,
                dependencies TEXT,  -- JSON array
                exports TEXT,       -- JSON array
                detailed_dependencies TEXT,  -- JSON array
                FOREIGN KEY (package_id) REFERENCES packages(id),
                UNIQUE(package_id, path)
            );
            
            -- Functions table
            CREATE TABLE IF NOT EXISTS functions (
                id INTEGER PRIMARY KEY,
                file_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                start_line INTEGER NOT NULL,
                length INTEGER NOT NULL,
                parameters TEXT,    -- JSON array
                return_type TEXT,
                docstring TEXT,
                calls_to TEXT,      -- JSON array
                dependencies TEXT,  -- JSON array
                types TEXT,         -- JSON array
                FOREIGN KEY (file_id) REFERENCES files(id),
                UNIQUE(file_id, name, start_line)
            );
            
            -- Classes table
            CREATE TABLE IF NOT EXISTS classes (
                id INTEGER PRIMARY KEY,
                file_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                start_line INTEGER NOT NULL,
                length INTEGER NOT NULL,
                methods TEXT,       -- JSON array
                attributes TEXT,    -- JSON array
                base_classes TEXT,  -- JSON array
                docstring TEXT,
                dependencies TEXT,  -- JSON array
                FOREIGN KEY (file_id) REFERENCES files(id),
                UNIQUE(file_id, name, start_line)
            );
            
            -- Variables table
            CREATE TABLE IF NOT EXISTS variables (
                id INTEGER PRIMARY KEY,
                file_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                start_line INTEGER NOT NULL,
                type TEXT,
                value TEXT,
                scope TEXT,
                FOREIGN KEY (file_id) REFERENCES files(id),
                UNIQUE(file_id, name, start_line)
            );
            
            -- Dependencies table for efficient relationship queries
            CREATE TABLE IF NOT EXISTS dependencies (
                id INTEGER PRIMARY KEY,
                source_type TEXT NOT NULL,  -- 'function', 'class', 'file', 'package'
                source_id INTEGER NOT NULL,
                target_name TEXT NOT NULL,
                target_type TEXT NOT NULL,  -- 'import', 'call', 'inherit', etc.
                FOREIGN KEY (source_id) REFERENCES functions(id) OR 
                         REFERENCES classes(id) OR 
                         REFERENCES files(id) OR 
                         REFERENCES packages(id)
            );
            
            -- Create indexes for efficient queries
            CREATE INDEX IF NOT EXISTS idx_repositories_name ON repositories(name);
            CREATE INDEX IF NOT EXISTS idx_packages_repository ON packages(repository_id);
            CREATE INDEX IF NOT EXISTS idx_files_package ON files(package_id);
            CREATE INDEX IF NOT EXISTS idx_functions_file ON functions(file_id);
            CREATE INDEX IF NOT EXISTS idx_functions_name ON functions(name);
            CREATE INDEX IF NOT EXISTS idx_classes_file ON classes(file_id);
            CREATE INDEX IF NOT EXISTS idx_classes_name ON classes(name);
            CREATE INDEX IF NOT EXISTS idx_dependencies_source ON dependencies(source_id);
            CREATE INDEX IF NOT EXISTS idx_dependencies_target ON dependencies(target_name);
        """)
        
        self.conn.commit()
    
    def _init_chroma(self):
        """Initialize ChromaDB for semantic search."""
        self.chroma_client = chromadb.PersistentClient(
            path=self.config.chroma_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Create collections for different types of code elements
        self.function_collection = self.chroma_client.get_or_create_collection(
            name="functions",
            metadata={"description": "Function embeddings for semantic search"}
        )
        
        self.class_collection = self.chroma_client.get_or_create_collection(
            name="classes", 
            metadata={"description": "Class embeddings for semantic search"}
        )
        
        self.file_collection = self.chroma_client.get_or_create_collection(
            name="files",
            metadata={"description": "File embeddings for semantic search"}
        )
    
    def store_code_graph(self, code_graph_data: Dict[str, Any]) -> str:
        """Store code graph data efficiently."""
        repo_name = code_graph_data["name"]
        
        # Check if repository already exists
        cursor = self.conn.execute(
            "SELECT id FROM repositories WHERE name = ?", (repo_name,)
        )
        repo_row = cursor.fetchone()
        
        if repo_row:
            repo_id = repo_row[0]
            # Update existing repository
            self._update_repository(repo_id, code_graph_data)
        else:
            # Create new repository
            repo_id = self._create_repository(code_graph_data)
        
        # Store packages and their contents
        self._store_packages(repo_id, code_graph_data["packages"])
        
        # Generate embeddings for semantic search
        self._generate_embeddings(repo_id, code_graph_data)
        
        return f"Repository {repo_name} stored successfully"
    
    def _create_repository(self, code_graph_data: Dict[str, Any]) -> int:
        """Create a new repository record."""
        cursor = self.conn.execute("""
            INSERT INTO repositories (name, language, total_files, total_functions, total_classes)
            VALUES (?, ?, ?, ?, ?)
        """, (
            code_graph_data["name"],
            code_graph_data["language"],
            code_graph_data["total_files"],
            code_graph_data["total_functions"],
            code_graph_data["total_classes"]
        ))
        return cursor.lastrowid
    
    def _update_repository(self, repo_id: int, code_graph_data: Dict[str, Any]):
        """Update existing repository data."""
        self.conn.execute("""
            UPDATE repositories 
            SET language = ?, total_files = ?, total_functions = ?, total_classes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            code_graph_data["language"],
            code_graph_data["total_files"],
            code_graph_data["total_functions"],
            code_graph_data["total_classes"],
            repo_id
        ))
        
        # Clear existing data
        self.conn.execute("DELETE FROM packages WHERE repository_id = ?", (repo_id,))
    
    def _store_packages(self, repo_id: int, packages: List[Dict[str, Any]]):
        """Store packages and their contents."""
        for package_data in packages:
            # Store package
            package_cursor = self.conn.execute("""
                INSERT INTO packages (repository_id, name, dependencies, exports)
                VALUES (?, ?, ?, ?)
            """, (
                repo_id,
                package_data["name"],
                json.dumps(package_data.get("dependencies", [])),
                json.dumps(package_data.get("exports", []))
            ))
            package_id = package_cursor.lastrowid
            
            # Store files
            self._store_files(package_id, package_data["files"])
    
    def _store_files(self, package_id: int, files: List[Dict[str, Any]]):
        """Store files and their contents."""
        for file_data in files:
            # Store file
            file_cursor = self.conn.execute("""
                INSERT INTO files (package_id, path, dependencies, exports, detailed_dependencies)
                VALUES (?, ?, ?, ?, ?)
            """, (
                package_id,
                file_data["path"],
                json.dumps(file_data.get("dependencies", [])),
                json.dumps(file_data.get("exports", [])),
                json.dumps(file_data.get("detailed_dependencies", []))
            ))
            file_id = file_cursor.lastrowid
            
            # Store functions
            for func_data in file_data.get("functions", []):
                self._store_function(file_id, func_data)
            
            # Store classes
            for class_data in file_data.get("types", []):
                self._store_class(file_id, class_data)
            
            # Store variables
            for var_data in file_data.get("variables", []):
                self._store_variable(file_id, var_data)
    
    def _store_function(self, file_id: int, func_data: Dict[str, Any]):
        """Store function data."""
        cursor = self.conn.execute("""
            INSERT INTO functions (file_id, name, start_line, length, parameters, return_type, 
                                 docstring, calls_to, dependencies, types)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            file_id,
            func_data["name"],
            func_data["start_line"],
            func_data["length"],
            json.dumps(func_data.get("parameters", [])),
            func_data.get("return_type"),
            func_data.get("docstring"),
            json.dumps(func_data.get("calls_to", [])),
            json.dumps(func_data.get("dependencies", [])),
            json.dumps(func_data.get("types", []))
        ))
        
        # Store dependencies
        func_id = cursor.lastrowid
        self._store_dependencies("function", func_id, func_data.get("calls_to", []), "call")
        self._store_dependencies("function", func_id, func_data.get("dependencies", []), "import")
    
    def _store_class(self, file_id: int, class_data: Dict[str, Any]):
        """Store class data."""
        cursor = self.conn.execute("""
            INSERT INTO classes (file_id, name, start_line, length, methods, attributes, 
                               base_classes, docstring, dependencies)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            file_id,
            class_data["name"],
            class_data["start_line"],
            class_data["length"],
            json.dumps(class_data.get("methods", [])),
            json.dumps(class_data.get("attributes", [])),
            json.dumps(class_data.get("base_classes", [])),
            class_data.get("docstring"),
            json.dumps(class_data.get("dependencies", []))
        ))
        
        # Store dependencies
        class_id = cursor.lastrowid
        self._store_dependencies("class", class_id, class_data.get("base_classes", []), "inherit")
        self._store_dependencies("class", class_id, class_data.get("dependencies", []), "import")
    
    def _store_variable(self, file_id: int, var_data: Dict[str, Any]):
        """Store variable data."""
        self.conn.execute("""
            INSERT INTO variables (file_id, name, start_line, type, value, scope)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            file_id,
            var_data["name"],
            var_data["start_line"],
            var_data.get("type"),
            var_data.get("value"),
            var_data.get("scope")
        ))
    
    def _store_dependencies(self, source_type: str, source_id: int, targets: List[str], target_type: str):
        """Store dependency relationships."""
        for target in targets:
            self.conn.execute("""
                INSERT INTO dependencies (source_type, source_id, target_name, target_type)
                VALUES (?, ?, ?, ?)
            """, (source_type, source_id, target, target_type))
    
    def _generate_embeddings(self, repo_id: int, code_graph_data: Dict[str, Any]):
        """Generate embeddings for semantic search."""
        print("🔍 Generating embeddings for semantic search...")
        
        # Get repository name for context
        cursor = self.conn.execute("SELECT name FROM repositories WHERE id = ?", (repo_id,))
        repo_name = cursor.fetchone()[0]
        
        # Process functions
        function_docs = []
        function_metadatas = []
        function_ids = []
        
        cursor = self.conn.execute("""
            SELECT f.id, f.name, f.docstring, f.parameters, f.return_type, 
                   fi.path, p.name as package_name
            FROM functions f
            JOIN files fi ON f.file_id = fi.id
            JOIN packages p ON fi.package_id = p.id
            WHERE p.repository_id = ?
        """, (repo_id,))
        
        for row in cursor.fetchall():
            func_id, name, docstring, params, return_type, file_path, package_name = row
            
            # Create document for embedding
            doc_parts = [f"Function: {name}"]
            if docstring:
                doc_parts.append(f"Description: {docstring}")
            if params:
                doc_parts.append(f"Parameters: {json.loads(params)}")
            if return_type:
                doc_parts.append(f"Returns: {return_type}")
            
            doc = " | ".join(doc_parts)
            function_docs.append(doc)
            function_metadatas.append({
                "repository": repo_name,
                "package": package_name,
                "file": file_path,
                "name": name,
                "type": "function"
            })
            function_ids.append(f"func_{func_id}")
        
        # Store function embeddings in batches
        if function_docs:
            embeddings = self.embedding_model.encode(function_docs)
            for i in range(0, len(function_docs), self.config.batch_size):
                batch_docs = function_docs[i:i+self.config.batch_size]
                batch_embeddings = embeddings[i:i+self.config.batch_size]
                batch_metadatas = function_metadatas[i:i+self.config.batch_size]
                batch_ids = function_ids[i:i+self.config.batch_size]
                
                self.function_collection.add(
                    documents=batch_docs,
                    embeddings=batch_embeddings.tolist(),
                    metadatas=batch_metadatas,
                    ids=batch_ids
                )
        
        # Process classes (similar approach)
        class_docs = []
        class_metadatas = []
        class_ids = []
        
        cursor = self.conn.execute("""
            SELECT c.id, c.name, c.docstring, c.methods, c.attributes, c.base_classes,
                   fi.path, p.name as package_name
            FROM classes c
            JOIN files fi ON c.file_id = fi.id
            JOIN packages p ON fi.package_id = p.id
            WHERE p.repository_id = ?
        """, (repo_id,))
        
        for row in cursor.fetchall():
            class_id, name, docstring, methods, attributes, base_classes, file_path, package_name = row
            
            doc_parts = [f"Class: {name}"]
            if docstring:
                doc_parts.append(f"Description: {docstring}")
            if methods:
                doc_parts.append(f"Methods: {json.loads(methods)}")
            if attributes:
                doc_parts.append(f"Attributes: {json.loads(attributes)}")
            if base_classes:
                doc_parts.append(f"Inherits from: {json.loads(base_classes)}")
            
            doc = " | ".join(doc_parts)
            class_docs.append(doc)
            class_metadatas.append({
                "repository": repo_name,
                "package": package_name,
                "file": file_path,
                "name": name,
                "type": "class"
            })
            class_ids.append(f"class_{class_id}")
        
        # Store class embeddings
        if class_docs:
            embeddings = self.embedding_model.encode(class_docs)
            for i in range(0, len(class_docs), self.config.batch_size):
                batch_docs = class_docs[i:i+self.config.batch_size]
                batch_embeddings = embeddings[i:i+self.config.batch_size]
                batch_metadatas = class_metadatas[i:i+self.config.batch_size]
                batch_ids = class_ids[i:i+self.config.batch_size]
                
                self.class_collection.add(
                    documents=batch_docs,
                    embeddings=batch_embeddings.tolist(),
                    metadatas=batch_metadatas,
                    ids=batch_ids
                )
        
        print(f"✅ Generated embeddings for {len(function_docs)} functions and {len(class_docs)} classes")
    
    def search_functions(self, query: str, repository: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search functions using semantic similarity."""
        query_embedding = self.embedding_model.encode([query])
        
        where_clause = {"repository": repository} if repository else None
        
        results = self.function_collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=limit,
            where=where_clause
        )
        
        return self._format_search_results(results)
    
    def search_classes(self, query: str, repository: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search classes using semantic similarity."""
        query_embedding = self.embedding_model.encode([query])
        
        where_clause = {"repository": repository} if repository else None
        
        results = self.class_collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=limit,
            where=where_clause
        )
        
        return self._format_search_results(results)
    
    def _format_search_results(self, results) -> List[Dict[str, Any]]:
        """Format search results for easy consumption."""
        formatted_results = []
        
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                formatted_results.append({
                    'document': doc,
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if results['distances'] else None
                })
        
        return formatted_results
    
    def get_repository_stats(self, repository_name: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a repository."""
        cursor = self.conn.execute("""
            SELECT r.*, 
                   COUNT(DISTINCT p.id) as package_count,
                   COUNT(DISTINCT f.id) as file_count,
                   COUNT(DISTINCT func.id) as function_count,
                   COUNT(DISTINCT c.id) as class_count,
                   COUNT(DISTINCT v.id) as variable_count
            FROM repositories r
            LEFT JOIN packages p ON r.id = p.repository_id
            LEFT JOIN files f ON p.id = f.package_id
            LEFT JOIN functions func ON f.id = func.file_id
            LEFT JOIN classes c ON f.id = c.file_id
            LEFT JOIN variables v ON f.id = v.file_id
            WHERE r.name = ?
            GROUP BY r.id
        """, (repository_name,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            'name': row[1],
            'language': row[2],
            'total_files': row[3],
            'total_functions': row[4],
            'total_classes': row[5],
            'package_count': row[7],
            'file_count': row[8],
            'function_count': row[9],
            'class_count': row[10],
            'variable_count': row[11],
            'created_at': row[6],
            'updated_at': row[7]
        }
    
    def get_dependency_graph(self, repository_name: str) -> Dict[str, Any]:
        """Get dependency graph for a repository."""
        cursor = self.conn.execute("""
            SELECT d.source_type, d.source_id, d.target_name, d.target_type,
                   f.name as function_name, c.name as class_name, fi.path as file_path
            FROM dependencies d
            JOIN repositories r ON r.name = ?
            JOIN packages p ON p.repository_id = r.id
            JOIN files fi ON fi.package_id = p.id
            LEFT JOIN functions f ON d.source_type = 'function' AND d.source_id = f.id
            LEFT JOIN classes c ON d.source_type = 'class' AND d.source_id = c.id
            WHERE (d.source_type = 'function' AND f.file_id = fi.id) OR
                  (d.source_type = 'class' AND c.file_id = fi.id)
        """, (repository_name,))
        
        nodes = set()
        edges = []
        
        for row in cursor.fetchall():
            source_type, source_id, target_name, target_type, func_name, class_name, file_path = row
            
            source_name = func_name or class_name
            if source_name:
                nodes.add((source_name, source_type, file_path))
                nodes.add((target_name, target_type, "external"))
                edges.append({
                    'source': source_name,
                    'target': target_name,
                    'type': target_type,
                    'file': file_path
                })
        
        return {
            'nodes': [{'name': name, 'type': type_, 'file': file} for name, type_, file in nodes],
            'edges': edges
        }
    
    def close(self):
        """Close database connections."""
        if hasattr(self, 'conn'):
            self.conn.close()
        if self.chroma_client:
            # ChromaDB handles its own cleanup
            pass

# Convenience functions
def store_code_graph_from_file(json_file_path: str, storage_config: StorageConfig = None) -> str:
    """Store code graph from JSON file."""
    with open(json_file_path, 'r') as f:
        code_graph_data = json.load(f)
    
    storage = CodeGraphStorage(storage_config)
    result = storage.store_code_graph(code_graph_data)
    storage.close()
    
    return result

def search_code_elements(query: str, repository: str = None, element_type: str = "function") -> List[Dict[str, Any]]:
    """Search code elements using semantic similarity."""
    storage = CodeGraphStorage()
    
    if element_type == "function":
        results = storage.search_functions(query, repository)
    elif element_type == "class":
        results = storage.search_classes(query, repository)
    else:
        raise ValueError("element_type must be 'function' or 'class'")
    
    storage.close()
    return results
