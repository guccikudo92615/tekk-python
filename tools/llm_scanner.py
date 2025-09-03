"""
LLMScanner tool for running security analysis using LLM.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv
import openai
sys.path.append(str(Path(__file__).parent.parent))
from models.schema import RepoContext

# Load environment variables
load_dotenv()


class LLMScanner:
    """Tool for running LLM-based security analysis on repositories."""
    
    def __init__(self):
        self.prompt_template = self._load_prompt_template()
        self.client = self._initialize_openai_client()
    
    def _initialize_openai_client(self):
        """Initialize OpenAI client with API key."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        return openai.OpenAI(api_key=api_key)
    
    def _load_prompt_template(self) -> str:
        """Load the security analysis prompt template."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "security_analysis.md"
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Security analysis prompt not found at {prompt_path}")
    
    def _format_prompt(self, repo_context: RepoContext) -> str:
        """
        Format the prompt template with repository context.
        
        Args:
            repo_context: Repository context information
            
        Returns:
            Formatted prompt string
        """
        try:
            # Use string replacement instead of format to avoid issues with curly braces
            prompt = self.prompt_template
            prompt = prompt.replace("{repo}", repo_context.root_path)
            prompt = prompt.replace("{stack}", repo_context.stack)
            prompt = prompt.replace("{cloud}", repo_context.cloud)
            return prompt
        except Exception as e:
            print(f"DEBUG: Prompt formatting error: {e}", file=sys.stderr)
            # Return a simple prompt if formatting fails
            return f"Analyze the repository at {repo_context.root_path} with stack {repo_context.stack} in {repo_context.cloud} environment."
    
    def run_llm(self, prompt: str) -> str:
        """
        Run the LLM with the given prompt using OpenAI API.
        
        Args:
            prompt: The formatted prompt to send to the LLM
            
        Returns:
            JSON string response from the LLM
        """
        try:
            model = os.getenv("OPENAI_MODEL", "gpt-4")
            temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.1"))
            
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior security engineer conducting comprehensive security analysis. Return ONLY valid JSON matching the specified schema. No additional text or explanations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=4000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"OpenAI API error: {e}", file=sys.stderr)
            # Return a fallback response if API fails
            return self._get_fallback_response()
    
    def _get_fallback_response(self) -> str:
        """Get a fallback response when OpenAI API fails."""
        fallback_response = {
            "summary": {
                "risk_overview": "Security analysis failed - OpenAI API unavailable. Manual review recommended.",
                "findings_total_count": 0,
                "missing_controls_count": 0,
                "severity_breakdown": {"Critical": 0, "High": 0, "Medium": 0, "Low": 0},
                "quick_wins_minutes": 0
            },
            "findings": [],
            "baseline_checklist": [],
            "prioritized_actions": [],
            "checks_omitted": ["LLM analysis failed - OpenAI API unavailable"]
        }
        return json.dumps(fallback_response)
    
    def scan_repository(self, repo_context: RepoContext) -> Dict[str, Any]:
        """
        Perform security analysis on the repository.
        
        Args:
            repo_context: Repository context information
            
        Returns:
            Dictionary containing the security analysis results
        """
        # Format the prompt with repository context
        formatted_prompt = self._format_prompt(repo_context)
        
        # Run the LLM analysis
        llm_response = self.run_llm(formatted_prompt)
        
        # Debug: print the response type and content
        print(f"DEBUG: llm_response type: {type(llm_response)}", file=sys.stderr)
        print(f"DEBUG: llm_response content: {str(llm_response)[:200]}...", file=sys.stderr)
        
        # Parse the JSON response
        try:
            # If llm_response is already a dict, return it directly
            if isinstance(llm_response, dict):
                return llm_response
            
            # Clean the response - remove markdown code blocks if present
            cleaned_response = llm_response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]  # Remove ```json
            if cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]   # Remove ```
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]  # Remove trailing ```
            cleaned_response = cleaned_response.strip()
            
            # Parse as JSON
            return json.loads(cleaned_response)
            
        except (json.JSONDecodeError, TypeError) as e:
            print(f"JSON parsing error: {e}", file=sys.stderr)
            print(f"Raw response: {llm_response[:500]}...", file=sys.stderr)
            # If LLM returns invalid JSON, return a minimal valid structure
            return {
                "summary": {
                    "risk_overview": "LLM analysis failed - invalid JSON response",
                    "findings_total_count": 0,
                    "missing_controls_count": 0,
                    "severity_breakdown": {"Critical": 0, "High": 0, "Medium": 0, "Low": 0},
                    "quick_wins_minutes": 0
                },
                "findings": [],
                "baseline_checklist": [],
                "prioritized_actions": [],
                "checks_omitted": [f"LLM analysis failed: {str(e)}"]
            }
