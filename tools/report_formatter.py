#!/usr/bin/env python3
"""
Report Formatter - Converts JSON security analysis reports to human-readable formats
Supports text, markdown, and PDF output with professional formatting
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("Warning: reportlab not available. PDF generation will be disabled.")


class SecurityReportFormatter:
    """Formats security analysis reports into human-readable formats"""
    
    def __init__(self, json_report_path: str):
        """Initialize with JSON report path"""
        self.json_report_path = Path(json_report_path)
        self.report_data = self._load_report()
        self.output_dir = self.json_report_path.parent
        
    def _load_report(self) -> Dict[str, Any]:
        """Load the JSON report data"""
        try:
            with open(self.json_report_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise Exception(f"Failed to load report: {e}")
    
    def format_text_report(self) -> str:
        """Generate a formatted text report"""
        lines = []
        
        # Header
        lines.append("=" * 80)
        lines.append("SECURITY ANALYSIS REPORT")
        lines.append("=" * 80)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Report File: {self.json_report_path.name}")
        lines.append("")
        
        # Summary
        summary = self.report_data.get('summary', {})
        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Risk Overview: {summary.get('risk_overview', 'N/A')}")
        lines.append(f"Total Findings: {summary.get('findings_total_count', 0)}")
        lines.append(f"Files Analyzed: {summary.get('files_analyzed', 0)}")
        lines.append(f"Analysis Agents: {summary.get('agents_used', 0)}")
        lines.append("")
        
        # Severity Breakdown
        severity_breakdown = summary.get('severity_breakdown', {})
        lines.append("SEVERITY BREAKDOWN")
        lines.append("-" * 40)
        for severity, count in severity_breakdown.items():
            lines.append(f"{severity:>8}: {count:>3} findings")
        lines.append("")
        
        # Findings by Severity
        findings = self.report_data.get('findings', [])
        findings_by_severity = self._group_findings_by_severity(findings)
        
        for severity in ['Critical', 'High', 'Medium', 'Low']:
            if severity in findings_by_severity:
                lines.append(f"{severity.upper()} SEVERITY FINDINGS")
                lines.append("-" * 40)
                lines.append("")
                
                for finding in findings_by_severity[severity]:
                    lines.append(f"ID: {finding.get('id', 'N/A')}")
                    lines.append(f"Title: {finding.get('title', 'N/A')}")
                    lines.append(f"Type: {finding.get('type', 'N/A')}")
                    lines.append(f"Category: {finding.get('category', 'N/A')}")
                    
                    # Location
                    locations = finding.get('location', [])
                    if locations:
                        lines.append(f"Location: {', '.join(locations)}")
                    
                    # Evidence
                    evidence = finding.get('evidence', '')
                    if evidence:
                        lines.append(f"Evidence: {evidence}")
                    
                    # Impact
                    impact = finding.get('impact', '')
                    if impact:
                        lines.append(f"Impact: {impact}")
                    
                    # Standards
                    standards = finding.get('standards', [])
                    if standards:
                        lines.append(f"Standards: {', '.join(standards)}")
                    
                    # Fix
                    fix = finding.get('fix', {})
                    if fix:
                        lines.append("Remediation:")
                        steps = fix.get('steps', [])
                        for i, step in enumerate(steps, 1):
                            lines.append(f"  {i}. {step}")
                        
                        eta = fix.get('eta', '')
                        if eta:
                            lines.append(f"  ETA: {eta}")
                        
                        owner = fix.get('owner_hint', '')
                        if owner:
                            lines.append(f"  Owner: {owner}")
                    
                    lines.append("")
                    lines.append("-" * 40)
                    lines.append("")
        
        # Footer
        lines.append("=" * 80)
        lines.append("END OF REPORT")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def format_markdown_report(self) -> str:
        """Generate a formatted markdown report"""
        lines = []
        
        # Header
        lines.append("# Security Analysis Report")
        lines.append("")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")  
        lines.append(f"**Report File:** `{self.json_report_path.name}`")
        lines.append("")
        
        # Summary
        summary = self.report_data.get('summary', {})
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(f"**Risk Overview:** {summary.get('risk_overview', 'N/A')}")
        lines.append(f"**Total Findings:** {summary.get('findings_total_count', 0)}")
        lines.append(f"**Files Analyzed:** {summary.get('files_analyzed', 0)}")
        lines.append(f"**Analysis Agents:** {summary.get('agents_used', 0)}")
        lines.append("")
        
        # Severity Breakdown Table
        severity_breakdown = summary.get('severity_breakdown', {})
        lines.append("## Severity Breakdown")
        lines.append("")
        lines.append("| Severity | Count |")
        lines.append("|----------|-------|")
        for severity, count in severity_breakdown.items():
            lines.append(f"| {severity} | {count} |")
        lines.append("")
        
        # Findings by Severity
        findings = self.report_data.get('findings', [])
        findings_by_severity = self._group_findings_by_severity(findings)
        
        for severity in ['Critical', 'High', 'Medium', 'Low']:
            if severity in findings_by_severity:
                lines.append(f"## {severity} Severity Findings")
                lines.append("")
                
                for i, finding in enumerate(findings_by_severity[severity], 1):
                    lines.append(f"### {i}. {finding.get('title', 'N/A')}")
                    lines.append("")
                    
                    # Metadata table
                    lines.append("| Field | Value |")
                    lines.append("|-------|-------|")
                    lines.append(f"| **ID** | `{finding.get('id', 'N/A')}` |")
                    lines.append(f"| **Type** | {finding.get('type', 'N/A')} |")
                    lines.append(f"| **Category** | {finding.get('category', 'N/A')} |")
                    lines.append(f"| **Likelihood** | {finding.get('likelihood', 'N/A')} |")
                    lines.append(f"| **Confidence** | {finding.get('confidence', 'N/A')} |")
                    
                    # Location
                    locations = finding.get('location', [])
                    if locations:
                        lines.append(f"| **Location** | {', '.join(locations)} |")
                    
                    lines.append("")
                    
                    # Evidence
                    evidence = finding.get('evidence', '')
                    if evidence:
                        lines.append("**Evidence:**")
                        lines.append("")
                        lines.append(f"> {evidence}")
                        lines.append("")
                    
                    # Impact
                    impact = finding.get('impact', '')
                    if impact:
                        lines.append("**Impact:**")
                        lines.append("")
                        lines.append(f"> {impact}")
                        lines.append("")
                    
                    # Standards
                    standards = finding.get('standards', [])
                    if standards:
                        lines.append("**Standards:**")
                        lines.append("")
                        for standard in standards:
                            lines.append(f"- {standard}")
                        lines.append("")
                    
                    # Fix
                    fix = finding.get('fix', {})
                    if fix:
                        lines.append("**Remediation:**")
                        lines.append("")
                        steps = fix.get('steps', [])
                        for i, step in enumerate(steps, 1):
                            lines.append(f"{i}. {step}")
                        lines.append("")
                        
                        eta = fix.get('eta', '')
                        owner = fix.get('owner_hint', '')
                        if eta or owner:
                            lines.append("**Additional Info:**")
                            lines.append("")
                            if eta:
                                lines.append(f"- **ETA:** {eta}")
                            if owner:
                                lines.append(f"- **Owner:** {owner}")
                            lines.append("")
                    
                    lines.append("---")
                    lines.append("")
        
        return "\n".join(lines)
    
    def format_pdf_report(self) -> str:
        """Generate a PDF report (requires reportlab)"""
        if not REPORTLAB_AVAILABLE:
            raise Exception("reportlab is required for PDF generation. Install with: pip install reportlab")
        
        pdf_path = self.output_dir / f"{self.json_report_path.stem}_formatted.pdf"
        
        # Create PDF document
        doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Create custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkred
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.darkblue
        )
        
        subheading_style = ParagraphStyle(
            'CustomSubHeading',
            parent=styles['Heading3'],
            fontSize=14,
            spaceAfter=8,
            textColor=colors.darkgreen
        )
        
        # Build content
        story = []
        
        # Title
        story.append(Paragraph("Security Analysis Report", title_style))
        story.append(Spacer(1, 12))
        
        # Header info
        story.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Paragraph(f"<b>Report File:</b> {self.json_report_path.name}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Summary
        summary = self.report_data.get('summary', {})
        story.append(Paragraph("Executive Summary", heading_style))
        
        summary_data = [
            ['Field', 'Value'],
            ['Risk Overview', summary.get('risk_overview', 'N/A')],
            ['Total Findings', str(summary.get('findings_total_count', 0))],
            ['Files Analyzed', str(summary.get('files_analyzed', 0))],
            ['Analysis Agents', str(summary.get('agents_used', 0))]
        ]
        
        summary_table = Table(summary_data)
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Severity breakdown
        severity_breakdown = summary.get('severity_breakdown', {})
        story.append(Paragraph("Severity Breakdown", heading_style))
        
        severity_data = [['Severity', 'Count']]
        for severity, count in severity_breakdown.items():
            severity_data.append([severity, str(count)])
        
        severity_table = Table(severity_data)
        severity_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(severity_table)
        story.append(PageBreak())
        
        # Findings by severity
        findings = self.report_data.get('findings', [])
        findings_by_severity = self._group_findings_by_severity(findings)
        
        for severity in ['Critical', 'High', 'Medium', 'Low']:
            if severity in findings_by_severity:
                story.append(Paragraph(f"{severity} Severity Findings", heading_style))
                story.append(Spacer(1, 12))
                
                for i, finding in enumerate(findings_by_severity[severity], 1):
                    story.append(Paragraph(f"{i}. {finding.get('title', 'N/A')}", subheading_style))
                    
                    # Finding details
                    details = []
                    details.append(f"<b>ID:</b> {finding.get('id', 'N/A')}")
                    details.append(f"<b>Type:</b> {finding.get('type', 'N/A')}")
                    details.append(f"<b>Category:</b> {finding.get('category', 'N/A')}")
                    details.append(f"<b>Likelihood:</b> {finding.get('likelihood', 'N/A')}")
                    details.append(f"<b>Confidence:</b> {finding.get('confidence', 'N/A')}")
                    
                    locations = finding.get('location', [])
                    if locations:
                        details.append(f"<b>Location:</b> {', '.join(locations)}")
                    
                    for detail in details:
                        story.append(Paragraph(detail, styles['Normal']))
                    
                    # Evidence
                    evidence = finding.get('evidence', '')
                    if evidence:
                        story.append(Paragraph("<b>Evidence:</b>", styles['Normal']))
                        story.append(Paragraph(evidence, styles['Normal']))
                    
                    # Impact
                    impact = finding.get('impact', '')
                    if impact:
                        story.append(Paragraph("<b>Impact:</b>", styles['Normal']))
                        story.append(Paragraph(impact, styles['Normal']))
                    
                    # Standards
                    standards = finding.get('standards', [])
                    if standards:
                        story.append(Paragraph("<b>Standards:</b>", styles['Normal']))
                        for standard in standards:
                            story.append(Paragraph(f"• {standard}", styles['Normal']))
                    
                    # Fix
                    fix = finding.get('fix', {})
                    if fix:
                        story.append(Paragraph("<b>Remediation:</b>", styles['Normal']))
                        steps = fix.get('steps', [])
                        for j, step in enumerate(steps, 1):
                            story.append(Paragraph(f"{j}. {step}", styles['Normal']))
                        
                        eta = fix.get('eta', '')
                        owner = fix.get('owner_hint', '')
                        if eta or owner:
                            if eta:
                                story.append(Paragraph(f"<b>ETA:</b> {eta}", styles['Normal']))
                            if owner:
                                story.append(Paragraph(f"<b>Owner:</b> {owner}", styles['Normal']))
                    
                    story.append(Spacer(1, 20))
                    
                    # Add page break for large findings
                    if i % 3 == 0:
                        story.append(PageBreak())
        
        # Build PDF
        doc.build(story)
        return str(pdf_path)
    
    def _group_findings_by_severity(self, findings: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group findings by severity level"""
        grouped = {}
        for finding in findings:
            severity = finding.get('severity', 'Unknown')
            if severity not in grouped:
                grouped[severity] = []
            grouped[severity].append(finding)
        return grouped
    
    def generate_all_formats(self) -> Dict[str, str]:
        """Generate all available formats and return file paths"""
        results = {}
        
        # Text format
        text_content = self.format_text_report()
        text_path = self.output_dir / f"{self.json_report_path.stem}_formatted.txt"
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
        results['text'] = str(text_path)
        
        # Markdown format
        markdown_content = self.format_markdown_report()
        markdown_path = self.output_dir / f"{self.json_report_path.stem}_formatted.md"
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        results['markdown'] = str(markdown_path)
        
        # PDF format (if available)
        if REPORTLAB_AVAILABLE:
            try:
                pdf_path = self.format_pdf_report()
                results['pdf'] = pdf_path
            except Exception as e:
                print(f"PDF generation failed: {e}")
        else:
            print("PDF generation skipped (reportlab not available)")
        
        return results


def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(description='Format security analysis reports')
    parser.add_argument('json_report', help='Path to JSON security analysis report')
    parser.add_argument('--format', choices=['text', 'markdown', 'pdf', 'all'], 
                       default='all', help='Output format')
    parser.add_argument('--output-dir', help='Output directory (default: same as input)')
    
    args = parser.parse_args()
    
    # Initialize formatter
    formatter = SecurityReportFormatter(args.json_report)
    
    if args.output_dir:
        formatter.output_dir = Path(args.output_dir)
        formatter.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate formats
    if args.format == 'all':
        results = formatter.generate_all_formats()
        print("Generated formatted reports:")
        for format_type, path in results.items():
            print(f"  {format_type.upper()}: {path}")
    else:
        if args.format == 'text':
            content = formatter.format_text_report()
            output_path = formatter.output_dir / f"{formatter.json_report_path.stem}_formatted.txt"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Text report generated: {output_path}")
        elif args.format == 'markdown':
            content = formatter.format_markdown_report()
            output_path = formatter.output_dir / f"{formatter.json_report_path.stem}_formatted.md"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Markdown report generated: {output_path}")
        elif args.format == 'pdf':
            if not REPORTLAB_AVAILABLE:
                print("Error: reportlab is required for PDF generation")
                return 1
            output_path = formatter.format_pdf_report()
            print(f"PDF report generated: {output_path}")


if __name__ == "__main__":
    main()
