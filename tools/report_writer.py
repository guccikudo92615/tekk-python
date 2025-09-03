"""
ReportWriter tool for outputting security analysis reports.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional


class ReportWriter:
    """Tool for writing security analysis reports to output."""
    
    def __init__(self):
        self.output_path: Optional[Path] = None
    
    def write_to_stdout(self, report: Dict[str, Any], pretty_print: bool = True) -> None:
        """
        Write the report to stdout.
        
        Args:
            report: Security analysis report dictionary
            pretty_print: Whether to format JSON with indentation
        """
        if pretty_print:
            json_output = json.dumps(report, indent=2, ensure_ascii=False)
        else:
            json_output = json.dumps(report, ensure_ascii=False)
        
        print(json_output)
    
    def write_to_file(self, report: Dict[str, Any], output_path: str, pretty_print: bool = True) -> None:
        """
        Write the report to a file.
        
        Args:
            report: Security analysis report dictionary
            output_path: Path to output file
            pretty_print: Whether to format JSON with indentation
        """
        path = Path(output_path)
        
        # Create parent directories if they don't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        
        if pretty_print:
            json_output = json.dumps(report, indent=2, ensure_ascii=False)
        else:
            json_output = json.dumps(report, ensure_ascii=False)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(json_output)
        
        self.output_path = path
    
    def write_report(self, report: Dict[str, Any], output_path: Optional[str] = None, pretty_print: bool = True) -> None:
        """
        Write the report to stdout or file based on output_path.
        
        Args:
            report: Security analysis report dictionary
            output_path: Optional path to output file (if None, writes to stdout)
            pretty_print: Whether to format JSON with indentation
        """
        if output_path:
            self.write_to_file(report, output_path, pretty_print)
        else:
            self.write_to_stdout(report, pretty_print)
    
    def validate_report_structure(self, report: Dict[str, Any]) -> bool:
        """
        Validate that the report has the required structure.
        
        Args:
            report: Security analysis report dictionary
            
        Returns:
            True if structure is valid, False otherwise
        """
        required_keys = ["summary", "findings", "baseline_checklist", "prioritized_actions", "checks_omitted"]
        
        # Check top-level keys
        for key in required_keys:
            if key not in report:
                return False
        
        # Check summary structure
        summary = report.get("summary", {})
        summary_keys = ["risk_overview", "findings_total_count", "missing_controls_count", 
                       "severity_breakdown", "quick_wins_minutes"]
        for key in summary_keys:
            if key not in summary:
                return False
        
        # Check severity breakdown
        severity_breakdown = summary.get("severity_breakdown", {})
        required_severities = ["Critical", "High", "Medium", "Low"]
        for severity in required_severities:
            if severity not in severity_breakdown:
                return False
        
        return True
    
    def get_output_info(self) -> Dict[str, Any]:
        """
        Get information about the output.
        
        Returns:
            Dictionary with output information
        """
        if self.output_path:
            return {
                "output_type": "file",
                "output_path": str(self.output_path),
                "file_size": self.output_path.stat().st_size if self.output_path.exists() else 0
            }
        else:
            return {
                "output_type": "stdout",
                "output_path": None,
                "file_size": None
            }
