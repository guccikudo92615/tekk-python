#!/usr/bin/env python3
"""
Coverage Analyzer - Verifies complete repository scanning coverage
Analyzes which files were scanned, chunked, and analyzed by the LLM scanner
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Set, Any, Tuple
from collections import defaultdict
import argparse


class CoverageAnalyzer:
    """Analyzes scanning coverage and provides detailed reports"""
    
    def __init__(self, repo_path: str, report_path: str):
        """Initialize with repository path and analysis report"""
        self.repo_path = Path(repo_path)
        self.report_path = Path(report_path)
        self.report_data = self._load_report()
        self.repo_files = self._get_repo_files()
        
    def _load_report(self) -> Dict[str, Any]:
        """Load the security analysis report"""
        try:
            with open(self.report_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise Exception(f"Failed to load report: {e}")
    
    def _get_repo_files(self) -> Set[Path]:
        """Get all files in the repository (excluding common ignore patterns)"""
        ignore_patterns = {
            '.git', '__pycache__', '.pytest_cache', 'node_modules', 
            '.venv', 'venv', 'env', '.env', 'dist', 'build',
            '.DS_Store', '*.pyc', '*.pyo', '*.pyd', '*.so',
            '*.egg-info', '.coverage', 'htmlcov', '.tox',
            '*.log', '*.tmp', '*.temp', '.vscode', '.idea'
        }
        
        repo_files = set()
        for root, dirs, files in os.walk(self.repo_path):
            # Remove ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_patterns]
            
            for file in files:
                file_path = Path(root) / file
                # Skip ignored files
                if not any(file_path.match(pattern) for pattern in ignore_patterns):
                    repo_files.add(file_path.relative_to(self.repo_path))
        
        return repo_files
    
    def analyze_coverage(self) -> Dict[str, Any]:
        """Perform comprehensive coverage analysis"""
        print("🔍 Analyzing scanning coverage...")
        
        # Extract scanned files from findings
        scanned_files = self._extract_scanned_files()
        
        # Analyze file types
        file_type_analysis = self._analyze_file_types()
        
        # Analyze chunking coverage
        chunking_analysis = self._analyze_chunking_coverage()
        
        # Calculate coverage metrics
        coverage_metrics = self._calculate_coverage_metrics(scanned_files)
        
        # Analyze findings distribution
        findings_analysis = self._analyze_findings_distribution()
        
        return {
            "coverage_metrics": coverage_metrics,
            "scanned_files": list(scanned_files),
            "file_type_analysis": file_type_analysis,
            "chunking_analysis": chunking_analysis,
            "findings_analysis": findings_analysis,
            "total_repo_files": len(self.repo_files),
            "total_scanned_files": len(scanned_files)
        }
    
    def _extract_scanned_files(self) -> Set[Path]:
        """Extract all files that were scanned from findings"""
        scanned_files = set()
        findings = self.report_data.get('findings', [])
        
        for finding in findings:
            locations = finding.get('location', [])
            for location in locations:
                # Extract file path from location (format: "path:line-range")
                if ':' in location:
                    file_path = location.split(':')[0]
                    scanned_files.add(Path(file_path))
                else:
                    scanned_files.add(Path(location))
        
        return scanned_files
    
    def _analyze_file_types(self) -> Dict[str, Any]:
        """Analyze file types in repository vs scanned files"""
        repo_file_types = defaultdict(int)
        scanned_file_types = defaultdict(int)
        
        # Analyze repository files
        for file_path in self.repo_files:
            ext = file_path.suffix.lower()
            if not ext:
                ext = 'no_extension'
            repo_file_types[ext] += 1
        
        # Analyze scanned files
        scanned_files = self._extract_scanned_files()
        for file_path in scanned_files:
            ext = file_path.suffix.lower()
            if not ext:
                ext = 'no_extension'
            scanned_file_types[ext] += 1
        
        return {
            "repository_file_types": dict(repo_file_types),
            "scanned_file_types": dict(scanned_file_types),
            "coverage_by_type": {
                ext: {
                    "total": repo_file_types[ext],
                    "scanned": scanned_file_types[ext],
                    "coverage_pct": (scanned_file_types[ext] / repo_file_types[ext] * 100) if repo_file_types[ext] > 0 else 0
                }
                for ext in set(repo_file_types.keys()) | set(scanned_file_types.keys())
            }
        }
    
    def _analyze_chunking_coverage(self) -> Dict[str, Any]:
        """Analyze chunking coverage from analysis metadata"""
        metadata = self.report_data.get('analysis_metadata', {})
        chunking_info = metadata.get('chunking_result', {})
        
        if not chunking_info:
            return {"status": "No chunking information available"}
        
        total_chunks = chunking_info.get('total_chunks', 0)
        total_files = chunking_info.get('total_files', 0)
        languages_detected = chunking_info.get('languages_detected', {})
        traversal_order = chunking_info.get('traversal_order', [])
        
        return {
            "total_chunks": total_chunks,
            "total_files_chunked": total_files,
            "languages_detected": languages_detected,
            "traversal_order": traversal_order[:10],  # First 10 files
            "chunking_efficiency": total_chunks / total_files if total_files > 0 else 0
        }
    
    def _calculate_coverage_metrics(self, scanned_files: Set[Path]) -> Dict[str, Any]:
        """Calculate comprehensive coverage metrics"""
        total_repo_files = len(self.repo_files)
        total_scanned_files = len(scanned_files)
        
        # Files not scanned
        unscanned_files = self.repo_files - scanned_files
        
        # Coverage percentage
        coverage_percentage = (total_scanned_files / total_repo_files * 100) if total_repo_files > 0 else 0
        
        # Analyze unscanned files
        unscanned_analysis = self._analyze_unscanned_files(unscanned_files)
        
        return {
            "total_repo_files": total_repo_files,
            "total_scanned_files": total_scanned_files,
            "coverage_percentage": round(coverage_percentage, 2),
            "unscanned_files": list(unscanned_files),
            "unscanned_count": len(unscanned_files),
            "unscanned_analysis": unscanned_analysis
        }
    
    def _analyze_unscanned_files(self, unscanned_files: Set[Path]) -> Dict[str, Any]:
        """Analyze files that were not scanned"""
        unscanned_by_type = defaultdict(int)
        unscanned_by_size = {"small": 0, "medium": 0, "large": 0}
        
        for file_path in unscanned_files:
            # File type analysis
            ext = file_path.suffix.lower()
            if not ext:
                ext = 'no_extension'
            unscanned_by_type[ext] += 1
            
            # File size analysis
            try:
                full_path = self.repo_path / file_path
                if full_path.exists():
                    size = full_path.stat().st_size
                    if size < 1024:  # < 1KB
                        unscanned_by_size["small"] += 1
                    elif size < 10240:  # < 10KB
                        unscanned_by_size["medium"] += 1
                    else:
                        unscanned_by_size["large"] += 1
            except OSError:
                pass
        
        return {
            "by_type": dict(unscanned_by_type),
            "by_size": unscanned_by_size
        }
    
    def _analyze_findings_distribution(self) -> Dict[str, Any]:
        """Analyze distribution of findings across files"""
        findings = self.report_data.get('findings', [])
        findings_per_file = defaultdict(int)
        severity_per_file = defaultdict(lambda: defaultdict(int))
        
        for finding in findings:
            locations = finding.get('location', [])
            severity = finding.get('severity', 'Unknown')
            
            for location in locations:
                if ':' in location:
                    file_path = location.split(':')[0]
                    findings_per_file[file_path] += 1
                    severity_per_file[file_path][severity] += 1
        
        # Find files with most findings
        top_files = sorted(findings_per_file.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "total_findings": len(findings),
            "files_with_findings": len(findings_per_file),
            "findings_per_file": dict(findings_per_file),
            "severity_per_file": dict(severity_per_file),
            "top_files_by_findings": top_files
        }
    
    def generate_coverage_report(self) -> str:
        """Generate a comprehensive coverage report"""
        analysis = self.analyze_coverage()
        
        lines = []
        lines.append("=" * 80)
        lines.append("REPOSITORY SCANNING COVERAGE ANALYSIS")
        lines.append("=" * 80)
        lines.append(f"Repository: {self.repo_path}")
        lines.append(f"Report: {self.report_path}")
        lines.append("")
        
        # Coverage Summary
        metrics = analysis['coverage_metrics']
        lines.append("COVERAGE SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Total Repository Files: {metrics['total_repo_files']}")
        lines.append(f"Files Scanned: {metrics['total_scanned_files']}")
        lines.append(f"Coverage: {metrics['coverage_percentage']}%")
        lines.append(f"Unscanned Files: {metrics['unscanned_count']}")
        lines.append("")
        
        # File Type Coverage
        file_types = analysis['file_type_analysis']
        lines.append("FILE TYPE COVERAGE")
        lines.append("-" * 40)
        lines.append(f"{'Type':<15} {'Total':<8} {'Scanned':<8} {'Coverage':<10}")
        lines.append("-" * 50)
        
        for ext, data in file_types['coverage_by_type'].items():
            lines.append(f"{ext:<15} {data['total']:<8} {data['scanned']:<8} {data['coverage_pct']:.1f}%")
        lines.append("")
        
        # Chunking Analysis
        chunking = analysis['chunking_analysis']
        if chunking.get('status') != "No chunking information available":
            lines.append("CHUNKING ANALYSIS")
            lines.append("-" * 40)
            lines.append(f"Total Chunks: {chunking.get('total_chunks', 'N/A')}")
            lines.append(f"Files Chunked: {chunking.get('total_files_chunked', 'N/A')}")
            lines.append(f"Chunking Efficiency: {chunking.get('chunking_efficiency', 0):.2f} chunks/file")
            
            languages = chunking.get('languages_detected', {})
            if languages:
                lines.append(f"Languages Detected: {', '.join(languages.keys())}")
            lines.append("")
        
        # Findings Analysis
        findings = analysis['findings_analysis']
        lines.append("FINDINGS ANALYSIS")
        lines.append("-" * 40)
        lines.append(f"Total Findings: {findings['total_findings']}")
        lines.append(f"Files with Findings: {findings['files_with_findings']}")
        lines.append("")
        
        # Top files by findings
        lines.append("TOP FILES BY FINDINGS")
        lines.append("-" * 40)
        for file_path, count in findings['top_files_by_findings'][:5]:
            lines.append(f"{file_path}: {count} findings")
        lines.append("")
        
        # Unscanned Files Analysis
        unscanned = metrics['unscanned_analysis']
        if unscanned['by_type']:
            lines.append("UNSCANNED FILES ANALYSIS")
            lines.append("-" * 40)
            lines.append("By Type:")
            for ext, count in unscanned['by_type'].items():
                lines.append(f"  {ext}: {count} files")
            lines.append("")
            lines.append("By Size:")
            for size, count in unscanned['by_size'].items():
                lines.append(f"  {size}: {count} files")
            lines.append("")
        
        # Recommendations
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 40)
        if metrics['coverage_percentage'] < 100:
            lines.append(f"⚠️  {metrics['unscanned_count']} files were not scanned")
            lines.append("   Consider reviewing unscanned files for potential security issues")
        else:
            lines.append("✅ 100% file coverage achieved")
        
        if findings['total_findings'] > 0:
            lines.append(f"🔍 {findings['total_findings']} security findings detected")
            lines.append("   Review and prioritize findings by severity")
        
        lines.append("")
        lines.append("=" * 80)
        lines.append("END OF COVERAGE ANALYSIS")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def save_coverage_report(self, output_path: str = None) -> str:
        """Save coverage report to file"""
        if output_path is None:
            output_path = self.report_path.parent / f"{self.report_path.stem}_coverage_analysis.txt"
        
        report_content = self.generate_coverage_report()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        return str(output_path)


def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(description='Analyze repository scanning coverage')
    parser.add_argument('repo_path', help='Path to the repository that was scanned')
    parser.add_argument('report_path', help='Path to the security analysis report JSON')
    parser.add_argument('--output', help='Output path for coverage report')
    
    args = parser.parse_args()
    
    # Initialize analyzer
    analyzer = CoverageAnalyzer(args.repo_path, args.report_path)
    
    # Generate and save report
    output_path = analyzer.save_coverage_report(args.output)
    
    print(f"Coverage analysis complete: {output_path}")
    
    # Print summary to console
    analysis = analyzer.analyze_coverage()
    metrics = analysis['coverage_metrics']
    print(f"\n📊 Coverage Summary:")
    print(f"   Files Scanned: {metrics['total_scanned_files']}/{metrics['total_repo_files']} ({metrics['coverage_percentage']}%)")
    print(f"   Findings: {analysis['findings_analysis']['total_findings']}")
    print(f"   Files with Findings: {analysis['findings_analysis']['files_with_findings']}")


if __name__ == "__main__":
    main()
