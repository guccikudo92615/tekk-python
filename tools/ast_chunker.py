"""
AST-Aware Hierarchical Chunker for Repository Analysis.
Implements language-aware chunking that respects AST boundaries and maintains semantic integrity.
"""

import json
import hashlib
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from collections import defaultdict

# Try to import tree-sitter, fallback to regex if not available
try:
    import tree_sitter
    from tree_sitter import Language, Parser
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    print("Warning: tree-sitter not available, using regex fallbacks")


@dataclass
class ChunkMetadata:
    """Metadata for a code chunk."""
    chunk_id: str
    type: str  # 'file', 'unit', 'config'
    path: str
    lang: str
    parent_file_hash: Optional[str] = None
    byte_start: int = 0
    byte_end: int = 0
    prelude: Optional[Dict[str, Any]] = None
    unit: Optional[Dict[str, Any]] = None
    neighbors: Optional[Dict[str, str]] = None
    summary: str = ""
    edges: Optional[Dict[str, List[str]]] = None


@dataclass
class FileMetadata:
    """Metadata for a file in the repository."""
    path: str
    size_bytes: int
    sha256: str
    lang: str
    imports: List[str]
    exports: List[str]
    symbols: List[str]
    is_entry_point: bool = False
    centrality_score: float = 0.0


class ASTChunker:
    """AST-aware hierarchical chunker for repository analysis."""
    
    def __init__(self, 
                 size_threshold: int = 400_000,  # 400KB
                 token_threshold: int = 100_000,  # ~100k tokens
                 prelude_lines: int = 200,
                 unit_max_tokens: int = 3000):
        self.size_threshold = size_threshold
        self.token_threshold = token_threshold
        self.prelude_lines = prelude_lines
        self.unit_max_tokens = unit_max_tokens
        
        # Language detection patterns
        self.lang_patterns = {
            'py': ['.py'],
            'js': ['.js'],
            'ts': ['.ts', '.tsx'],
            'jsx': ['.jsx'],
            'go': ['.go'],
            'java': ['.java'],
            'cs': ['.cs'],
            'rs': ['.rs'],
            'php': ['.php'],
            'rb': ['.rb'],
            'cpp': ['.cpp', '.cc', '.cxx'],
            'c': ['.c'],
            'h': ['.h', '.hpp'],
            'json': ['.json'],
            'yaml': ['.yaml', '.yml'],
            'toml': ['.toml'],
            'md': ['.md'],
            'sql': ['.sql']
        }
        
        # Entry point patterns
        self.entry_point_patterns = [
            'main', 'server', 'app', 'index', 'routes', 'entry',
            'start', 'bootstrap', 'init', 'run'
        ]
        
        # Initialize tree-sitter parsers if available
        self.parsers = {}
        if TREE_SITTER_AVAILABLE:
            self._init_tree_sitter_parsers()
    
    def _init_tree_sitter_parsers(self):
        """Initialize tree-sitter parsers for supported languages."""
        # This would require tree-sitter language bindings
        # For now, we'll use regex fallbacks
        pass
    
    def chunk_repository(self, repo_path: str, goal_hints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main entry point for repository chunking.
        
        Args:
            repo_path: Path to the repository
            goal_hints: Optional hints about what to prioritize
            
        Returns:
            Dictionary with chunks, file metadata, and traversal order
        """
        repo_path = Path(repo_path)
        
        # Step 1: Index all files
        print("📁 Indexing repository files...")
        file_metadata = self._index_repository(repo_path)
        
        # Step 2: Calculate centrality scores
        print("🔗 Calculating file centrality...")
        self._calculate_centrality(file_metadata)
        
        # Step 3: Determine traversal order
        print("🗺️ Determining traversal order...")
        traversal_order = self._determine_traversal_order(file_metadata, goal_hints)
        
        # Step 4: Create chunks
        print("✂️ Creating AST-aware chunks...")
        chunks = self._create_chunks(file_metadata, repo_path)
        
        # Step 5: Package results
        result = {
            "repo_id": self._calculate_repo_hash(repo_path),
            "chunks": [asdict(chunk) for chunk in chunks],
            "file_metadata": [asdict(fm) for fm in file_metadata],
            "traversal_order": traversal_order,
            "chunking_stats": {
                "total_files": len(file_metadata),
                "total_chunks": len(chunks),
                "chunks_by_type": self._count_chunks_by_type(chunks),
                "languages_detected": list(set(fm.lang for fm in file_metadata))
            }
        }
        
        return result
    
    def _index_repository(self, repo_path: Path) -> List[FileMetadata]:
        """Index all files in the repository."""
        file_metadata = []
        
        for file_path in repo_path.rglob("*"):
            if file_path.is_file() and not self._should_ignore_file(file_path):
                try:
                    metadata = self._analyze_file(file_path, repo_path)
                    file_metadata.append(metadata)
                except Exception as e:
                    print(f"Warning: Could not analyze {file_path}: {e}")
                    continue
        
        return file_metadata
    
    def _should_ignore_file(self, file_path: Path) -> bool:
        """Determine if a file should be ignored."""
        ignore_patterns = [
            '.git', '__pycache__', 'node_modules', '.venv', 'venv',
            'vendor', 'third_party', 'dist', 'build', '.next',
            '.DS_Store', '*.log', '*.tmp', '*.cache'
        ]
        
        path_str = str(file_path)
        return any(pattern in path_str for pattern in ignore_patterns)
    
    def _analyze_file(self, file_path: Path, repo_root: Path) -> FileMetadata:
        """Analyze a single file and extract metadata."""
        relative_path = str(file_path.relative_to(repo_root))
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Skip binary files
            return FileMetadata(
                path=relative_path,
                size_bytes=file_path.stat().st_size,
                sha256="",
                lang="binary",
                imports=[],
                exports=[],
                symbols=[]
            )
        
        # Calculate hash
        sha256 = hashlib.sha256(content.encode()).hexdigest()
        
        # Detect language
        lang = self._detect_language(file_path)
        
        # Extract imports, exports, symbols
        imports = self._extract_imports(content, lang)
        exports = self._extract_exports(content, lang)
        symbols = self._extract_symbols(content, lang)
        
        # Check if it's an entry point
        is_entry_point = self._is_entry_point(file_path, content)
        
        return FileMetadata(
            path=relative_path,
            size_bytes=len(content.encode()),
            sha256=sha256,
            lang=lang,
            imports=imports,
            exports=exports,
            symbols=symbols,
            is_entry_point=is_entry_point
        )
    
    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension."""
        suffix = file_path.suffix.lower()
        
        for lang, extensions in self.lang_patterns.items():
            if suffix in extensions:
                return lang
        
        return "unknown"
    
    def _extract_imports(self, content: str, lang: str) -> List[str]:
        """Extract import statements from file content."""
        imports = []
        
        if lang == 'py':
            # Python imports
            import_pattern = r'^(?:from\s+(\S+)\s+)?import\s+([^\n]+)'
            for match in re.finditer(import_pattern, content, re.MULTILINE):
                if match.group(1):  # from X import Y
                    imports.append(f"{match.group(1)}.{match.group(2)}")
                else:  # import X
                    imports.append(match.group(2))
        
        elif lang in ['js', 'ts', 'jsx', 'tsx']:
            # JavaScript/TypeScript imports
            import_pattern = r'import\s+(?:{[^}]+}|\w+|\*\s+as\s+\w+)\s+from\s+[\'"]([^\'"]+)[\'"]'
            imports.extend(re.findall(import_pattern, content))
        
        elif lang == 'go':
            # Go imports
            import_pattern = r'import\s+(?:[\'"]([^\'"]+)[\'"]|\(\s*[\'"]([^\'"]+)[\'"]\s*\))'
            for match in re.finditer(import_pattern, content):
                imports.append(match.group(1) or match.group(2))
        
        return imports
    
    def _extract_exports(self, content: str, lang: str) -> List[str]:
        """Extract export statements from file content."""
        exports = []
        
        if lang == 'py':
            # Python: look for __all__ or function/class definitions
            all_pattern = r'__all__\s*=\s*\[([^\]]+)\]'
            all_match = re.search(all_pattern, content)
            if all_match:
                exports.extend([s.strip().strip("'\"") for s in all_match.group(1).split(',')])
        
        elif lang in ['js', 'ts', 'jsx', 'tsx']:
            # JavaScript/TypeScript exports
            export_pattern = r'export\s+(?:default\s+)?(?:function\s+(\w+)|const\s+(\w+)|class\s+(\w+)|interface\s+(\w+))'
            for match in re.finditer(export_pattern, content):
                exports.extend([g for g in match.groups() if g])
        
        return exports
    
    def _extract_symbols(self, content: str, lang: str) -> List[str]:
        """Extract top-level symbols (classes, functions) from file content."""
        symbols = []
        
        if lang == 'py':
            # Python classes and functions
            class_pattern = r'^class\s+(\w+)'
            func_pattern = r'^def\s+(\w+)'
            symbols.extend(re.findall(class_pattern, content, re.MULTILINE))
            symbols.extend(re.findall(func_pattern, content, re.MULTILINE))
        
        elif lang in ['js', 'ts', 'jsx', 'tsx']:
            # JavaScript/TypeScript classes and functions
            class_pattern = r'^(?:export\s+)?class\s+(\w+)'
            func_pattern = r'^(?:export\s+)?(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s+)?\s*\()'
            symbols.extend(re.findall(class_pattern, content, re.MULTILINE))
            for match in re.finditer(func_pattern, content, re.MULTILINE):
                symbols.extend([g for g in match.groups() if g])
        
        elif lang == 'go':
            # Go functions and types
            func_pattern = r'^func\s+(\w+)'
            type_pattern = r'^type\s+(\w+)'
            symbols.extend(re.findall(func_pattern, content, re.MULTILINE))
            symbols.extend(re.findall(type_pattern, content, re.MULTILINE))
        
        return symbols
    
    def _is_entry_point(self, file_path: Path, content: str) -> bool:
        """Determine if a file is likely an entry point."""
        filename = file_path.stem.lower()
        
        # Check filename patterns
        if any(pattern in filename for pattern in self.entry_point_patterns):
            return True
        
        # Check for entry point indicators in content
        entry_indicators = [
            'if __name__ == "__main__"',  # Python
            'main()',  # General
            'app.listen',  # Node.js
            'server.listen',  # Node.js
            'func main()',  # Go
            'public static void main',  # Java
        ]
        
        return any(indicator in content for indicator in entry_indicators)
    
    def _calculate_centrality(self, file_metadata: List[FileMetadata]):
        """Calculate centrality scores based on imports/exports."""
        # Build import graph
        import_graph = defaultdict(set)
        export_map = defaultdict(set)
        
        for fm in file_metadata:
            for imp in fm.imports:
                import_graph[fm.path].add(imp)
            for exp in fm.exports:
                export_map[exp].add(fm.path)
        
        # Calculate centrality (simplified: files that are imported more are more central)
        centrality_scores = defaultdict(float)
        
        for fm in file_metadata:
            # Score based on how many files import from this file
            for exp in fm.exports:
                centrality_scores[fm.path] += len(export_map[exp])
            
            # Boost entry points
            if fm.is_entry_point:
                centrality_scores[fm.path] += 10
        
        # Normalize scores
        max_score = max(centrality_scores.values()) if centrality_scores else 1
        for fm in file_metadata:
            fm.centrality_score = centrality_scores[fm.path] / max_score
    
    def _determine_traversal_order(self, file_metadata: List[FileMetadata], 
                                 goal_hints: Optional[Dict[str, Any]] = None) -> List[str]:
        """Determine the order in which files should be analyzed."""
        # Sort by priority
        def priority_score(fm: FileMetadata) -> Tuple[bool, float, int]:
            # Entry points first
            entry_priority = fm.is_entry_point
            
            # Then by centrality
            centrality = fm.centrality_score
            
            # Then by size (smaller first for early context)
            size_priority = -fm.size_bytes
            
            return (entry_priority, centrality, size_priority)
        
        sorted_files = sorted(file_metadata, key=priority_score, reverse=True)
        return [fm.path for fm in sorted_files]
    
    def _create_chunks(self, file_metadata: List[FileMetadata], repo_root: Path) -> List[ChunkMetadata]:
        """Create chunks from file metadata."""
        chunks = []
        
        for fm in file_metadata:
            file_path = repo_root / fm.path
            
            if fm.size_bytes > self.size_threshold:
                # Large file: split into units
                file_chunks = self._split_large_file(file_path, fm)
                chunks.extend(file_chunks)
            else:
                # Small file: single chunk
                chunk = self._create_file_chunk(file_path, fm)
                chunks.append(chunk)
        
        return chunks
    
    def _split_large_file(self, file_path: Path, file_metadata: FileMetadata) -> List[ChunkMetadata]:
        """Split a large file into AST-aware units."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Skip binary files
            return []
        
        # Try AST parsing first
        if TREE_SITTER_AVAILABLE and file_metadata.lang in ['py', 'js', 'ts']:
            units = self._parse_ast_units(content, file_metadata.lang)
        else:
            # Fallback to regex parsing
            units = self._parse_regex_units(content, file_metadata.lang)
        
        if not units:
            # If parsing fails, treat as single chunk
            return [self._create_file_chunk(file_path, file_metadata)]
        
        # Create chunks for each unit
        chunks = []
        for i, unit in enumerate(units):
            chunk_id = f"{file_metadata.sha256}:{unit['start']}:{unit['end']}"
            
            # Create prelude (imports + constants)
            prelude_content = self._extract_prelude(content, unit['start'])
            
            # Get neighbors
            prev_unit = units[i-1] if i > 0 else None
            next_unit = units[i+1] if i < len(units)-1 else None
            
            chunk = ChunkMetadata(
                chunk_id=chunk_id,
                type="unit",
                path=file_metadata.path,
                lang=file_metadata.lang,
                parent_file_hash=file_metadata.sha256,
                byte_start=unit['start'],
                byte_end=unit['end'],
                prelude={
                    "content": prelude_content,
                    "lines": [0, len(prelude_content.split('\n'))]
                },
                unit={
                    "kind": unit['kind'],
                    "name": unit['name'],
                    "span_lines": [unit['start_line'], unit['end_line']],
                    "content": content[unit['start']:unit['end']]
                },
                neighbors={
                    "prev": prev_unit['name'] if prev_unit else None,
                    "next": next_unit['name'] if next_unit else None
                },
                summary=f"{unit['kind']} {unit['name']}",
                edges={
                    "calls": unit.get('calls', []),
                    "called_by": unit.get('called_by', [])
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def _parse_ast_units(self, content: str, lang: str) -> List[Dict[str, Any]]:
        """Parse file content into AST units using tree-sitter."""
        # This would use tree-sitter for proper AST parsing
        # For now, fall back to regex
        return self._parse_regex_units(content, lang)
    
    def _parse_regex_units(self, content: str, lang: str) -> List[Dict[str, Any]]:
        """Parse file content into units using regex patterns."""
        units = []
        lines = content.split('\n')
        
        if lang == 'py':
            # Python: classes and functions
            for i, line in enumerate(lines):
                if re.match(r'^class\s+\w+', line.strip()):
                    unit = self._extract_python_unit(content, lines, i, 'class')
                    if unit:
                        units.append(unit)
                elif re.match(r'^def\s+\w+', line.strip()):
                    unit = self._extract_python_unit(content, lines, i, 'function')
                    if unit:
                        units.append(unit)
        
        elif lang in ['js', 'ts', 'jsx', 'tsx']:
            # JavaScript/TypeScript: classes and functions
            for i, line in enumerate(lines):
                if re.match(r'^(?:export\s+)?class\s+\w+', line.strip()):
                    unit = self._extract_js_unit(content, lines, i, 'class')
                    if unit:
                        units.append(unit)
                elif re.match(r'^(?:export\s+)?(?:function\s+\w+|const\s+\w+\s*=\s*(?:async\s+)?\s*\()', line.strip()):
                    unit = self._extract_js_unit(content, lines, i, 'function')
                    if unit:
                        units.append(unit)
        
        return units
    
    def _extract_python_unit(self, content: str, lines: List[str], start_line: int, kind: str) -> Optional[Dict[str, Any]]:
        """Extract a Python unit (class or function) with proper indentation handling."""
        # Find the unit name
        line = lines[start_line].strip()
        if kind == 'class':
            match = re.match(r'^class\s+(\w+)', line)
        else:  # function
            match = re.match(r'^def\s+(\w+)', line)
        
        if not match:
            return None
        
        name = match.group(1)
        
        # Find the end of the unit by tracking indentation
        start_indent = len(lines[start_line]) - len(lines[start_line].lstrip())
        end_line = start_line
        
        for i in range(start_line + 1, len(lines)):
            if lines[i].strip() == '':  # Skip empty lines
                continue
            
            current_indent = len(lines[i]) - len(lines[i].lstrip())
            if current_indent <= start_indent:
                end_line = i - 1
                break
        else:
            end_line = len(lines) - 1
        
        # Calculate byte positions
        start_byte = sum(len(line) + 1 for line in lines[:start_line])  # +1 for newline
        end_byte = sum(len(line) + 1 for line in lines[:end_line + 1])
        
        return {
            'kind': kind,
            'name': name,
            'start': start_byte,
            'end': end_byte,
            'start_line': start_line,
            'end_line': end_line,
            'calls': [],  # Would be populated by more sophisticated analysis
            'called_by': []
        }
    
    def _extract_js_unit(self, content: str, lines: List[str], start_line: int, kind: str) -> Optional[Dict[str, Any]]:
        """Extract a JavaScript/TypeScript unit (class or function)."""
        # Similar to Python but with different syntax
        # This is a simplified version - would need more sophisticated parsing for JS
        line = lines[start_line].strip()
        
        if kind == 'class':
            match = re.match(r'^(?:export\s+)?class\s+(\w+)', line)
        else:  # function
            match = re.match(r'^(?:export\s+)?(?:function\s+(\w+)|const\s+(\w+))', line)
        
        if not match:
            return None
        
        name = match.group(1) or match.group(2)
        
        # For JS, we'd need to handle braces properly
        # This is a simplified version
        end_line = start_line
        brace_count = 0
        in_unit = False
        
        for i in range(start_line, len(lines)):
            line_content = lines[i]
            for char in line_content:
                if char == '{':
                    brace_count += 1
                    in_unit = True
                elif char == '}':
                    brace_count -= 1
                    if in_unit and brace_count == 0:
                        end_line = i
                        break
            if in_unit and brace_count == 0:
                break
        
        # Calculate byte positions
        start_byte = sum(len(line) + 1 for line in lines[:start_line])
        end_byte = sum(len(line) + 1 for line in lines[:end_line + 1])
        
        return {
            'kind': kind,
            'name': name,
            'start': start_byte,
            'end': end_byte,
            'start_line': start_line,
            'end_line': end_line,
            'calls': [],
            'called_by': []
        }
    
    def _extract_prelude(self, content: str, unit_start: int) -> str:
        """Extract prelude (imports, constants) for a unit."""
        lines = content[:unit_start].split('\n')
        
        # Take first N lines or until we hit the unit
        prelude_lines = lines[:self.prelude_lines]
        
        # Filter to keep only imports, constants, and comments
        filtered_lines = []
        for line in prelude_lines:
            stripped = line.strip()
            if (stripped.startswith(('import ', 'from ', 'const ', 'let ', 'var ', '//', '#', '/*')) or
                stripped == '' or
                stripped.startswith('package ') or  # Go
                stripped.startswith('use ')):  # Rust
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    def _create_file_chunk(self, file_path: Path, file_metadata: FileMetadata) -> ChunkMetadata:
        """Create a single chunk for a small file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            content = "[Binary file]"
        
        chunk_id = f"{file_metadata.sha256}:0:{len(content)}"
        
        return ChunkMetadata(
            chunk_id=chunk_id,
            type="file",
            path=file_metadata.path,
            lang=file_metadata.lang,
            byte_start=0,
            byte_end=len(content),
            prelude={
                "content": content[:min(len(content), self.prelude_lines * 50)],  # First part of file
                "lines": [0, min(len(content.split('\n')), self.prelude_lines)]
            },
            unit={
                "kind": "file",
                "name": file_path.stem,
                "span_lines": [0, len(content.split('\n'))],
                "content": content
            },
            summary=f"Complete {file_metadata.lang} file: {file_metadata.path}",
            edges={
                "calls": file_metadata.imports,
                "called_by": []
            }
        )
    
    def _calculate_repo_hash(self, repo_path: Path) -> str:
        """Calculate a hash for the repository."""
        # Simple hash based on repo path and some file stats
        hasher = hashlib.sha256()
        hasher.update(str(repo_path).encode())
        return hasher.hexdigest()[:16]
    
    def _count_chunks_by_type(self, chunks: List[ChunkMetadata]) -> Dict[str, int]:
        """Count chunks by type."""
        counts = defaultdict(int)
        for chunk in chunks:
            counts[chunk.type] += 1
        return dict(counts)
