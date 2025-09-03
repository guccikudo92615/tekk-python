"""
Guardrails tool for validating and strengthening LLM security reports.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Set
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from models.schema import RepoContext, SecurityReport, Finding, BaselineCheck, PrioritizedAction, Summary


class Guardrails:
    """Tool for validating and enhancing security analysis reports."""
    
    def __init__(self):
        self.foundational_controls = [
            "Authentication", "Authorization", "Rate Limiting", "Security Headers",
            "Audit Logging", "Secrets Management", "Environment Separation",
            "Backup Strategy", "Privacy Controls", "Monitoring"
        ]
    
    def validate_and_repair_schema(self, llm_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and repair the LLM report schema.
        
        Args:
            llm_report: Raw LLM report dictionary
            
        Returns:
            Validated and repaired report dictionary
        """
        # Ensure all required top-level keys exist
        required_keys = ["summary", "findings", "baseline_checklist", "prioritized_actions", "checks_omitted"]
        for key in required_keys:
            if key not in llm_report:
                llm_report[key] = self._get_default_value(key)
        
        # Validate and repair summary
        llm_report["summary"] = self._repair_summary(llm_report.get("summary", {}))
        
        # Validate and repair findings
        llm_report["findings"] = self._repair_findings(llm_report.get("findings", []))
        
        # Validate and repair baseline checklist
        llm_report["baseline_checklist"] = self._repair_baseline_checklist(llm_report.get("baseline_checklist", []))
        
        # Validate and repair prioritized actions
        llm_report["prioritized_actions"] = self._repair_prioritized_actions(llm_report.get("prioritized_actions", []))
        
        # Ensure checks_omitted is a list
        if not isinstance(llm_report["checks_omitted"], list):
            llm_report["checks_omitted"] = ["Invalid checks_omitted format"]
        
        return llm_report
    
    def _get_default_value(self, key: str) -> Any:
        """Get default value for missing keys."""
        defaults = {
            "summary": {
                "risk_overview": "Analysis completed with schema validation",
                "findings_total_count": 0,
                "missing_controls_count": 0,
                "severity_breakdown": {"Critical": 0, "High": 0, "Medium": 0, "Low": 0},
                "quick_wins_minutes": 0
            },
            "findings": [],
            "baseline_checklist": [],
            "prioritized_actions": [],
            "checks_omitted": ["Schema validation applied"]
        }
        return defaults.get(key, [])
    
    def _repair_summary(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """Repair summary section."""
        required_fields = {
            "risk_overview": "Risk assessment not provided",
            "findings_total_count": 0,
            "missing_controls_count": 0,
            "severity_breakdown": {"Critical": 0, "High": 0, "Medium": 0, "Low": 0},
            "quick_wins_minutes": 0
        }
        
        for field, default in required_fields.items():
            if field not in summary:
                summary[field] = default
        
        return summary
    
    def _repair_findings(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Repair findings list."""
        repaired_findings = []
        
        for i, finding in enumerate(findings):
            if not isinstance(finding, dict):
                continue
            
            # Ensure required fields exist
            finding["id"] = finding.get("id", f"SEC-{i+1:03d}")
            finding["title"] = finding.get("title", "Unnamed security issue")
            finding["type"] = finding.get("type", "Issue")
            finding["control"] = finding.get("control", "Other")
            finding["category"] = finding.get("category", "Other")
            finding["location"] = finding.get("location", [])
            finding["evidence"] = finding.get("evidence", "No evidence provided")
            finding["impact"] = finding.get("impact", "Impact not specified")
            finding["likelihood"] = finding.get("likelihood", "Medium")
            finding["severity"] = finding.get("severity", "Medium")
            finding["confidence"] = finding.get("confidence", "Medium")
            finding["standards"] = finding.get("standards", [])
            finding["notes"] = finding.get("notes")
            
            # Repair fix section
            if "fix" not in finding or not isinstance(finding["fix"], dict):
                finding["fix"] = {
                    "steps": ["Fix steps not provided"],
                    "secure_example": "No example provided",
                    "owner_hint": "Security",
                    "eta": "≤1d"
                }
            else:
                fix = finding["fix"]
                fix["steps"] = fix.get("steps", ["Fix steps not provided"])
                fix["secure_example"] = fix.get("secure_example", "No example provided")
                fix["owner_hint"] = fix.get("owner_hint", "Security")
                fix["eta"] = fix.get("eta", "≤1d")
            
            repaired_findings.append(finding)
        
        return repaired_findings
    
    def _repair_baseline_checklist(self, checklist: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Repair baseline checklist."""
        repaired_checklist = []
        
        for item in checklist:
            if not isinstance(item, dict):
                continue
            
            repaired_item = {
                "control": item.get("control", "Unknown Control"),
                "status": item.get("status", "N/A"),
                "justification": item.get("justification", "No justification provided")
            }
            repaired_checklist.append(repaired_item)
        
        return repaired_checklist
    
    def _repair_prioritized_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Repair prioritized actions."""
        repaired_actions = []
        
        for action in actions:
            if not isinstance(action, dict):
                continue
            
            repaired_action = {
                "id": action.get("id", "UNKNOWN"),
                "eta": action.get("eta", "≤1d")
            }
            repaired_actions.append(repaired_action)
        
        return repaired_actions
    
    def add_missing_controls(self, repo_context: RepoContext, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add missing control findings based on repository structure analysis.
        
        Args:
            repo_context: Repository context
            report: Current security report
            
        Returns:
            Enhanced report with missing control findings
        """
        repo_path = Path(repo_context.root_path)
        existing_controls = self._get_existing_controls(report)
        missing_controls = []
        
        # Check for foundational controls
        for control in self.foundational_controls:
            if control not in existing_controls:
                missing_finding = self._create_missing_control_finding(control, repo_path)
                if missing_finding:
                    missing_controls.append(missing_finding)
        
        # Add missing controls to findings
        if missing_controls:
            report["findings"].extend(missing_controls)
            report["summary"]["missing_controls_count"] += len(missing_controls)
            report["summary"]["findings_total_count"] += len(missing_controls)
        
        return report
    
    def _get_existing_controls(self, report: Dict[str, Any]) -> Set[str]:
        """Get set of existing controls from the report."""
        existing = set()
        
        for finding in report.get("findings", []):
            if finding.get("type") == "MissingControl":
                control = finding.get("control", "")
                if control:
                    existing.add(control)
        
        for item in report.get("baseline_checklist", []):
            if item.get("status") == "Present":
                existing.add(item.get("control", ""))
        
        return existing
    
    def _create_missing_control_finding(self, control: str, repo_path: Path) -> Dict[str, Any]:
        """Create a missing control finding based on repository structure."""
        control_mappings = {
            "Authentication": {
                "control": "AuthN",
                "category": "AuthZ",
                "files_to_check": ["auth", "login", "user", "session"],
                "evidence_template": "No authentication implementation found in {files}"
            },
            "Authorization": {
                "control": "AuthZ",
                "category": "AuthZ",
                "files_to_check": ["auth", "permission", "role", "access"],
                "evidence_template": "No authorization framework found in {files}"
            },
            "Rate Limiting": {
                "control": "RateLimiting",
                "category": "Other",
                "files_to_check": ["middleware", "rate", "limit", "throttle"],
                "evidence_template": "No rate limiting implementation found in {files}"
            },
            "Security Headers": {
                "control": "Headers",
                "category": "Headers",
                "files_to_check": ["middleware", "config", "app", "server"],
                "evidence_template": "No security headers configuration found in {files}"
            },
            "Audit Logging": {
                "control": "Logging",
                "category": "Logging",
                "files_to_check": ["log", "audit", "monitor", "track"],
                "evidence_template": "No audit logging implementation found in {files}"
            }
        }
        
        mapping = control_mappings.get(control)
        if not mapping:
            return None
        
        # Check for files that might contain this control
        found_files = []
        for pattern in mapping["files_to_check"]:
            for file_path in repo_path.rglob(f"*{pattern}*"):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    found_files.append(str(file_path.relative_to(repo_path)))
        
        if not found_files:
            found_files = ["No relevant files found"]
        
        evidence = mapping["evidence_template"].format(files=", ".join(found_files[:3]))
        
        return {
            "id": f"SEC-{len(found_files):03d}",
            "title": f"Missing {control}",
            "type": "MissingControl",
            "control": mapping["control"],
            "category": mapping["category"],
            "location": found_files[:3],
            "evidence": evidence,
            "impact": f"Application lacks {control.lower()} which is a fundamental security control",
            "likelihood": "Medium",
            "severity": "Medium",
            "confidence": "Low",
            "standards": ["OWASP-ASVS V4.0"],
            "fix": {
                "steps": [
                    f"Implement {control.lower()} framework",
                    "Configure appropriate policies",
                    "Test implementation thoroughly"
                ],
                "secure_example": f"// Implement {control.lower()} here",
                "owner_hint": "Security",
                "eta": "≤1d"
            },
            "notes": "Needs verification - structural analysis only"
        }
    
    def normalize_and_deduplicate(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize severities and deduplicate findings.
        
        Args:
            report: Security report
            
        Returns:
            Normalized and deduplicated report
        """
        # Deduplicate findings by title and evidence
        seen_findings = set()
        unique_findings = []
        
        for finding in report.get("findings", []):
            key = (finding.get("title", ""), finding.get("evidence", ""))
            if key not in seen_findings:
                seen_findings.add(key)
                unique_findings.append(finding)
            else:
                # Merge locations if duplicate
                for existing in unique_findings:
                    if (existing.get("title", ""), existing.get("evidence", "")) == key:
                        existing_locations = set(existing.get("location", []))
                        new_locations = set(finding.get("location", []))
                        existing["location"] = list(existing_locations.union(new_locations))
                        break
        
        report["findings"] = unique_findings
        
        # Recalculate summary counts
        self._recalculate_summary(report)
        
        return report
    
    def _recalculate_summary(self, report: Dict[str, Any]) -> None:
        """Recalculate summary statistics."""
        findings = report.get("findings", [])
        
        # Count findings by type and severity
        total_count = len(findings)
        missing_controls_count = sum(1 for f in findings if f.get("type") == "MissingControl")
        
        severity_breakdown = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        for finding in findings:
            severity = finding.get("severity", "Medium")
            if severity in severity_breakdown:
                severity_breakdown[severity] += 1
        
        # Update summary
        summary = report.get("summary", {})
        summary["findings_total_count"] = total_count
        summary["missing_controls_count"] = missing_controls_count
        summary["severity_breakdown"] = severity_breakdown
        
        # Estimate quick wins (Low severity findings that can be fixed in ≤30m)
        quick_wins = sum(1 for f in findings 
                        if f.get("severity") == "Low" and f.get("fix", {}).get("eta") == "≤30m")
        summary["quick_wins_minutes"] = quick_wins * 30
    
    def apply_guardrails(self, repo_context: RepoContext, llm_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply all guardrails to the LLM report.
        
        Args:
            repo_context: Repository context
            llm_report: Raw LLM report
            
        Returns:
            Validated and enhanced security report
        """
        # Step 1: Validate and repair schema
        report = self.validate_and_repair_schema(llm_report)
        
        # Step 2: Add missing controls based on repo structure
        report = self.add_missing_controls(repo_context, report)
        
        # Step 3: Normalize and deduplicate
        report = self.normalize_and_deduplicate(report)
        
        return report
