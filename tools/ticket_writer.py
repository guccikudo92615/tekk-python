"""
TicketWriter tool for converting security findings into Jira-style tickets.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional


class TicketWriter:
    """Tool for converting security findings into Jira-style tickets."""
    
    def __init__(self):
        self.tickets: List[Dict[str, Any]] = []
    
    def _map_severity_to_priority(self, severity: str) -> str:
        """
        Map severity to Jira priority.
        
        Args:
            severity: Security finding severity
            
        Returns:
            Jira priority level
        """
        mapping = {
            "Critical": "P1",
            "High": "P2", 
            "Medium": "P3",
            "Low": "P4"
        }
        return mapping.get(severity, "P3")
    
    def _create_ticket_title(self, finding: Dict[str, Any]) -> str:
        """
        Create ticket title with severity prefix.
        
        Args:
            finding: Security finding dictionary
            
        Returns:
            Formatted ticket title
        """
        severity = finding.get("severity", "Medium")
        title = finding.get("title", "Unnamed security issue")
        return f"[{severity}] {title}"
    
    def _create_ticket_description(self, finding: Dict[str, Any]) -> str:
        """
        Create detailed ticket description with LLM instructions.
        
        Args:
            finding: Security finding dictionary
            
        Returns:
            Formatted ticket description
        """
        description_parts = []
        
        # Security Issue Description
        title = finding.get("title", "Unnamed security issue")
        description_parts.append(f"## Security Issue: {title}")
        description_parts.append("")
        
        # Why it's a problem
        impact = finding.get("impact", "Impact not specified")
        description_parts.append(f"**Why this is a problem:** {impact}")
        description_parts.append("")
        
        # Evidence
        evidence = finding.get("evidence", "No evidence provided")
        description_parts.append(f"**Evidence:** {evidence}")
        description_parts.append("")
        
        # Location
        locations = finding.get("location", [])
        if locations:
            location_str = ", ".join(locations)
            description_parts.append(f"**Location:** {location_str}")
            description_parts.append("")
        
        # Why it should be fixed
        likelihood = finding.get("likelihood", "Medium")
        severity = finding.get("severity", "Medium")
        description_parts.append(f"**Why it should be fixed:** This is a {severity} severity issue with {likelihood} likelihood of exploitation. ")
        
        standards = finding.get("standards", [])
        if standards:
            standards_str = ", ".join(standards)
            description_parts.append(f"It violates security standards: {standards_str}.")
        
        description_parts.append("")
        
        # LLM Instruction
        llm_instruction = self._create_llm_instruction(finding)
        description_parts.append("## LLM Fix Instruction")
        description_parts.append("")
        description_parts.append("Copy and paste this instruction to an LLM to get specific fix guidance:")
        description_parts.append("")
        description_parts.append("```")
        description_parts.append(llm_instruction)
        description_parts.append("```")
        description_parts.append("")
        
        # Technical Details
        description_parts.append("## Technical Details")
        description_parts.append("")
        description_parts.append(f"**Type:** {finding.get('type', 'Issue')}")
        description_parts.append(f"**Control:** {finding.get('control', 'Other')}")
        description_parts.append(f"**Category:** {finding.get('category', 'Other')}")
        description_parts.append(f"**Confidence:** {finding.get('confidence', 'Medium')}")
        
        # Fix steps
        fix = finding.get("fix", {})
        if fix:
            description_parts.append("")
            description_parts.append("**Manual Fix Steps:**")
            steps = fix.get("steps", [])
            for i, step in enumerate(steps, 1):
                description_parts.append(f"{i}. {step}")
            
            # Secure example
            secure_example = fix.get("secure_example", "")
            if secure_example:
                description_parts.append("")
                description_parts.append("**Secure Example:**")
                description_parts.append("```")
                description_parts.append(secure_example)
                description_parts.append("```")
        
        # Notes
        notes = finding.get("notes")
        if notes:
            description_parts.append("")
            description_parts.append(f"**Notes:** {notes}")
        
        return "\n".join(description_parts)
    
    def _create_llm_instruction(self, finding: Dict[str, Any]) -> str:
        """
        Create LLM instruction for fixing the security issue.
        
        Args:
            finding: Security finding dictionary
            
        Returns:
            LLM instruction string
        """
        title = finding.get("title", "security issue")
        control = finding.get("control", "security control")
        category = finding.get("category", "security")
        impact = finding.get("impact", "security vulnerability")
        
        instruction = f"""Your task is to fix {title} in this {category} application.

**Problem:** {impact}

**Security Control:** {control}

**What you need to do:**
1. Identify the specific code causing this issue
2. Implement a secure solution following best practices
3. Ensure the fix doesn't break existing functionality
4. Add appropriate error handling and validation
5. Test the implementation

**Requirements:**
- Follow OWASP security guidelines
- Use secure coding practices
- Provide working code examples
- Explain the security improvement
- Consider edge cases and error scenarios

Please provide a complete, production-ready solution with explanations."""
        
        return instruction
    
    def _create_ticket_labels(self, finding: Dict[str, Any]) -> List[str]:
        """
        Create ticket labels.
        
        Args:
            finding: Security finding dictionary
            
        Returns:
            List of ticket labels
        """
        labels = ["security", "tekk"]
        
        # Add category label
        category = finding.get("category", "Other")
        labels.append(f"category:{category}")
        
        # Add control label
        control = finding.get("control", "Other")
        labels.append(f"control:{control}")
        
        # Add severity label
        severity = finding.get("severity", "Medium")
        labels.append(f"severity:{severity}")
        
        # Add type label
        finding_type = finding.get("type", "Issue")
        labels.append(f"type:{finding_type}")
        
        return labels
    
    def _create_ticket_from_finding(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a Jira-style ticket from a security finding.
        
        Args:
            finding: Security finding dictionary
            
        Returns:
            Ticket dictionary
        """
        return {
            "title": self._create_ticket_title(finding),
            "description": self._create_ticket_description(finding),
            "labels": self._create_ticket_labels(finding),
            "priority": self._map_severity_to_priority(finding.get("severity", "Medium")),
            "source_finding_id": finding.get("id", "UNKNOWN")
        }
    
    def convert_findings_to_tickets(self, report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert all findings in the report to tickets.
        
        Args:
            report: Security analysis report
            
        Returns:
            List of ticket dictionaries
        """
        findings = report.get("findings", [])
        tickets = []
        
        for finding in findings:
            ticket = self._create_ticket_from_finding(finding)
            tickets.append(ticket)
        
        self.tickets = tickets
        return tickets
    
    def write_tickets_to_file(self, tickets: List[Dict[str, Any]], output_path: str, pretty_print: bool = True) -> None:
        """
        Write tickets to a JSON file.
        
        Args:
            tickets: List of ticket dictionaries
            output_path: Path to output file
            pretty_print: Whether to format JSON with indentation
        """
        path = Path(output_path)
        
        # Create parent directories if they don't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        
        if pretty_print:
            json_output = json.dumps(tickets, indent=2, ensure_ascii=False)
        else:
            json_output = json.dumps(tickets, ensure_ascii=False)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(json_output)
    
    def write_tickets_to_stdout(self, tickets: List[Dict[str, Any]], pretty_print: bool = True) -> None:
        """
        Write tickets to stdout.
        
        Args:
            tickets: List of ticket dictionaries
            pretty_print: Whether to format JSON with indentation
        """
        if pretty_print:
            json_output = json.dumps(tickets, indent=2, ensure_ascii=False)
        else:
            json_output = json.dumps(tickets, ensure_ascii=False)
        
        print(json_output)
    
    def write_tickets(self, report: Dict[str, Any], output_path: Optional[str] = None, pretty_print: bool = True) -> List[Dict[str, Any]]:
        """
        Convert findings to tickets and write to output.
        
        Args:
            report: Security analysis report
            output_path: Optional path to output file (if None, writes to stdout)
            pretty_print: Whether to format JSON with indentation
            
        Returns:
            List of created tickets
        """
        tickets = self.convert_findings_to_tickets(report)
        
        if output_path:
            self.write_tickets_to_file(tickets, output_path, pretty_print)
        else:
            self.write_tickets_to_stdout(tickets, pretty_print)
        
        return tickets
    
    def get_ticket_summary(self) -> Dict[str, Any]:
        """
        Get summary of created tickets.
        
        Returns:
            Dictionary with ticket summary information
        """
        if not self.tickets:
            return {"total_tickets": 0, "by_priority": {}, "by_severity": {}}
        
        by_priority = {}
        by_severity = {}
        
        for ticket in self.tickets:
            priority = ticket.get("priority", "P3")
            by_priority[priority] = by_priority.get(priority, 0) + 1
            
            # Extract severity from title
            title = ticket.get("title", "")
            if title.startswith("[") and "]" in title:
                severity = title[1:title.index("]")]
                by_severity[severity] = by_severity.get(severity, 0) + 1
        
        return {
            "total_tickets": len(self.tickets),
            "by_priority": by_priority,
            "by_severity": by_severity
        }
