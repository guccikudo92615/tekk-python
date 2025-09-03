"""
Semantic Module Graph Chunker - Groups code by semantic relationships and dependencies.
"""

import ast
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict, Counter
import networkx as nx

@dataclass
class ModuleType:
    """Module type classification."""
    category: str  # 'frontend', 'backend', 'config', 'utility', 'test'
    subcategory: str  # 'component', 'api', 'service', 'hook', etc.
    confidence: float  # 0.0 to 1.0

@dataclass
class CodeModule:
    """Represents a semantic code module."""
    name: str
    files: List[str]
    module_type: ModuleType
    dependencies: List[str]
    dependents: List[str]
    size: int
    description: str
    entry_points: List[str]  # Main files that define this module

class SemanticChunker:
    """Intelligent chunking based on semantic relationships and code structure."""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.graph = nx.DiGraph()
        self.modules: Dict[str, CodeModule] = {}
        self.module_patterns = self._load_module_patterns()
        
    def _load_module_patterns(self) -> Dict[str, Dict]:
        """Load module classification patterns for different code types."""
        return {
            'frontend_component': {
                'keywords': ['component', 'ui', 'render', 'jsx', 'tsx', 'react', 'vue', 'angular'],
                'file_patterns': ['components', 'ui', 'views', 'pages'],
                'file_extensions': ['.tsx', '.jsx', '.vue', '.svelte'],
                'category': 'frontend',
                'subcategory': 'component',
                'confidence': 0.9
            },
            'frontend_hook': {
                'keywords': ['use', 'hook', 'state', 'effect', 'context'],
                'file_patterns': ['hooks', 'utils'],
                'file_extensions': ['.ts', '.js'],
                'category': 'frontend',
                'subcategory': 'hook',
                'confidence': 0.8
            },
            'backend_api': {
                'keywords': ['api', 'endpoint', 'route', 'controller', 'handler', 'request', 'response'],
                'file_patterns': ['api', 'routes', 'controllers', 'handlers', 'endpoints'],
                'file_extensions': ['.ts', '.js', '.py', '.java', '.go'],
                'category': 'backend',
                'subcategory': 'api',
                'confidence': 0.9
            },
            'backend_service': {
                'keywords': ['service', 'business', 'logic', 'domain', 'repository'],
                'file_patterns': ['services', 'business', 'domain', 'repositories'],
                'file_extensions': ['.ts', '.js', '.py', '.java', '.go'],
                'category': 'backend',
                'subcategory': 'service',
                'confidence': 0.8
            },
            'data_model': {
                'keywords': ['model', 'schema', 'entity', 'type', 'interface', 'class'],
                'file_patterns': ['models', 'schemas', 'entities', 'types'],
                'file_extensions': ['.ts', '.js', '.py', '.java', '.go'],
                'category': 'backend',
                'subcategory': 'model',
                'confidence': 0.9
            },
            'config': {
                'keywords': ['config', 'settings', 'env', 'environment', 'setup'],
                'file_patterns': ['config', 'settings', 'env'],
                'file_extensions': ['.json', '.yaml', '.yml', '.toml', '.env', '.js', '.ts'],
                'category': 'config',
                'subcategory': 'settings',
                'confidence': 0.9
            },
            'utility': {
                'keywords': ['util', 'helper', 'common', 'shared', 'lib', 'tool'],
                'file_patterns': ['utils', 'lib', 'helpers', 'common', 'shared'],
                'file_extensions': ['.ts', '.js', '.py', '.java', '.go'],
                'category': 'utility',
                'subcategory': 'helper',
                'confidence': 0.7
            },
            'test': {
                'keywords': ['test', 'spec', 'mock', 'stub', 'fixture'],
                'file_patterns': ['test', 'tests', '__tests__', 'spec'],
                'file_extensions': ['.test.ts', '.test.js', '.spec.ts', '.spec.js'],
                'category': 'test',
                'subcategory': 'unit',
                'confidence': 0.9
            }
        }
    
    def analyze_repository(self) -> List[CodeModule]:
        """Analyze repository and create semantic modules."""
        print("🔍 Building semantic dependency graph...")
        
        # Step 1: Build file dependency graph
        self._build_dependency_graph()
        
        # Step 2: Identify semantic modules
        self._identify_semantic_modules()
        
        # Step 3: Classify module types
        self._classify_module_types()
        
        # Step 4: Optimize module sizes for LLM context
        self._optimize_module_sizes()
        
        return list(self.modules.values())
    
    def _build_dependency_graph(self):
        """Build a graph of file dependencies."""
        # Find all code files with different extensions
        extensions = ['*.ts', '*.tsx', '*.js', '*.jsx', '*.py', '*.java', '*.go', '*.rs']
        all_files = []
        for ext in extensions:
            all_files.extend(self.repo_path.rglob(ext))
        
        for file_path in all_files:
            if self._should_skip_file(file_path):
                continue
                
            relative_path = str(file_path.relative_to(self.repo_path))
            self.graph.add_node(relative_path)
            
            # Parse imports/dependencies
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                imports = self._extract_imports(content, file_path.suffix)
                
                for import_path in imports:
                    if import_path and not import_path.startswith(('http', 'https')):
                        self.graph.add_edge(relative_path, import_path)
                        
            except Exception as e:
                print(f"Warning: Could not parse {file_path}: {e}")
    
    def _extract_imports(self, content: str, file_ext: str) -> List[str]:
        """Extract import statements from file content."""
        imports = []
        
        if file_ext in ['.ts', '.tsx', '.js', '.jsx']:
            # JavaScript/TypeScript imports
            patterns = [
                r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]",
                r"import\s+['\"]([^'\"]+)['\"]",
                r"require\(['\"]([^'\"]+)['\"]\)"
            ]
        elif file_ext == '.py':
            # Python imports
            patterns = [
                r"import\s+([a-zA-Z_][a-zA-Z0-9_]*)",
                r"from\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+import"
            ]
        else:
            return imports
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            imports.extend(matches)
        
        return imports
    
    def _identify_semantic_modules(self):
        """Identify semantic modules using connected components and heuristics."""
        # Find strongly connected components
        sccs = list(nx.strongly_connected_components(self.graph))
        
        for i, scc in enumerate(sccs):
            if len(scc) < 2:  # Skip single-file components
                continue
                
            module_name = f"module_{i+1}"
            self.modules[module_name] = CodeModule(
                name=module_name,
                files=list(scc),
                module_type=ModuleType('unknown', 'component', 0.5),
                dependencies=[],
                dependents=[],
                size=sum(self._get_file_size(f) for f in scc),
                description=f"Connected component with {len(scc)} files",
                entry_points=list(scc)  # All files are potential entry points
            )
        
        # Group remaining files by directory structure and semantic patterns
        self._group_by_semantic_patterns()
    
    def _group_by_semantic_patterns(self):
        """Group files by semantic patterns and directory structure."""
        ungrouped_files = set(self.graph.nodes()) - set(
            file for module in self.modules.values() for file in module.files
        )
        
        # Group by directory and semantic similarity
        directory_groups = defaultdict(list)
        for file_path in ungrouped_files:
            dir_path = str(Path(file_path).parent)
            directory_groups[dir_path].append(file_path)
        
        for dir_path, files in directory_groups.items():
            if len(files) > 1:
                module_name = f"dir_{dir_path.replace('/', '_').replace('.', '_')}"
                self.modules[module_name] = CodeModule(
                    name=module_name,
                    files=files,
                    module_type=ModuleType('unknown', 'directory', 0.5),
                    dependencies=[],
                    dependents=[],
                    size=sum(self._get_file_size(f) for f in files),
                    description=f"Directory-based module: {dir_path}",
                    entry_points=files  # All files are potential entry points
                )
    
    def _classify_module_types(self):
        """Classify module types based on content and structure."""
        for module_name, module in self.modules.items():
            best_match = None
            best_confidence = 0.0
            
            for pattern_name, pattern in self.module_patterns.items():
                confidence = self._calculate_module_type_confidence(module, pattern)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = pattern
            
            if best_match:
                module.module_type = ModuleType(
                    category=best_match['category'],
                    subcategory=best_match['subcategory'],
                    confidence=best_confidence
                )
            else:
                # Default classification
                module.module_type = ModuleType('unknown', 'mixed', 0.3)
    
    def _calculate_module_type_confidence(self, module: CodeModule, pattern: Dict) -> float:
        """Calculate confidence score for module type classification."""
        confidence = 0.0
        total_files = len(module.files)
        
        if total_files == 0:
            return 0.0
        
        # Check file extensions
        extension_matches = 0
        for file_path in module.files:
            file_ext = Path(file_path).suffix.lower()
            if file_ext in pattern['file_extensions']:
                extension_matches += 1
        
        if extension_matches > 0:
            confidence += (extension_matches / total_files) * 0.4
        
        # Check file path patterns
        path_matches = 0
        for file_path in module.files:
            file_lower = file_path.lower()
            if any(pattern_name in file_lower for pattern_name in pattern['file_patterns']):
                path_matches += 1
        
        if path_matches > 0:
            confidence += (path_matches / total_files) * 0.3
        
        # Check content keywords
        content_matches = 0
        for file_path in module.files:
            try:
                full_path = self.repo_path / file_path
                if full_path.exists():
                    content = full_path.read_text(encoding='utf-8', errors='ignore')
                    content_lower = content.lower()
                    if any(keyword in content_lower for keyword in pattern['keywords']):
                        content_matches += 1
            except:
                pass
        
        if content_matches > 0:
            confidence += (content_matches / total_files) * 0.3
        
        return min(1.0, confidence)
    
    def _optimize_module_sizes(self):
        """Optimize module sizes for LLM context window."""
        max_size = 50000  # 50KB per module
        optimized_modules = {}
        
        for module_name, module in self.modules.items():
            if module.size <= max_size:
                optimized_modules[module_name] = module
            else:
                # Split large modules
                split_modules = self._split_large_module(module, max_size)
                optimized_modules.update(split_modules)
        
        self.modules = optimized_modules
    
    def _split_large_module(self, module: CodeModule, max_size: int) -> Dict[str, CodeModule]:
        """Split a large module into smaller ones."""
        split_modules = {}
        current_files = []
        current_size = 0
        module_count = 1
        
        for file_path in module.files:
            file_size = self._get_file_size(file_path)
            
            if current_size + file_size > max_size and current_files:
                # Create new module
                new_module_name = f"{module.name}_part_{module_count}"
                split_modules[new_module_name] = CodeModule(
                    name=new_module_name,
                    files=current_files.copy(),
                    module_type=module.module_type,
                    dependencies=module.dependencies,
                    dependents=module.dependents,
                    size=current_size,
                    description=f"{module.description} (part {module_count})",
                    entry_points=current_files.copy()
                )
                current_files = []
                current_size = 0
                module_count += 1
            
            current_files.append(file_path)
            current_size += file_size
        
        # Add remaining files
        if current_files:
            new_module_name = f"{module.name}_part_{module_count}"
            split_modules[new_module_name] = CodeModule(
                name=new_module_name,
                files=current_files,
                module_type=module.module_type,
                dependencies=module.dependencies,
                dependents=module.dependents,
                size=current_size,
                description=f"{module.description} (part {module_count})",
                entry_points=current_files
            )
        
        return split_modules
    
    def _get_file_size(self, file_path: str) -> int:
        """Get file size in characters."""
        try:
            full_path = self.repo_path / file_path
            if full_path.exists():
                return len(full_path.read_text(encoding='utf-8', errors='ignore'))
        except:
            pass
        return 0
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        skip_dirs = {'.git', 'node_modules', '.next', 'dist', 'build', 'target', '__pycache__'}
        return any(skip_dir in file_path.parts for skip_dir in skip_dirs)
    
    def get_prioritized_chunks(self) -> List[Tuple[str, CodeModule]]:
        """Get modules prioritized by type importance and size."""
        # Priority order: frontend components, backend APIs, config, utilities, tests
        type_priority = {
            'frontend': 1,
            'backend': 2,
            'config': 3,
            'utility': 4,
            'test': 5,
            'unknown': 6
        }
        
        return sorted(
            self.modules.items(),
            key=lambda x: (
                type_priority.get(x[1].module_type.category, 6),
                x[1].module_type.confidence,
                x[1].size
            )
        )
    
    def export_graph(self, output_path: str):
        """Export the dependency graph for visualization."""
        graph_data = {
            'nodes': [
                {
                    'id': node,
                    'group': self._get_node_type(node),
                    'size': self._get_file_size(node),
                    'type': self._get_node_type(node)
                }
                for node in self.graph.nodes()
            ],
            'links': [
                {'source': edge[0], 'target': edge[1]}
                for edge in self.graph.edges()
            ],
            'modules': [
                {
                    'name': module.name,
                    'type': f"{module.module_type.category}_{module.module_type.subcategory}",
                    'confidence': module.module_type.confidence,
                    'files': module.files,
                    'size': module.size,
                    'description': module.description
                }
                for module in self.modules.values()
            ]
        }
        
        with open(output_path, 'w') as f:
            json.dump(graph_data, f, indent=2)
    
    def _get_node_type(self, node: str) -> str:
        """Get the type of a node for visualization."""
        # Find which module this node belongs to
        for module in self.modules.values():
            if node in module.files:
                return f"{module.module_type.category}_{module.module_type.subcategory}"
        return "unknown"
    
    def get_repository_insights(self) -> Dict:
        """Get insights about the repository structure."""
        total_files = len(self.graph.nodes())
        total_modules = len(self.modules)
        
        # Module type distribution
        type_distribution = Counter(module.module_type.category for module in self.modules.values())
        subcategory_distribution = Counter(f"{module.module_type.category}_{module.module_type.subcategory}" for module in self.modules.values())
        
        # Size distribution
        size_ranges = {
            'small': len([m for m in self.modules.values() if m.size < 10000]),
            'medium': len([m for m in self.modules.values() if 10000 <= m.size < 50000]),
            'large': len([m for m in self.modules.values() if m.size >= 50000])
        }
        
        # Dependency analysis
        dependency_stats = {
            'avg_dependencies': sum(len(module.dependencies) for module in self.modules.values()) / max(total_modules, 1),
            'max_dependencies': max((len(module.dependencies) for module in self.modules.values()), default=0),
            'isolated_modules': len([m for m in self.modules.values() if len(m.dependencies) == 0])
        }
        
        # Technology stack detection
        tech_stack = self._detect_technology_stack()
        
        return {
            'total_files': total_files,
            'total_modules': total_modules,
            'type_distribution': dict(type_distribution),
            'subcategory_distribution': dict(subcategory_distribution),
            'size_distribution': size_ranges,
            'dependency_stats': dependency_stats,
            'technology_stack': tech_stack,
            'graph_metrics': {
                'nodes': len(self.graph.nodes()),
                'edges': len(self.graph.edges()),
                'density': nx.density(self.graph),
                'strongly_connected_components': len(list(nx.strongly_connected_components(self.graph)))
            }
        }
    
    def _detect_technology_stack(self) -> Dict[str, bool]:
        """Detect the technology stack used in the repository."""
        tech_stack = {
            'react': False,
            'vue': False,
            'angular': False,
            'node': False,
            'python': False,
            'java': False,
            'go': False,
            'rust': False,
            'typescript': False,
            'javascript': False
        }
        
        # Check file extensions
        all_files = list(self.graph.nodes())
        extensions = Counter(Path(f).suffix.lower() for f in all_files)
        
        if extensions.get('.tsx', 0) > 0 or extensions.get('.ts', 0) > 0:
            tech_stack['typescript'] = True
        if extensions.get('.jsx', 0) > 0 or extensions.get('.js', 0) > 0:
            tech_stack['javascript'] = True
        if extensions.get('.py', 0) > 0:
            tech_stack['python'] = True
        if extensions.get('.java', 0) > 0:
            tech_stack['java'] = True
        if extensions.get('.go', 0) > 0:
            tech_stack['go'] = True
        if extensions.get('.rs', 0) > 0:
            tech_stack['rust'] = True
        
        # Check for framework-specific patterns
        for module in self.modules.values():
            for file_path in module.files:
                try:
                    full_path = self.repo_path / file_path
                    if full_path.exists():
                        content = full_path.read_text(encoding='utf-8', errors='ignore')
                        content_lower = content.lower()
                        
                        if 'react' in content_lower or 'jsx' in content_lower:
                            tech_stack['react'] = True
                        if 'vue' in content_lower:
                            tech_stack['vue'] = True
                        if 'angular' in content_lower:
                            tech_stack['angular'] = True
                        if 'express' in content_lower or 'fastify' in content_lower:
                            tech_stack['node'] = True
                except:
                    pass
        
        return tech_stack
