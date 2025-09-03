"""
Universal Code Graph Generator - Analyzes any repository and creates detailed code graphs.
Inspired by python-code-graph but supports multiple programming languages.
"""

import ast
import json
import re
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import networkx as nx

@dataclass
class FunctionInfo:
    """Information about a function."""
    name: str
    referenced_in: List[str]
    file_name: str
    start_line: int
    length: int
    dependencies: List[str]
    types: List[str]
    calls_to: List[str]
    parameters: List[str] = None
    return_type: str = None
    docstring: str = None

@dataclass
class ClassInfo:
    """Information about a class."""
    name: str
    referenced_in: List[str]
    file_name: str
    start_line: int
    length: int
    dependencies: List[str]
    methods: List[str]
    attributes: List[str]
    base_classes: List[str] = None
    docstring: str = None

@dataclass
class VariableInfo:
    """Information about a variable."""
    name: str
    referenced_in: List[str]
    file_name: str
    start_line: int
    type: str = None
    value: str = None
    scope: str = None  # 'global', 'local', 'class'

@dataclass
class FileInfo:
    """Information about a file."""
    path: str
    types: List[ClassInfo]
    variables: List[VariableInfo]
    functions: List[FunctionInfo]
    dependencies: List[str]
    exports: List[str]
    detailed_dependencies: List[Dict[str, Any]]

@dataclass
class PackageInfo:
    """Information about a package/module."""
    name: str
    files: List[FileInfo]
    dependencies: List[str]
    exports: List[str]

@dataclass
class CodeGraph:
    """Complete code graph structure."""
    name: str
    packages: List[PackageInfo]
    language: str
    total_files: int
    total_functions: int
    total_classes: int
    total_variables: int

class UniversalCodeGraphGenerator:
    """Universal code graph generator for any programming language."""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.language_detectors = {
            'python': self._is_python_file,
            'javascript': self._is_javascript_file,
            'typescript': self._is_typescript_file,
            'java': self._is_java_file,
            'go': self._is_go_file,
            'rust': self._is_rust_file,
            'cpp': self._is_cpp_file,
            'c': self._is_c_file
        }
        self.parsers = {
            'python': self._parse_python_file,
            'javascript': self._parse_javascript_file,
            'typescript': self._parse_typescript_file,
            'java': self._parse_java_file,
            'go': self._parse_go_file,
            'rust': self._parse_rust_file,
            'cpp': self._parse_cpp_file,
            'c': self._parse_c_file
        }
        
    def create_code_graph(self, output_json_path: str = None) -> CodeGraph:
        """Create a comprehensive code graph for the repository."""
        print(f"🔍 Analyzing repository: {self.repo_path}")
        
        # Detect primary language
        primary_language = self._detect_primary_language()
        print(f"📝 Primary language detected: {primary_language}")
        
        # Find all code files
        code_files = self._find_code_files()
        print(f"📁 Found {len(code_files)} code files")
        
        # Group files by package/module structure
        packages = self._group_files_by_package(code_files)
        print(f"📦 Found {len(packages)} packages/modules")
        
        # Analyze each package
        analyzed_packages = []
        total_functions = 0
        total_classes = 0
        total_variables = 0
        
        for package_name, files in packages.items():
            print(f"🔍 Analyzing package: {package_name}")
            package_info = self._analyze_package(package_name, files, primary_language)
            analyzed_packages.append(package_info)
            
            # Count totals
            for file_info in package_info.files:
                total_functions += len(file_info.functions)
                total_classes += len(file_info.types)
                total_variables += len(file_info.variables)
        
        # Create code graph
        code_graph = CodeGraph(
            name=self.repo_path.name,
            packages=analyzed_packages,
            language=primary_language,
            total_files=len(code_files),
            total_functions=total_functions,
            total_classes=total_classes,
            total_variables=total_variables
        )
        
        # Export to JSON if path provided
        if output_json_path:
            self._export_to_json(code_graph, output_json_path)
            print(f"💾 Code graph exported to: {output_json_path}")
        
        print(f"✅ Analysis complete: {total_functions} functions, {total_classes} classes, {total_variables} variables")
        return code_graph
    
    def _detect_primary_language(self) -> str:
        """Detect the primary programming language of the repository."""
        language_counts = defaultdict(int)
        
        for file_path in self.repo_path.rglob('*'):
            if file_path.is_file():
                for lang, detector in self.language_detectors.items():
                    if detector(file_path):
                        language_counts[lang] += 1
        
        if not language_counts:
            return 'unknown'
        
        return max(language_counts.items(), key=lambda x: x[1])[0]
    
    def _find_code_files(self) -> List[Path]:
        """Find all code files in the repository."""
        code_files = []
        
        for file_path in self.repo_path.rglob('*'):
            if file_path.is_file() and not self._should_skip_file(file_path):
                for lang, detector in self.language_detectors.items():
                    if detector(file_path):
                        code_files.append(file_path)
                        break
        
        return code_files
    
    def _group_files_by_package(self, files: List[Path]) -> Dict[str, List[Path]]:
        """Group files by package/module structure."""
        packages = defaultdict(list)
        
        for file_path in files:
            # Determine package name based on directory structure
            relative_path = file_path.relative_to(self.repo_path)
            package_parts = relative_path.parts[:-1]  # Exclude filename
            
            if package_parts:
                package_name = '.'.join(package_parts)
            else:
                package_name = 'root'
            
            packages[package_name].append(file_path)
        
        return dict(packages)
    
    def _analyze_package(self, package_name: str, files: List[Path], language: str) -> PackageInfo:
        """Analyze a package and return detailed information."""
        file_infos = []
        all_dependencies = set()
        all_exports = set()
        
        for file_path in files:
            try:
                file_info = self._analyze_file(file_path, language)
                file_infos.append(file_info)
                all_dependencies.update(file_info.dependencies)
                all_exports.update(file_info.exports)
            except Exception as e:
                print(f"Warning: Could not analyze {file_path}: {e}")
        
        return PackageInfo(
            name=package_name,
            files=file_infos,
            dependencies=list(all_dependencies),
            exports=list(all_exports)
        )
    
    def _analyze_file(self, file_path: Path, language: str) -> FileInfo:
        """Analyze a single file and extract detailed information."""
        if language not in self.parsers:
            return self._create_empty_file_info(file_path)
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            return self.parsers[language](file_path, content)
        except Exception as e:
            print(f"Warning: Could not parse {file_path}: {e}")
            return self._create_empty_file_info(file_path)
    
    def _create_empty_file_info(self, file_path: Path) -> FileInfo:
        """Create empty file info for unsupported files."""
        relative_path = str(file_path.relative_to(self.repo_path))
        return FileInfo(
            path=relative_path,
            types=[],
            variables=[],
            functions=[],
            dependencies=[],
            exports=[],
            detailed_dependencies=[]
        )
    
    # Language detection methods
    def _is_python_file(self, file_path: Path) -> bool:
        return file_path.suffix == '.py'
    
    def _is_javascript_file(self, file_path: Path) -> bool:
        return file_path.suffix == '.js'
    
    def _is_typescript_file(self, file_path: Path) -> bool:
        return file_path.suffix in ['.ts', '.tsx']
    
    def _is_java_file(self, file_path: Path) -> bool:
        return file_path.suffix == '.java'
    
    def _is_go_file(self, file_path: Path) -> bool:
        return file_path.suffix == '.go'
    
    def _is_rust_file(self, file_path: Path) -> bool:
        return file_path.suffix == '.rs'
    
    def _is_cpp_file(self, file_path: Path) -> bool:
        return file_path.suffix in ['.cpp', '.cc', '.cxx', '.hpp']
    
    def _is_c_file(self, file_path: Path) -> bool:
        return file_path.suffix in ['.c', '.h']
    
    # Language-specific parsers
    def _parse_python_file(self, file_path: Path, content: str) -> FileInfo:
        """Parse Python file using AST."""
        try:
            tree = ast.parse(content)
            relative_path = str(file_path.relative_to(self.repo_path))
            
            functions = []
            classes = []
            variables = []
            dependencies = []
            exports = []
            
            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        dependencies.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        dependencies.append(node.module)
            
            # Extract functions, classes, and variables
            for node in tree.body:
                if isinstance(node, ast.FunctionDef):
                    func_info = self._extract_python_function(node, relative_path, content)
                    functions.append(func_info)
                    exports.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    class_info = self._extract_python_class(node, relative_path, content)
                    classes.append(class_info)
                    exports.append(node.name)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            var_info = self._extract_python_variable(target, node, relative_path)
                            variables.append(var_info)
            
            return FileInfo(
                path=relative_path,
                types=classes,
                variables=variables,
                functions=functions,
                dependencies=dependencies,
                exports=exports,
                detailed_dependencies=[{'name': dep, 'type': 'import'} for dep in dependencies]
            )
            
        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
            return self._create_empty_file_info(file_path)
    
    def _extract_python_function(self, node: ast.FunctionDef, file_path: str, content: str) -> FunctionInfo:
        """Extract information from a Python function."""
        lines = content.split('\n')
        start_line = node.lineno
        end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 1
        length = end_line - start_line + 1
        
        # Extract parameters
        parameters = [arg.arg for arg in node.args.args]
        
        # Extract docstring
        docstring = None
        if (node.body and isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Constant) and 
            isinstance(node.body[0].value.value, str)):
            docstring = node.body[0].value.value
        
        # Find function calls
        calls_to = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls_to.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls_to.append(child.func.attr)
        
        return FunctionInfo(
            name=node.name,
            referenced_in=[file_path],
            file_name=Path(file_path).name,
            start_line=start_line,
            length=length,
            dependencies=[],
            types=[],
            calls_to=calls_to,
            parameters=parameters,
            docstring=docstring
        )
    
    def _extract_python_class(self, node: ast.ClassDef, file_path: str, content: str) -> ClassInfo:
        """Extract information from a Python class."""
        lines = content.split('\n')
        start_line = node.lineno
        end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 1
        length = end_line - start_line + 1
        
        # Extract methods and attributes
        methods = []
        attributes = []
        
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(item.name)
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        attributes.append(target.id)
        
        # Extract base classes
        base_classes = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_classes.append(base.id)
        
        # Extract docstring
        docstring = None
        if (node.body and isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Constant) and 
            isinstance(node.body[0].value.value, str)):
            docstring = node.body[0].value.value
        
        return ClassInfo(
            name=node.name,
            referenced_in=[file_path],
            file_name=Path(file_path).name,
            start_line=start_line,
            length=length,
            dependencies=[],
            methods=methods,
            attributes=attributes,
            base_classes=base_classes,
            docstring=docstring
        )
    
    def _extract_python_variable(self, target: ast.Name, node: ast.Assign, file_path: str) -> VariableInfo:
        """Extract information from a Python variable."""
        return VariableInfo(
            name=target.id,
            referenced_in=[file_path],
            file_name=Path(file_path).name,
            start_line=node.lineno,
            scope='global'
        )
    
    def _parse_javascript_file(self, file_path: Path, content: str) -> FileInfo:
        """Parse JavaScript file using regex patterns."""
        relative_path = str(file_path.relative_to(self.repo_path))
        
        functions = []
        classes = []
        variables = []
        dependencies = []
        exports = []
        
        # Extract imports
        import_patterns = [
            r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]",
            r"import\s+['\"]([^'\"]+)['\"]",
            r"require\(['\"]([^'\"]+)['\"]\)"
        ]
        
        for pattern in import_patterns:
            matches = re.findall(pattern, content)
            dependencies.extend(matches)
        
        # Extract functions
        function_pattern = r'function\s+(\w+)\s*\('
        for match in re.finditer(function_pattern, content):
            func_name = match.group(1)
            start_line = content[:match.start()].count('\n') + 1
            
            # Find function end (simplified)
            brace_count = 0
            in_function = False
            end_pos = match.end()
            
            for i, char in enumerate(content[match.end():], match.end()):
                if char == '{':
                    brace_count += 1
                    in_function = True
                elif char == '}':
                    brace_count -= 1
                    if in_function and brace_count == 0:
                        end_pos = i + 1
                        break
            
            end_line = content[:end_pos].count('\n') + 1
            length = end_line - start_line + 1
            
            functions.append(FunctionInfo(
                name=func_name,
                referenced_in=[relative_path],
                file_name=Path(file_path).name,
                start_line=start_line,
                length=length,
                dependencies=[],
                types=[],
                calls_to=[]
            ))
            exports.append(func_name)
        
        # Extract classes
        class_pattern = r'class\s+(\w+)'
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            start_line = content[:match.start()].count('\n') + 1
            
            classes.append(ClassInfo(
                name=class_name,
                referenced_in=[relative_path],
                file_name=Path(file_path).name,
                start_line=start_line,
                length=1,  # Simplified
                dependencies=[],
                methods=[],
                attributes=[]
            ))
            exports.append(class_name)
        
        return FileInfo(
            path=relative_path,
            types=classes,
            variables=variables,
            functions=functions,
            dependencies=dependencies,
            exports=exports,
            detailed_dependencies=[{'name': dep, 'type': 'import'} for dep in dependencies]
        )
    
    def _parse_typescript_file(self, file_path: Path, content: str) -> FileInfo:
        """Parse TypeScript file (similar to JavaScript but with type annotations)."""
        # For now, use JavaScript parser as base
        js_result = self._parse_javascript_file(file_path, content)
        
        # Add TypeScript-specific parsing here
        # This could include interface extraction, type definitions, etc.
        
        return js_result
    
    def _parse_java_file(self, file_path: Path, content: str) -> FileInfo:
        """Parse Java file using regex patterns."""
        relative_path = str(file_path.relative_to(self.repo_path))
        
        functions = []
        classes = []
        variables = []
        dependencies = []
        exports = []
        
        # Extract imports
        import_pattern = r'import\s+([^;]+);'
        matches = re.findall(import_pattern, content)
        dependencies.extend(matches)
        
        # Extract classes
        class_pattern = r'(?:public\s+|private\s+|protected\s+)?class\s+(\w+)'
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            start_line = content[:match.start()].count('\n') + 1
            
            classes.append(ClassInfo(
                name=class_name,
                referenced_in=[relative_path],
                file_name=Path(file_path).name,
                start_line=start_line,
                length=1,  # Simplified
                dependencies=[],
                methods=[],
                attributes=[]
            ))
            exports.append(class_name)
        
        # Extract methods
        method_pattern = r'(?:public\s+|private\s+|protected\s+)?(?:static\s+)?(?:\w+\s+)*(\w+)\s*\([^)]*\)\s*\{'
        for match in re.finditer(method_pattern, content):
            method_name = match.group(1)
            start_line = content[:match.start()].count('\n') + 1
            
            functions.append(FunctionInfo(
                name=method_name,
                referenced_in=[relative_path],
                file_name=Path(file_path).name,
                start_line=start_line,
                length=1,  # Simplified
                dependencies=[],
                types=[],
                calls_to=[]
            ))
        
        return FileInfo(
            path=relative_path,
            types=classes,
            variables=variables,
            functions=functions,
            dependencies=dependencies,
            exports=exports,
            detailed_dependencies=[{'name': dep, 'type': 'import'} for dep in dependencies]
        )
    
    def _parse_go_file(self, file_path: Path, content: str) -> FileInfo:
        """Parse Go file using regex patterns."""
        relative_path = str(file_path.relative_to(self.repo_path))
        
        functions = []
        classes = []  # Go doesn't have classes, but has structs
        variables = []
        dependencies = []
        exports = []
        
        # Extract imports
        import_pattern = r'import\s+["\']([^"\']+)["\']'
        matches = re.findall(import_pattern, content)
        dependencies.extend(matches)
        
        # Extract functions
        func_pattern = r'func\s+(\w+)\s*\('
        for match in re.finditer(func_pattern, content):
            func_name = match.group(1)
            start_line = content[:match.start()].count('\n') + 1
            
            functions.append(FunctionInfo(
                name=func_name,
                referenced_in=[relative_path],
                file_name=Path(file_path).name,
                start_line=start_line,
                length=1,  # Simplified
                dependencies=[],
                types=[],
                calls_to=[]
            ))
            exports.append(func_name)
        
        # Extract structs
        struct_pattern = r'type\s+(\w+)\s+struct'
        for match in re.finditer(struct_pattern, content):
            struct_name = match.group(1)
            start_line = content[:match.start()].count('\n') + 1
            
            classes.append(ClassInfo(
                name=struct_name,
                referenced_in=[relative_path],
                file_name=Path(file_path).name,
                start_line=start_line,
                length=1,  # Simplified
                dependencies=[],
                methods=[],
                attributes=[]
            ))
            exports.append(struct_name)
        
        return FileInfo(
            path=relative_path,
            types=classes,
            variables=variables,
            functions=functions,
            dependencies=dependencies,
            exports=exports,
            detailed_dependencies=[{'name': dep, 'type': 'import'} for dep in dependencies]
        )
    
    def _parse_rust_file(self, file_path: Path, content: str) -> FileInfo:
        """Parse Rust file using regex patterns."""
        relative_path = str(file_path.relative_to(self.repo_path))
        
        functions = []
        classes = []  # Rust has structs and enums
        variables = []
        dependencies = []
        exports = []
        
        # Extract imports
        use_pattern = r'use\s+([^;]+);'
        matches = re.findall(use_pattern, content)
        dependencies.extend(matches)
        
        # Extract functions
        fn_pattern = r'fn\s+(\w+)\s*\('
        for match in re.finditer(fn_pattern, content):
            func_name = match.group(1)
            start_line = content[:match.start()].count('\n') + 1
            
            functions.append(FunctionInfo(
                name=func_name,
                referenced_in=[relative_path],
                file_name=Path(file_path).name,
                start_line=start_line,
                length=1,  # Simplified
                dependencies=[],
                types=[],
                calls_to=[]
            ))
            exports.append(func_name)
        
        # Extract structs
        struct_pattern = r'struct\s+(\w+)'
        for match in re.finditer(struct_pattern, content):
            struct_name = match.group(1)
            start_line = content[:match.start()].count('\n') + 1
            
            classes.append(ClassInfo(
                name=struct_name,
                referenced_in=[relative_path],
                file_name=Path(file_path).name,
                start_line=start_line,
                length=1,  # Simplified
                dependencies=[],
                methods=[],
                attributes=[]
            ))
            exports.append(struct_name)
        
        return FileInfo(
            path=relative_path,
            types=classes,
            variables=variables,
            functions=functions,
            dependencies=dependencies,
            exports=exports,
            detailed_dependencies=[{'name': dep, 'type': 'use'} for dep in dependencies]
        )
    
    def _parse_cpp_file(self, file_path: Path, content: str) -> FileInfo:
        """Parse C++ file using regex patterns."""
        relative_path = str(file_path.relative_to(self.repo_path))
        
        functions = []
        classes = []
        variables = []
        dependencies = []
        exports = []
        
        # Extract includes
        include_pattern = r'#include\s*[<"]([^>"]+)[>"]'
        matches = re.findall(include_pattern, content)
        dependencies.extend(matches)
        
        # Extract classes
        class_pattern = r'class\s+(\w+)'
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            start_line = content[:match.start()].count('\n') + 1
            
            classes.append(ClassInfo(
                name=class_name,
                referenced_in=[relative_path],
                file_name=Path(file_path).name,
                start_line=start_line,
                length=1,  # Simplified
                dependencies=[],
                methods=[],
                attributes=[]
            ))
            exports.append(class_name)
        
        # Extract functions
        func_pattern = r'(?:\w+\s+)*(\w+)\s*\([^)]*\)\s*\{'
        for match in re.finditer(func_pattern, content):
            func_name = match.group(1)
            if func_name not in ['if', 'while', 'for', 'switch']:  # Skip control structures
                start_line = content[:match.start()].count('\n') + 1
                
                functions.append(FunctionInfo(
                    name=func_name,
                    referenced_in=[relative_path],
                    file_name=Path(file_path).name,
                    start_line=start_line,
                    length=1,  # Simplified
                    dependencies=[],
                    types=[],
                    calls_to=[]
                ))
                exports.append(func_name)
        
        return FileInfo(
            path=relative_path,
            types=classes,
            variables=variables,
            functions=functions,
            dependencies=dependencies,
            exports=exports,
            detailed_dependencies=[{'name': dep, 'type': 'include'} for dep in dependencies]
        )
    
    def _parse_c_file(self, file_path: Path, content: str) -> FileInfo:
        """Parse C file using regex patterns."""
        relative_path = str(file_path.relative_to(self.repo_path))
        
        functions = []
        classes = []  # C doesn't have classes
        variables = []
        dependencies = []
        exports = []
        
        # Extract includes
        include_pattern = r'#include\s*[<"]([^>"]+)[>"]'
        matches = re.findall(include_pattern, content)
        dependencies.extend(matches)
        
        # Extract functions
        func_pattern = r'(?:\w+\s+)*(\w+)\s*\([^)]*\)\s*\{'
        for match in re.finditer(func_pattern, content):
            func_name = match.group(1)
            if func_name not in ['if', 'while', 'for', 'switch']:  # Skip control structures
                start_line = content[:match.start()].count('\n') + 1
                
                functions.append(FunctionInfo(
                    name=func_name,
                    referenced_in=[relative_path],
                    file_name=Path(file_path).name,
                    start_line=start_line,
                    length=1,  # Simplified
                    dependencies=[],
                    types=[],
                    calls_to=[]
                ))
                exports.append(func_name)
        
        return FileInfo(
            path=relative_path,
            types=classes,
            variables=variables,
            functions=functions,
            dependencies=dependencies,
            exports=exports,
            detailed_dependencies=[{'name': dep, 'type': 'include'} for dep in dependencies]
        )
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        skip_dirs = {'.git', 'node_modules', '.next', 'dist', 'build', 'target', '__pycache__', 'venv', 'env'}
        return any(skip_dir in file_path.parts for skip_dir in skip_dirs)
    
    def _export_to_json(self, code_graph: CodeGraph, output_path: str):
        """Export code graph to JSON file."""
        # Convert dataclasses to dictionaries
        def convert_to_dict(obj):
            if hasattr(obj, '__dict__'):
                return {k: convert_to_dict(v) for k, v in obj.__dict__.items()}
            elif isinstance(obj, list):
                return [convert_to_dict(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: convert_to_dict(v) for k, v in obj.items()}
            else:
                return obj
        
        graph_dict = convert_to_dict(code_graph)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(graph_dict, f, indent=2, ensure_ascii=False)

# Convenience function similar to python-code-graph
def create_code_graph(directory_path: str, output_json_path: str = None) -> CodeGraph:
    """Create a code graph for any repository (similar to python-code-graph API)."""
    generator = UniversalCodeGraphGenerator(directory_path)
    return generator.create_code_graph(output_json_path)
