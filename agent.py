"""
Main agent orchestrator for the Tekk.coach Minimal Repo Security Analyzer.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add tools directory to path for imports
sys.path.append(str(Path(__file__).parent / "tools"))

from tools.repo_provider import RepoProvider
from tools.llm_scanner import LLMScanner
from tools.guardrails import Guardrails
from tools.report_writer import ReportWriter
from tools.ticket_writer import TicketWriter


class SecurityAnalyzerAgent:
    """Main agent that orchestrates the security analysis workflow."""
    
    def __init__(self):
        self.repo_provider = RepoProvider()
        self.llm_scanner = LLMScanner()
        self.guardrails = Guardrails()
        self.report_writer = ReportWriter()
        self.ticket_writer = TicketWriter()
    
    def analyze_repository(self, 
                          repo_path: str, 
                          stack: str, 
                          cloud: str = "local",
                          output_path: Optional[str] = None,
                          tickets_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform complete security analysis on a repository.
        
        Args:
            repo_path: Path to the repository
            stack: Technology stack description
            cloud: Cloud environment (default: "local")
            output_path: Optional path for report output
            tickets_path: Optional path for tickets output
            
        Returns:
            Dictionary containing analysis results and metadata
            
        Raises:
            ValueError: If repository path is invalid
            Exception: If analysis fails
        """
        try:
            # Step 1: RepoProvider - Validate repository and get context
            print("Step 1: Validating repository...", file=sys.stderr)
            repo_context = self.repo_provider.get_repo_context(repo_path, stack, cloud)
            print(f"Repository validated: {repo_context.root_path}", file=sys.stderr)
            
            # Step 2: LLMScanner - Run security analysis
            print("Step 2: Running LLM security analysis...", file=sys.stderr)
            llm_report = self.llm_scanner.scan_repository(repo_context)
            print(f"LLM analysis completed: {llm_report.get('summary', {}).get('findings_total_count', 0)} findings", file=sys.stderr)
            
            # Step 3: Guardrails - Validate and enhance report
            print("Step 3: Applying guardrails...", file=sys.stderr)
            enhanced_report = self.guardrails.apply_guardrails(repo_context, llm_report)
            print(f"Guardrails applied: {enhanced_report.get('summary', {}).get('findings_total_count', 0)} total findings", file=sys.stderr)
            
            # Step 4: ReportWriter - Output final report
            print("Step 4: Writing security report...", file=sys.stderr)
            self.report_writer.write_report(enhanced_report, output_path)
            
            # Step 5: TicketWriter - Generate Jira-style tickets
            tickets = []
            if tickets_path:
                print("Step 5: Generating Jira tickets...", file=sys.stderr)
                tickets = self.ticket_writer.write_tickets(enhanced_report, tickets_path)
                print(f"Generated {len(tickets)} tickets", file=sys.stderr)
            
            # Return analysis metadata
            return {
                "success": True,
                "repo_context": {
                    "root_path": repo_context.root_path,
                    "commit_ref": repo_context.commit_ref,
                    "stack": repo_context.stack,
                    "cloud": repo_context.cloud
                },
                "analysis_summary": enhanced_report.get("summary", {}),
                "tickets_generated": len(tickets),
                "output_info": self.report_writer.get_output_info()
            }
            
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            raise
        except Exception as e:
            print(f"Unexpected error during analysis: {e}", file=sys.stderr)
            raise
    
    def validate_inputs(self, repo_path: str, stack: str) -> None:
        """
        Validate input parameters.
        
        Args:
            repo_path: Repository path
            stack: Technology stack
            
        Raises:
            ValueError: If inputs are invalid
        """
        if not repo_path:
            raise ValueError("Repository path is required")
        
        if not stack:
            raise ValueError("Technology stack is required")
        
        if not isinstance(repo_path, str):
            raise ValueError("Repository path must be a string")
        
        if not isinstance(stack, str):
            raise ValueError("Technology stack must be a string")


def main():
    """Main entry point for the security analyzer."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Tekk.coach Minimal Repo Security Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m tekksec --repo ./my-repo --stack "Next.js + Express"
  python -m tekksec --repo ./my-repo --stack "React + Node.js" --output report.json
  python -m tekksec --repo ./my-repo --stack "Python + Flask" --tickets tickets.json
        """
    )
    
    parser.add_argument(
        "--repo", 
        required=True,
        help="Local path to repository (required)"
    )
    
    parser.add_argument(
        "--stack", 
        required=True,
        help="Technology stack description (required)"
    )
    
    parser.add_argument(
        "--cloud", 
        default="local",
        help="Cloud environment (default: local)"
    )
    
    parser.add_argument(
        "--output", 
        help="Path for final report JSON output"
    )
    
    parser.add_argument(
        "--tickets", 
        help="Path for Jira-style tickets JSON output"
    )
    
    args = parser.parse_args()
    
    try:
        # Create and run the security analyzer
        agent = SecurityAnalyzerAgent()
        
        # Validate inputs
        agent.validate_inputs(args.repo, args.stack)
        
        # Run analysis
        result = agent.analyze_repository(
            repo_path=args.repo,
            stack=args.stack,
            cloud=args.cloud,
            output_path=args.output,
            tickets_path=args.tickets
        )
        
        # Print success message to stderr (not stdout to avoid interfering with JSON output)
        print("Security analysis completed successfully!", file=sys.stderr)
        print(f"Findings: {result['analysis_summary'].get('findings_total_count', 0)}", file=sys.stderr)
        print(f"Tickets: {result['tickets_generated']}", file=sys.stderr)
        
        # Exit with success code
        sys.exit(0)
        
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
