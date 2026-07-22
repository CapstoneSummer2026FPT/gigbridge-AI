import httpx
import json
from typing import List, Dict, Any, Optional
from app.clients.llm.base import BaseLLMClient
from app.core.config import settings

class ClaudeClient(BaseLLMClient):
    """Client for Anthropic Claude completion requests (using HTTP/JSON)"""
    
    def __init__(self):
        self.api_key = settings.CLAUDE_API_KEY
        self.model_name = "claude-3-5-sonnet-20240620"  # Default model
        self.url = "https://api.anthropic.com/v1/messages"

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        response_format: Optional[Any] = None,
        model: Optional[str] = None,
    ) -> str:
        if not self.api_key:
            raise ValueError("Claude API Key is not configured.")

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        # Format messages for Anthropic (roles: user, assistant only. System goes to top-level key)
        formatted_messages = []
        if history:
            for msg in history:
                # Map openai roles to anthropic roles
                role = "assistant" if msg["role"] == "assistant" else "user"
                formatted_messages.append({"role": role, "content": msg["content"]})
        
        formatted_messages.append({"role": "user", "content": user_prompt})

        # If structured format is requested, we append instructions to the prompt
        actual_system_prompt = system_prompt
        if response_format:
            schema_json = json.dumps(response_format.model_json_schema())
            actual_system_prompt += f"\n\nCRITICAL: You must return the output as a valid JSON object matching the following JSON Schema. Do not include markdown code block formatting or any other text before/after the JSON.\nSchema:\n{schema_json}"

        payload = {
            "model": model or self.model_name,
            "max_tokens": 4000,
            "system": actual_system_prompt,
            "messages": formatted_messages,
            "temperature": 0.0
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(self.url, headers=headers, json=payload)
            response.raise_for_status()
            response_data = response.json()
            
            content_text = response_data["content"][0]["text"]
            
            if response_format:
                # Verify it is valid JSON (Pydantic parser will validate it later)
                # Just strip any surrounding formatting in case model didn't obey instructions
                cleaned_text = content_text.strip()
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                content_text = cleaned_text.strip()
                
            return content_text
