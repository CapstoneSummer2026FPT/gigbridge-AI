import os
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from app.clients.llm.base import BaseLLMClient
from app.core.config import settings

class OpenAIClient(BaseLLMClient):
    """Client for OpenAI completion requests"""
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        # Initialize client only if API key is provided
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None
        self.model_name = "gpt-4o"  # Default model

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        response_format: Optional[Any] = None
    ) -> str:
        if not self.client:
            raise ValueError("OpenAI API Key is not configured.")

        messages = [{"role": "system", "content": system_prompt}]
        
        # Append history if any
        if history:
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})
                
        messages.append({"role": "user", "content": user_prompt})

        kwargs = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.0
        }

        # Handle structured outputs if Pydantic model is supplied
        if response_format:
            # Pydantic structured output helper
            response = await self.client.beta.chat.completions.parse(
                **kwargs,
                response_format=response_format
            )
            return response.choices[0].message.content
        else:
            response = await self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
