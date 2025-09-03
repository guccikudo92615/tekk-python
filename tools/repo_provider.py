"""
RepoProvider tool for validating and providing repository context.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from models.schema import RepoContext


class RepoProvider:
    """Tool for validating local repository paths and extracting context."""
    
    def __init__(self):
        self.repo_path: Optional[Path] = None
        self.commit_ref: Optional[str] = None
    
    def validate_repo_path(self, repo_path: str) -> Path:
        """
        Validate that the provided path is a valid local repository.
        
        Args:
            repo_path: Path to the repository
            
        Returns:
            Path object for the validated repository
            
        Raises:
            ValueError: If the path is invalid or not a repository
        """
        path = Path(repo_path).resolve()
        
        if not path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")
        
        if not path.is_dir():
            raise ValueError(f"Repository path is not a directory: {repo_path}")
        
        # Check if it's a git repository
        git_dir = path / ".git"
        if not git_dir.exists():
            raise ValueError(f"Path is not a git repository: {repo_path}")
        
        self.repo_path = path
        return path
    
    def get_commit_ref(self) -> Optional[str]:
        """
        Get the current commit reference if available.
        
        Returns:
            Current commit hash or None if not available
        """
        if not self.repo_path:
            return None
        
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                self.commit_ref = result.stdout.strip()
                return self.commit_ref
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            # Git not available or other error
            pass
        
        return None
    
    def get_repo_context(self, repo_path: str, stack: str, cloud: str = "local") -> RepoContext:
        """
        Get complete repository context.
        
        Args:
            repo_path: Path to the repository
            stack: Technology stack description
            cloud: Cloud environment (default: "local")
            
        Returns:
            RepoContext object with all repository information
            
        Raises:
            ValueError: If the repository path is invalid
        """
        validated_path = self.validate_repo_path(repo_path)
        commit_ref = self.get_commit_ref()
        
        return RepoContext(
            root_path=str(validated_path),
            commit_ref=commit_ref,
            stack=stack,
            cloud=cloud
        )
