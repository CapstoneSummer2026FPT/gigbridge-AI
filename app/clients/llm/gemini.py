from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from app.clients.llm.base import BaseLLMClient
from app.core.config import settings

class GeminiClient(BaseLLMClient):
    """Client for Google Gemini (using OpenAI-compatible endpoints)"""
    
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        # Initialize client using Google OpenAI-compatible gateway
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        ) if self.api_key else None
        self.model_name = "gemini-1.5-flash"  # Default model

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        response_format: Optional[Any] = None
    ) -> str:
        if not self.client:
            raise ValueError("Gemini API Key is not configured.")

        messages = [{"role": "system", "content": system_prompt}]
        
        if history:
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})
                
        messages.append({"role": "user", "content": user_prompt})

        kwargs = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.0
        }

        if response_format:
            response = await self.client.beta.chat.completions.parse(
                **kwargs,
                response_format=response_format
            )
            return response.choices[0].message.content
        else:
            response = await self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
