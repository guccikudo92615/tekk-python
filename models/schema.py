"""
Pydantic models for the security analysis report and ticket schemas.
"""

from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field


class FixInfo(BaseModel):
    """Fix information for a security finding."""
    steps: List[str] = Field(description="Step-by-step fix instructions")
    secure_example: str = Field(description="Minimal correct snippet/config")
    owner_hint: Literal["Backend", "Frontend", "DevOps", "Security"] = Field(description="Suggested owner")
    eta: Literal["≤30m", "≤1h", "≤1d"] = Field(description="Estimated time to fix")


class Finding(BaseModel):
    """Individual security finding."""
    id: str = Field(description="Unique finding ID (e.g., SEC-001)")
    title: str = Field(description="Short, specific title")
    type: Literal["Issue", "MissingControl"] = Field(description="Type of finding")
    control: Literal[
        "AuthN", "AuthZ", "TenantIsolation", "RateLimiting", "InputValidation",
        "Secrets", "Headers", "Uploads", "Dependencies", "Cloud", "CI/CD",
        "Logging", "Monitoring", "Backups", "Privacy", "Other"
    ] = Field(description="Security control category")
    category: Literal[
        "Secrets", "AuthZ", "CORS", "Crypto", "Headers", "Uploads",
        "Dependencies", "Cloud", "CI/CD", "Logging", "Privacy", "Other"
    ] = Field(description="Finding category")
    location: List[str] = Field(description="File paths and line ranges")
    evidence: str = Field(description="Exact snippet or evidence-of-absence (masked)")
    impact: str = Field(description="Impact description")
    likelihood: Literal["Low", "Medium", "High"] = Field(description="Likelihood of exploitation")
    severity: Literal["Low", "Medium", "High", "Critical"] = Field(description="Severity level")
    confidence: Literal["Low", "Medium", "High"] = Field(description="Confidence in finding")
    standards: List[str] = Field(description="Relevant security standards (OWASP, CWE, etc.)")
    fix: FixInfo = Field(description="Fix information")
    notes: Optional[str] = Field(default=None, description="Additional notes")


class BaselineCheck(BaseModel):
    """Baseline security control check."""
    control: str = Field(description="Control name")
    status: Literal["Present", "Missing", "N/A"] = Field(description="Control status")
    justification: str = Field(description="Justification for status")


class PrioritizedAction(BaseModel):
    """Prioritized action item."""
    id: str = Field(description="Finding ID")
    eta: str = Field(description="Estimated time to complete")


class Summary(BaseModel):
    """Report summary information."""
    risk_overview: str = Field(description="High-level risk overview")
    findings_total_count: int = Field(description="Total number of findings")
    missing_controls_count: int = Field(description="Number of missing control findings")
    severity_breakdown: Dict[Literal["Critical", "High", "Medium", "Low"], int] = Field(
        description="Count of findings by severity"
    )
    quick_wins_minutes: int = Field(description="Estimated time for quick wins in minutes")


class SecurityReport(BaseModel):
    """Complete security analysis report."""
    summary: Summary = Field(description="Report summary")
    findings: List[Finding] = Field(description="List of security findings")
    baseline_checklist: List[BaselineCheck] = Field(description="Baseline security controls")
    prioritized_actions: List[PrioritizedAction] = Field(description="Prioritized action items")
    checks_omitted: List[str] = Field(description="Checks that were omitted and why")


class Ticket(BaseModel):
    """Jira-style ticket for a security finding."""
    title: str = Field(description="Ticket title with severity prefix")
    description: str = Field(description="Detailed ticket description")
    labels: List[str] = Field(description="Ticket labels")
    priority: Literal["P1", "P2", "P3", "P4"] = Field(description="Ticket priority")
    source_finding_id: str = Field(description="ID of the source finding")


class RepoContext(BaseModel):
    """Repository context information."""
    root_path: str = Field(description="Root path of the repository")
    commit_ref: Optional[str] = Field(default=None, description="Git commit/ref if available")
    stack: str = Field(description="Technology stack description")
    cloud: str = Field(default="local", description="Cloud environment")
