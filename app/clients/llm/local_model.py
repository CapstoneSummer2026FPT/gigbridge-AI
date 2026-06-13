from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from app.clients.llm.base import BaseLLMClient
from app.core.config import settings

class LocalModelClient(BaseLLMClient):
    """Client for local model generation (via local Ollama OpenAI-compatible endpoint)"""
    
    def __init__(self):
        self.base_url = f"{settings.LOCAL_OLLAMA_URL.rstrip('/')}/v1/"
        self.model_name = settings.LOCAL_MODEL_NAME
        self.client = AsyncOpenAI(
            api_key="ollama-local",  # Mock key required by SDK
            base_url=self.base_url
        )

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        response_format: Optional[Any] = None
    ) -> str:
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

        # Ollama supports structured JSON output format via standard client calls if configured
        if response_format:
            response = await self.client.beta.chat.completions.parse(
                **kwargs,
                response_format=response_format
            )
            return response.choices[0].message.content
        else:
            response = await self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
