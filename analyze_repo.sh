#!/bin/bash

# Tekk.coach Security Analyzer - Quick Analysis Script
# Usage: ./analyze_repo.sh <repo-path> <stack-description> [repo-name]

if [ $# -lt 2 ]; then
    echo "Usage: $0 <repo-path> <stack-description> [repo-name]"
    echo "Example: $0 ./my-repo \"React + Node.js\" my-project"
    exit 1
fi

REPO_PATH="$1"
STACK="$2"
REPO_NAME="${3:-$(basename "$REPO_PATH")}"
DATE=$(date +%Y%m%d)
OUTPUT_DIR="reports/${REPO_NAME}-${DATE}"

echo "🔍 Starting security analysis..."
echo "Repository: $REPO_PATH"
echo "Stack: $STACK"
echo "Output: $OUTPUT_DIR"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Run analysis
python agent.py \
    --repo "$REPO_PATH" \
    --stack "$STACK" \
    --output "$OUTPUT_DIR/security-report.json" \
    --tickets "$OUTPUT_DIR/jira-tickets.json"

if [ $? -eq 0 ]; then
    echo "✅ Analysis complete!"
    echo "📁 Reports saved to: $OUTPUT_DIR"
    echo "📋 Files generated:"
    ls -la "$OUTPUT_DIR"
else
    echo "❌ Analysis failed!"
    exit 1
fi
