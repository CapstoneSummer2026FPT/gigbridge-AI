from typing import List, Dict, Any, Optional
import httpx
from app.clients.llm.base import BaseLLMClient
from app.core.config import settings

class LocalModelClient(BaseLLMClient):
    """Client for local model generation via Ollama's native chat API."""
    
    def __init__(self):
        self.base_url = settings.LOCAL_OLLAMA_URL.rstrip("/")
        self.model_name = settings.LOCAL_MODEL_NAME

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        response_format: Optional[Any] = None,
        model: Optional[str] = None,
    ) -> str:
        messages = [{"role": "system", "content": system_prompt}]
        
        if history:
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})
                
        messages.append({"role": "user", "content": user_prompt})

        payload: Dict[str, Any] = {
            "model": model or self.model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.0
            }
        }

        if response_format:
            payload["format"] = response_format.model_json_schema()

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

        return data["message"]["content"]
