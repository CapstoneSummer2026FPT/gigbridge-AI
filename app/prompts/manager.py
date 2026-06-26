import os
from jinja2 import Environment, FileSystemLoader
from typing import Dict, Any

class PromptManager:
    """Manages prompt template loading, compiling, and rendering using Jinja2 templates"""
    
    def __init__(self):
        # Set up template path
        self.template_dir = os.path.join(os.path.dirname(__file__), "templates")
        os.makedirs(self.template_dir, exist_ok=True)
        self.env = Environment(loader=FileSystemLoader(self.template_dir))

    def render_prompt(self, template_name: str, variables: Dict[str, Any]) -> str:
        """
        Loads a prompt template from app/prompts/templates/ and renders it with variables.
        
        Args:
            template_name: e.g. 'job_posts.txt'
            variables: key-value context variables
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**variables)
        except Exception:
            # Fallback inline default prompts if files are missing (ensuring robustness)
            return self._get_fallback_prompt(template_name, variables)

    def _get_fallback_prompt(self, template_name: str, variables: Dict[str, Any]) -> str:
        if "job_posts" in template_name:
            return (
                f"Generate a professional, structured plain text job post based on this client prompt: {variables.get('client_prompt', '')}."
            )
        elif "interviews" in template_name:
            return (
                f"You are an AI Interview Recruiter for GigBridge. Ask a concise question for the "
                f"role: {variables.get('job_title', 'Developer')}."
            )
        elif "matching" in template_name:
            return (
                f"Compare the job requirements: {variables.get('job_description', '')} "
                f"against candidate resume: {variables.get('resume', '')} and score it."
            )
        return "Audit and analyze the following payload context."

# Dependency helper
_prompt_manager = PromptManager()

def get_prompt_manager() -> PromptManager:
    return _prompt_manager
