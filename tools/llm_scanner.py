"""
Context-Aware LLM Scanner for running security analysis using GPT-4o.
Handles large codebases by spawning sub-agents when context limits are reached.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv
import openai
sys.path.append(str(Path(__file__).parent.parent))
from models.schema import RepoContext
from tools.ast_chunker import ASTChunker

# Load environment variables
load_dotenv()


class LLMScanner:
    """Context-aware LLM scanner for security analysis with sub-agent spawning."""
    
    def __init__(self):
        self.prompt_template = self._load_prompt_template()
        self.client = self._initialize_openai_client()
        self.max_context_tokens = 50000  # Very conservative limit for GPT-4o
        self.analysis_results = []  # Store results from all agents
        
        # Initialize AST-aware chunker with very small limits for GPT-4o
        self.ast_chunker = ASTChunker(
            size_threshold=50_000,  # 50KB - very small for better context management
            token_threshold=10_000,  # ~10k tokens - very small
            prelude_lines=20,  # Very small prelude
            unit_max_tokens=1000  # Very small unit max
        )
    
    def _initialize_openai_client(self):
        """Initialize OpenAI client with API key."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        return openai.OpenAI(api_key=api_key)
    
    def _get_relevant_files(self, repo_path: str) -> List[Dict[str, str]]:
        """
        Get relevant files from the repository for analysis.
        
        Args:
            repo_path: Path to the repository
            
        Returns:
            List of file information dictionaries
        """
        repo_path = Path(repo_path)
        relevant_files = []
        
        # File extensions to analyze
        code_extensions = {'.js', '.ts', '.tsx', '.jsx', '.py', '.java', '.go', '.rs', '.php', '.rb', '.cs', '.cpp', '.c', '.h', '.hpp'}
        config_extensions = {'.json', '.yaml', '.yml', '.toml', '.ini', '.conf', '.config', '.env', '.properties'}
        
        # Directories to skip
        skip_dirs = {'.git', 'node_modules', '.next', 'dist', 'build', 'target', '__pycache__', '.pytest_cache', 'venv', 'env'}
        
        for file_path in repo_path.rglob('*'):
            if file_path.is_file():
                # Skip files in ignored directories
                if any(skip_dir in file_path.parts for skip_dir in skip_dirs):
                    continue
                
                # Check if file is relevant
                if (file_path.suffix.lower() in code_extensions or 
                    file_path.suffix.lower() in config_extensions or
                    file_path.name in {'package.json', 'requirements.txt', 'Dockerfile', 'docker-compose.yml', 'README.md'}):
                    
                    try:
                        # Read file content (limit size to avoid context window issues)
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        
                        # Limit file size to 10KB to manage context window
                        if len(content) > 10000:
                            content = content[:10000] + "\n... [FILE TRUNCATED - TOO LARGE]"
                        
                        relevant_files.append({
                            'path': str(file_path.relative_to(repo_path)),
                            'content': content,
                            'size': len(content)
                        })
                    except Exception as e:
                        print(f"Warning: Could not read file {file_path}: {e}", file=sys.stderr)
        
        return relevant_files
    
    def _create_code_analysis_prompt(self, repo_context: RepoContext, files: List[Dict[str, str]]) -> str:
        """
        Create a comprehensive prompt with actual repository code.
        
        Args:
            repo_context: Repository context
            files: List of relevant files
            
        Returns:
            Formatted prompt with code content
        """
        base_prompt = self.prompt_template.replace("{repo}", repo_context.root_path)
        base_prompt = base_prompt.replace("{stack}", repo_context.stack)
        base_prompt = base_prompt.replace("{cloud}", repo_context.cloud)
        
        # Add code analysis section
        code_section = "\n\n## Repository Code Analysis\n\n"
        code_section += f"Analyze the following {len(files)} files from the repository:\n\n"
        
        for i, file_info in enumerate(files[:20]):  # Limit to first 20 files to manage context
            code_section += f"### File {i+1}: {file_info['path']}\n"
            code_section += f"```\n{file_info['content']}\n```\n\n"
        
        if len(files) > 20:
            code_section += f"... and {len(files) - 20} more files (truncated for context window)\n\n"
        
        code_section += "Based on the actual code above, identify specific security issues and missing controls.\n"
        code_section += "For each finding, provide:\n"
        code_section += "- Exact file paths and line numbers (e.g., 'file.tsx:45-67')\n"
        code_section += "- Function names, component names, or method names where issues exist\n"
        code_section += "- Specific code context and evidence\n"
        code_section += "- API endpoint names, configuration setting names, etc.\n"
        
        return base_prompt + code_section
    
    def _load_prompt_template(self) -> str:
        """Load the security analysis prompt template."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "security_analysis.md"
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Security analysis prompt not found at {prompt_path}")
    
    def _format_prompt(self, repo_context: RepoContext) -> str:
        """
        Format the prompt template with repository context.
        
        Args:
            repo_context: Repository context information
            
        Returns:
            Formatted prompt string
        """
        try:
            # Use string replacement instead of format to avoid issues with curly braces
            prompt = self.prompt_template
            prompt = prompt.replace("{repo}", repo_context.root_path)
            prompt = prompt.replace("{stack}", repo_context.stack)
            prompt = prompt.replace("{cloud}", repo_context.cloud)
            return prompt
        except Exception as e:
            print(f"DEBUG: Prompt formatting error: {e}", file=sys.stderr)
            # Return a simple prompt if formatting fails
            return f"Analyze the repository at {repo_context.root_path} with stack {repo_context.stack} in {repo_context.cloud} environment."
    
    def analyze_repository(self, repo_path: str, output_dir: str = "reports", 
                          goal_hints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main analysis method using AST-aware hierarchical chunking.
        Spawns sub-agents when context limits are reached.
        
        Args:
            repo_path: Path to the repository to analyze
            output_dir: Directory to save analysis results
            goal_hints: Optional hints about what to prioritize
            
        Returns:
            Combined analysis results from all agents
        """
        print(f"🔍 Starting AST-aware security analysis of {repo_path}")
        
        # Use AST chunker to create hierarchical chunks
        chunking_result = self.ast_chunker.chunk_repository(repo_path, goal_hints)
        print(f"📦 Created {chunking_result['chunking_stats']['total_chunks']} chunks from {chunking_result['chunking_stats']['total_files']} files")
        
        # Reset analysis results
        self.analysis_results = []
        
        # Group chunks by context limits
        chunk_groups = self._group_chunks_by_context(chunking_result['chunks'])
        print(f"🔄 Organized into {len(chunk_groups)} analysis groups")
        
        # Process each group with progressive analysis
        print(f"🎯 Processing {len(chunk_groups)} groups with progressive analysis...")
        
        for i, chunk_group in enumerate(chunk_groups):
            print(f"🔄 Processing group {i+1}/{len(chunk_groups)} ({len(chunk_group)} chunks)")
            
            if i == 0:
                # Main agent processes first group
                result = self._analyze_chunk_group(chunk_group, repo_path, is_main_agent=True)
            else:
                # Sub-agent processes remaining groups
                result = self._analyze_chunk_group(chunk_group, repo_path, is_main_agent=False, 
                                                 previous_results=self.analysis_results)
            
            self.analysis_results.append(result)
            
            # If we have too many groups, implement batching strategy
            if len(chunk_groups) > 20:
                # For very large repositories, batch results every 10 groups
                if (i + 1) % 10 == 0:
                    print(f"📦 Batching results after {i+1} groups...")
                    # Could implement intermediate result consolidation here
        
        # Combine all results
        final_report = self._combine_analysis_results(repo_path, chunking_result)
        
        # Save results
        self._save_results(final_report, output_dir)
        
        print(f"✅ Analysis complete! Found {len(final_report.get('findings', []))} total findings")
        return final_report
    
    def _group_chunks_by_context(self, chunks: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Group AST chunks with dynamic sizing and strict context limits."""
        groups = []
        current_group = []
        current_tokens = 0
        
        # Very conservative limits - aim for much smaller groups
        max_tokens_per_group = 15000  # 15k tokens max per group
        max_chunks_per_group = 3      # Max 3 chunks per group
        
        for chunk in chunks:
            # Estimate tokens for this chunk
            chunk_tokens = self._estimate_chunk_tokens(chunk)
            
            # If this single chunk is too big, split it further
            if chunk_tokens > 8000:  # 8k tokens max per chunk
                print(f"⚠️ Chunk too large ({chunk_tokens} tokens), splitting further...")
                # For now, skip very large chunks or handle them specially
                continue
            
            # If adding this chunk would exceed limits, start a new group
            if (current_tokens + chunk_tokens > max_tokens_per_group or 
                len(current_group) >= max_chunks_per_group):
                if current_group:
                    groups.append(current_group)
                    current_group = []
                    current_tokens = 0
            
            current_group.append(chunk)
            current_tokens += chunk_tokens
        
        # Add remaining chunks
        if current_group:
            groups.append(current_group)
        
        print(f"📊 Created {len(groups)} groups with strict limits:")
        print(f"   - Max {max_tokens_per_group} tokens per group")
        print(f"   - Max {max_chunks_per_group} chunks per group")
        print(f"   - Max 8000 tokens per chunk")
        
        return groups
    
    def _estimate_chunk_tokens(self, chunk: Dict[str, Any]) -> int:
        """Estimate token count for a chunk with more accurate calculation."""
        total_tokens = 0
        
        # Add prelude content
        if chunk.get('prelude', {}).get('content'):
            prelude_content = chunk['prelude']['content']
            # More accurate: count words and add overhead
            words = len(prelude_content.split())
            total_tokens += words * 1.3  # ~1.3 tokens per word
        
        # Add unit content
        if chunk.get('unit', {}).get('content'):
            unit_content = chunk['unit']['content']
            words = len(unit_content.split())
            total_tokens += words * 1.3
        
        # Add overhead for JSON structure, prompts, etc.
        total_tokens += 500  # Base overhead
        
        return int(total_tokens)
    
    def _analyze_chunk_group(self, chunk_group: List[Dict[str, Any]], repo_path: str, 
                           is_main_agent: bool = True, previous_results: List[Dict] = None) -> Dict[str, Any]:
        """Analyze a group of AST chunks using LLM."""
        
        # Create context for this chunk group
        repo_context = RepoContext(
            root_path=repo_path,
            stack="detected",
            cloud="detected"
        )
        
        # Create prompt for this chunk group
        if is_main_agent:
            prompt = self._create_main_agent_ast_prompt(chunk_group, repo_context)
        else:
            prompt = self._create_sub_agent_ast_prompt(chunk_group, repo_context, previous_results)
        
        # Run LLM analysis
        try:
            response = self.run_llm(prompt)
            if not response or response.strip() == "":
                print("❌ Empty response from LLM")
                return self._get_fallback_chunk_group_result(chunk_group, is_main_agent)
            
            # Clean response - remove markdown code blocks
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]  # Remove ```json
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]  # Remove ```
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]  # Remove trailing ```
            cleaned_response = cleaned_response.strip()
            
            result = json.loads(cleaned_response)
            if not isinstance(result, dict):
                print("❌ Invalid response format from LLM")
                return self._get_fallback_chunk_group_result(chunk_group, is_main_agent)
            
            result['agent_type'] = 'main' if is_main_agent else 'sub'
            result['chunks_analyzed'] = len(chunk_group)
            return result
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            print(f"Cleaned response was: {cleaned_response[:200]}...")
            return self._get_fallback_chunk_group_result(chunk_group, is_main_agent)
        except Exception as e:
            print(f"❌ Analysis error: {e}")
            return self._get_fallback_chunk_group_result(chunk_group, is_main_agent)
    
    def _create_main_agent_ast_prompt(self, chunk_group: List[Dict[str, Any]], repo_context: RepoContext) -> str:
        """Create prompt for main agent analysis of AST chunks."""
        base_prompt = self._format_prompt(repo_context)
        
        code_section = f"\n\n## AST-Aware Repository Analysis (Main Agent)\n\n"
        code_section += f"Analyze the following {len(chunk_group)} code units organized by AST structure:\n\n"
        
        for i, chunk in enumerate(chunk_group):
            chunk_type = chunk.get('type', 'unknown')
            chunk_path = chunk.get('path', 'unknown')
            chunk_lang = chunk.get('lang', 'unknown')
            
            code_section += f"### Unit {i+1}: {chunk_type.upper()} - {chunk_path}\n"
            code_section += f"*Language: {chunk_lang}*\n\n"
            
            # Add prelude (imports, constants)
            if chunk.get('prelude', {}).get('content'):
                code_section += f"#### Prelude (imports, constants):\n"
                code_section += f"```{chunk_lang}\n{chunk['prelude']['content']}\n```\n\n"
            
            # Add main unit content
            if chunk.get('unit', {}).get('content'):
                unit_info = chunk['unit']
                code_section += f"#### {unit_info.get('kind', 'unit').title()}: {unit_info.get('name', 'unnamed')}\n"
                code_section += f"```{chunk_lang}\n{unit_info['content']}\n```\n\n"
            
            # Add neighbors context
            if chunk.get('neighbors'):
                neighbors = chunk['neighbors']
                if neighbors.get('prev') or neighbors.get('next'):
                    code_section += f"#### Context: "
                    if neighbors.get('prev'):
                        code_section += f"Previous: {neighbors['prev']} "
                    if neighbors.get('next'):
                        code_section += f"Next: {neighbors['next']}"
                    code_section += f"\n\n"
        
        code_section += "Based on the AST-organized code above, identify specific security issues and missing controls.\n"
        code_section += "This is the MAIN analysis - provide comprehensive findings.\n"
        code_section += "Pay attention to how units interact and potential security gaps between them.\n"
        
        return base_prompt + code_section
    
    def _create_sub_agent_ast_prompt(self, chunk_group: List[Dict[str, Any]], repo_context: RepoContext, 
                                   previous_results: List[Dict]) -> str:
        """Create prompt for sub-agent analysis of AST chunks."""
        base_prompt = self._format_prompt(repo_context)
        
        # Include summary of previous findings
        previous_summary = self._summarize_previous_results(previous_results)
        
        code_section = f"\n\n## AST-Aware Repository Analysis (Sub-Agent)\n\n"
        code_section += f"Previous analysis found: {previous_summary}\n\n"
        code_section += f"Now analyze these additional {len(chunk_group)} code units:\n\n"
        
        for i, chunk in enumerate(chunk_group):
            chunk_type = chunk.get('type', 'unknown')
            chunk_path = chunk.get('path', 'unknown')
            chunk_lang = chunk.get('lang', 'unknown')
            
            code_section += f"### Unit {i+1}: {chunk_type.upper()} - {chunk_path}\n"
            code_section += f"*Language: {chunk_lang}*\n\n"
            
            # Add prelude (imports, constants)
            if chunk.get('prelude', {}).get('content'):
                code_section += f"#### Prelude (imports, constants):\n"
                code_section += f"```{chunk_lang}\n{chunk['prelude']['content']}\n```\n\n"
            
            # Add main unit content
            if chunk.get('unit', {}).get('content'):
                unit_info = chunk['unit']
                code_section += f"#### {unit_info.get('kind', 'unit').title()}: {unit_info.get('name', 'unnamed')}\n"
                code_section += f"```{chunk_lang}\n{unit_info['content']}\n```\n\n"
        
        code_section += "Focus on NEW security issues not found in previous analysis.\n"
        code_section += "Avoid duplicating findings from the main agent.\n"
        code_section += "Pay attention to how these units interact with previously analyzed components.\n"
        
        return base_prompt + code_section
    
    def _get_fallback_chunk_group_result(self, chunk_group: List[Dict[str, Any]], is_main_agent: bool) -> Dict[str, Any]:
        """Get fallback result for a chunk group when analysis fails."""
        return {
            "summary": {
                "risk_overview": f"Analysis failed for {len(chunk_group)} chunks",
                "findings_total_count": 0
            },
            "findings": [],
            "agent_type": 'main' if is_main_agent else 'sub',
            "chunks_analyzed": len(chunk_group),
            "error": "Analysis failed"
        }
    
    def _chunk_files_by_context(self, files: List[Dict[str, str]]) -> List[List[Dict[str, str]]]:
        """Organize files into logical chunks based on repository structure."""
        
        # Group files by directory/component structure
        file_groups = self._group_files_by_structure(files)
        
        # Create chunks that respect context limits while keeping related files together
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for group_name, group_files in file_groups.items():
            group_tokens = sum(len(f['content']) // 4 for f in group_files)
            
            # If this group alone exceeds context limit, split it
            if group_tokens > self.max_context_tokens // 2:
                # Split large groups by file type or size
                sub_groups = self._split_large_group(group_files)
                for sub_group in sub_groups:
                    if current_chunk:
                        chunks.append(current_chunk)
                        current_chunk = []
                        current_tokens = 0
                    chunks.append(sub_group)
            else:
                # If adding this group would exceed limits, start a new chunk
                if current_tokens + group_tokens > self.max_context_tokens // 2:
                    if current_chunk:
                        chunks.append(current_chunk)
                        current_chunk = []
                        current_tokens = 0
                
                current_chunk.extend(group_files)
                current_tokens += group_tokens
        
        # Add remaining files
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _group_files_by_structure(self, files: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
        """Group files by logical repository structure (directories, components, etc.)."""
        groups = {}
        
        for file_info in files:
            file_path = file_info['path']
            
            # Determine group based on file path and type
            group_name = self._determine_file_group(file_path, file_info)
            
            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append(file_info)
        
        return groups
    
    def _determine_file_group(self, file_path: str, file_info: Dict[str, str]) -> str:
        """Determine which logical group a file belongs to."""
        path_parts = file_path.split('/')
        
        # Configuration and setup files
        if any(part in ['package.json', 'requirements.txt', 'Dockerfile', 'docker-compose.yml', 
                       'tsconfig.json', 'webpack.config.js', 'vite.config.ts', '.env', '.gitignore'] 
               for part in path_parts):
            return "configuration"
        
        # Source code directories
        if 'src' in path_parts:
            # Group by subdirectory within src
            src_index = path_parts.index('src')
            if src_index + 1 < len(path_parts):
                return f"src_{path_parts[src_index + 1]}"
            return "src_root"
        
        # Components (React/Vue/Angular)
        if 'components' in path_parts:
            return "components"
        
        # API/Backend
        if any(part in ['api', 'backend', 'server', 'routes', 'controllers', 'handlers'] 
               for part in path_parts):
            return "api_backend"
        
        # Database related
        if any(part in ['migrations', 'schema', 'models', 'database', 'db'] 
               for part in path_parts):
            return "database"
        
        # Authentication/Security
        if any(part in ['auth', 'security', 'middleware', 'guards', 'policies'] 
               for part in path_parts):
            return "auth_security"
        
        # Supabase specific
        if 'supabase' in path_parts:
            if 'functions' in path_parts:
                return "supabase_functions"
            return "supabase_config"
        
        # Tests
        if any(part in ['test', 'tests', '__tests__', 'spec'] 
               for part in path_parts):
            return "tests"
        
        # Documentation
        if any(part in ['docs', 'documentation', 'README'] 
               for part in path_parts) or file_path.endswith('.md'):
            return "documentation"
        
        # Utilities and helpers
        if any(part in ['utils', 'helpers', 'lib', 'common', 'shared'] 
               for part in path_parts):
            return "utilities"
        
        # Root level files
        if len(path_parts) == 1:
            return "root_files"
        
        # Default: group by top-level directory
        return path_parts[0] if path_parts else "unknown"
    
    def _split_large_group(self, files: List[Dict[str, str]]) -> List[List[Dict[str, str]]]:
        """Split a large group of files into smaller chunks while maintaining logical structure."""
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        # Sort files by size (smaller first) to optimize chunking
        sorted_files = sorted(files, key=lambda f: len(f['content']))
        
        for file_info in sorted_files:
            file_tokens = len(file_info['content']) // 4
            
            # If this file alone is too large, put it in its own chunk
            if file_tokens > self.max_context_tokens // 3:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = []
                    current_tokens = 0
                chunks.append([file_info])
            else:
                # If adding this file would exceed limits, start a new chunk
                if current_tokens + file_tokens > self.max_context_tokens // 2:
                    if current_chunk:
                        chunks.append(current_chunk)
                        current_chunk = []
                        current_tokens = 0
                
                current_chunk.append(file_info)
                current_tokens += file_tokens
        
        # Add remaining files
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _analyze_chunk(self, files: List[Dict[str, str]], repo_path: str, 
                      is_main_agent: bool = True, previous_results: List[Dict] = None) -> Dict[str, Any]:
        """Analyze a chunk of files using LLM."""
        
        # Create context for this chunk
        repo_context = RepoContext(
            root_path=repo_path,
            stack="detected",
            cloud="detected"
        )
        
        # Create prompt for this chunk
        if is_main_agent:
            prompt = self._create_main_agent_prompt(files, repo_context)
        else:
            prompt = self._create_sub_agent_prompt(files, repo_context, previous_results)
        
        # Run LLM analysis
        try:
            response = self.run_llm(prompt)
            result = json.loads(response)
            result['agent_type'] = 'main' if is_main_agent else 'sub'
            result['files_analyzed'] = len(files)
            return result
        except Exception as e:
            print(f"❌ Analysis error: {e}")
            return self._get_fallback_chunk_result(files, is_main_agent)
    
    def _create_main_agent_prompt(self, files: List[Dict[str, str]], repo_context: RepoContext) -> str:
        """Create prompt for main agent analysis."""
        base_prompt = self._format_prompt(repo_context)
        
        # Group files by their logical structure for better context
        file_groups = self._group_files_by_structure(files)
        
        code_section = f"\n\n## Repository Code Analysis (Main Agent)\n\n"
        code_section += f"Analyze the following {len(files)} files organized by logical repository structure:\n\n"
        
        for group_name, group_files in file_groups.items():
            code_section += f"### {group_name.replace('_', ' ').title()} Component ({len(group_files)} files)\n"
            code_section += f"*This group contains related files that work together*\n\n"
            
            for file_info in group_files:
                code_section += f"#### {file_info['path']}\n"
                code_section += f"```\n{file_info['content']}\n```\n\n"
        
        code_section += "Based on the actual code above, identify specific security issues and missing controls.\n"
        code_section += "This is the MAIN analysis - provide comprehensive findings.\n"
        code_section += "Pay attention to how components interact and potential security gaps between them.\n"
        
        return base_prompt + code_section
    
    def _create_sub_agent_prompt(self, files: List[Dict[str, str]], repo_context: RepoContext, 
                                previous_results: List[Dict]) -> str:
        """Create prompt for sub-agent analysis."""
        base_prompt = self._format_prompt(repo_context)
        
        # Include summary of previous findings
        previous_summary = self._summarize_previous_results(previous_results)
        
        # Group files by their logical structure for better context
        file_groups = self._group_files_by_structure(files)
        
        code_section = f"\n\n## Repository Code Analysis (Sub-Agent)\n\n"
        code_section += f"Previous analysis found: {previous_summary}\n\n"
        code_section += f"Now analyze these additional {len(files)} files organized by logical repository structure:\n\n"
        
        for group_name, group_files in file_groups.items():
            code_section += f"### {group_name.replace('_', ' ').title()} Component ({len(group_files)} files)\n"
            code_section += f"*This group contains related files that work together*\n\n"
            
            for file_info in group_files:
                code_section += f"#### {file_info['path']}\n"
                code_section += f"```\n{file_info['content']}\n```\n\n"
        
        code_section += "Focus on NEW security issues not found in previous analysis.\n"
        code_section += "Avoid duplicating findings from the main agent.\n"
        code_section += "Pay attention to how these components interact with previously analyzed components.\n"
        
        return base_prompt + code_section
    
    def _summarize_previous_results(self, previous_results: List[Dict]) -> str:
        """Create a summary of previous analysis results."""
        if not previous_results:
            return "No previous findings"
        
        total_findings = sum(len(result.get('findings', [])) for result in previous_results)
        return f"{total_findings} findings from {len(previous_results)} previous analysis chunks"
    
    def _combine_analysis_results(self, repo_path: str, chunking_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Combine results from all agents into final report."""
        if not self.analysis_results:
            return self._get_fallback_response()
        
        # Combine findings from all agents
        all_findings = []
        total_files = 0
        
        for result in self.analysis_results:
            all_findings.extend(result.get('findings', []))
            total_files += result.get('files_analyzed', 0)
        
        # Create combined summary
        combined_summary = {
            "risk_overview": f"Comprehensive security analysis of {repo_path} using {len(self.analysis_results)} analysis agents",
            "findings_total_count": len(all_findings),
            "files_analyzed": total_files,
            "agents_used": len(self.analysis_results),
            "severity_breakdown": self._calculate_severity_breakdown(all_findings)
        }
        
        return {
            "summary": combined_summary,
            "findings": all_findings,
            "analysis_metadata": {
                "total_agents": len(self.analysis_results),
                "total_files": total_files,
                "context_management": "enabled"
            }
        }
    
    def _calculate_severity_breakdown(self, findings: List[Dict]) -> Dict[str, int]:
        """Calculate severity breakdown from findings."""
        breakdown = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        for finding in findings:
            severity = finding.get('severity', 'Low')
            if severity in breakdown:
                breakdown[severity] += 1
        return breakdown
    
    def _save_results(self, report: Dict[str, Any], output_dir: str):
        """Save analysis results to files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save main report
        report_file = output_path / "security-analysis-report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"💾 Results saved to {report_file}")
    
    def _get_fallback_chunk_result(self, files: List[Dict[str, str]], is_main_agent: bool) -> Dict[str, Any]:
        """Get fallback result for a chunk when analysis fails."""
        return {
            "summary": {
                "risk_overview": f"Analysis failed for {len(files)} files",
                "findings_total_count": 0
            },
            "findings": [],
            "agent_type": 'main' if is_main_agent else 'sub',
            "files_analyzed": len(files),
            "error": "Analysis failed"
        }

    def run_llm(self, prompt: str) -> str:
        """
        Run the LLM with the given prompt using GPT-4o.
        
        Args:
            prompt: The formatted prompt to send to the LLM
            
        Returns:
            JSON string response from the LLM
        """
        try:
            # Use GPT-4o for better performance and larger context
            model = "gpt-4o"
            temperature = 0.1
            
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior security engineer conducting comprehensive security analysis. For each finding, provide detailed context including function names, component names, exact line numbers, and code snippets. Return ONLY valid JSON matching the specified schema. No additional text or explanations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=8000  # Increased for more detailed analysis
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"OpenAI API error: {e}", file=sys.stderr)
            # Return a fallback response if API fails
            return json.dumps(self._get_fallback_response())
    
    def _get_fallback_response(self) -> str:
        """Get a fallback response when OpenAI API fails."""
        fallback_response = {
            "summary": {
                "risk_overview": "Security analysis failed - OpenAI API unavailable. Manual review recommended.",
                "findings_total_count": 0,
                "missing_controls_count": 0,
                "severity_breakdown": {"Critical": 0, "High": 0, "Medium": 0, "Low": 0},
                "quick_wins_minutes": 0
            },
            "findings": [],
            "baseline_checklist": [],
            "prioritized_actions": [],
            "checks_omitted": ["LLM analysis failed - OpenAI API unavailable"]
        }
        return json.dumps(fallback_response)
    
    def scan_repository(self, repo_context: RepoContext) -> Dict[str, Any]:
        """
        Perform security analysis on the repository.
        
        Args:
            repo_context: Repository context information
            
        Returns:
            Dictionary containing the security analysis results
        """
        print("🔍 Scanning repository files...", file=sys.stderr)
        
        # Get relevant files from the repository
        relevant_files = self._get_relevant_files(repo_context.root_path)
        print(f"📁 Found {len(relevant_files)} relevant files to analyze", file=sys.stderr)
        
        # Create comprehensive prompt with actual code
        formatted_prompt = self._create_code_analysis_prompt(repo_context, relevant_files)
        
        print(f"📝 Created prompt with {len(formatted_prompt)} characters", file=sys.stderr)
        print(f"📊 Analyzing {min(len(relevant_files), 20)} files in detail", file=sys.stderr)
        
        # Run the LLM analysis
        llm_response = self.run_llm(formatted_prompt)
        
        # Debug: print the response type and content
        print(f"DEBUG: llm_response type: {type(llm_response)}", file=sys.stderr)
        print(f"DEBUG: llm_response content: {str(llm_response)[:200]}...", file=sys.stderr)
        
        # Parse the JSON response
        try:
            # If llm_response is already a dict, return it directly
            if isinstance(llm_response, dict):
                return llm_response
            
            # Clean the response - remove markdown code blocks if present
            cleaned_response = llm_response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]  # Remove ```json
            if cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]   # Remove ```
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]  # Remove trailing ```
            cleaned_response = cleaned_response.strip()
            
            # Parse as JSON
            return json.loads(cleaned_response)
            
        except (json.JSONDecodeError, TypeError) as e:
            print(f"JSON parsing error: {e}", file=sys.stderr)
            print(f"Raw response: {llm_response[:500]}...", file=sys.stderr)
            # If LLM returns invalid JSON, return a minimal valid structure
            return {
                "summary": {
                    "risk_overview": "LLM analysis failed - invalid JSON response",
                    "findings_total_count": 0,
                    "missing_controls_count": 0,
                    "severity_breakdown": {"Critical": 0, "High": 0, "Medium": 0, "Low": 0},
                    "quick_wins_minutes": 0
                },
                "findings": [],
                "baseline_checklist": [],
                "prioritized_actions": [],
                "checks_omitted": [f"LLM analysis failed: {str(e)}"]
            }
