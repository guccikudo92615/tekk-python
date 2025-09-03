# Tekk.coach Minimal Repo Security Analyzer

A single-agent system that analyzes repositories for security issues and generates Jira-style tickets for remediation.

## Features

- **Single-Agent Architecture**: Streamlined 4-tool workflow
- **LLM-Based Analysis**: Comprehensive security scanning using AI
- **Guardrails**: Validation and enhancement of security reports
- **Missing Control Detection**: Identifies fundamental security gaps
- **Jira Integration**: Generates ready-to-import tickets
- **Strict JSON Output**: Machine-readable reports

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd tekk3-python

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python -m tekksec --repo ./my-repo --stack "Next.js + Express"
```

### With Output Files

```bash
python -m tekksec --repo ./my-repo \
  --stack "React + Node.js" \
  --output report.json \
  --tickets tickets.json
```

### Command Line Options

- `--repo` (required): Local path to repository
- `--stack` (required): Technology stack description
- `--cloud` (optional): Cloud environment (default: "local")
- `--output` (optional): Path for final report JSON
- `--tickets` (optional): Path for Jira-style tickets JSON

## Architecture

The system follows a strict 4-tool workflow:

1. **RepoProvider**: Validates repository path and extracts context
2. **LLMScanner**: Runs comprehensive security analysis using AI
3. **Guardrails**: Validates, repairs, and enhances the analysis
4. **ReportWriter**: Outputs final JSON report
5. **TicketWriter**: Converts findings to Jira-style tickets

## Output Formats

### Security Report JSON

```json
{
  "summary": {
    "risk_overview": "Brief risk assessment",
    "findings_total_count": 0,
    "missing_controls_count": 0,
    "severity_breakdown": {"Critical": 0, "High": 0, "Medium": 0, "Low": 0},
    "quick_wins_minutes": 45
  },
  "findings": [...],
  "baseline_checklist": [...],
  "prioritized_actions": [...],
  "checks_omitted": [...]
}
```

### Jira Tickets JSON

```json
[
  {
    "title": "[High] CORS allows * with credentials",
    "description": "Impact: ...\nEvidence: ...\nFix: ...",
    "labels": ["security", "tekk", "category:CORS", "severity:High"],
    "priority": "P2",
    "source_finding_id": "SEC-102"
  }
]
```

## Security Controls Analyzed

- Authentication & Authorization
- Input Validation & Injection Prevention
- Secrets Management
- Security Headers
- Rate Limiting
- File Upload Security
- Dependencies & Vulnerabilities
- Configuration Security
- Logging & Monitoring
- Privacy Controls

## Development

### Project Structure

```
tekk3-python/
├── agent.py                 # Main orchestrator
├── __main__.py             # CLI entry point
├── models/
│   └── schema.py           # Pydantic models
├── tools/
│   ├── repo_provider.py    # Repository validation
│   ├── llm_scanner.py      # LLM security analysis
│   ├── guardrails.py       # Report validation & enhancement
│   ├── report_writer.py    # JSON output
│   └── ticket_writer.py    # Jira ticket generation
└── prompts/
    └── security_analysis.md # LLM prompt template
```

### Testing

```bash
# Test with a sample repository
python -m tekksec --repo . --stack "Python + Flask" --output test-report.json
```

## License

MIT License - see LICENSE file for details.
