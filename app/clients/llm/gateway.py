import logging
from typing import List, Dict, Any, Optional
from app.clients.llm.base import BaseLLMClient
from app.clients.llm.openai import OpenAIClient
from app.clients.llm.gemini import GeminiClient
from app.clients.llm.claude import ClaudeClient
from app.clients.llm.local_model import LocalModelClient
from app.core.config import settings
from app.core.exceptions import LLMProviderException

logger = logging.getLogger("ai_server.llm_gateway")

class LLMGateway(BaseLLMClient):
    """
    Self-contained LLM Router/Gateway that manages model providers,
    routing queries, and executing failovers automatically.
    """
    
    def __init__(self):
        self.providers: Dict[str, BaseLLMClient] = {
            "gemini": GeminiClient(),
            "openai": OpenAIClient(),
            "claude": ClaudeClient(),
            "local": LocalModelClient()
        }
        self.default_provider = settings.DEFAULT_LLM_PROVIDER

    def get_fallback_order(self) -> List[str]:
        """
        Determines the priority order for failovers.
        """
        if self.default_provider == "local":
            return ["local"]

        # Place default provider first, then maintain standard sequence
        order = [self.default_provider]
        standard_sequence = ["openai", "gemini", "claude", "local"]
        for p in standard_sequence:
            if p not in order:
                order.append(p)
        return order

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        response_format: Optional[Any] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        allow_fallback: bool = True,
    ) -> str:
        selected_provider = (provider or self.default_provider).lower()
        fallback_list = (
            self.get_fallback_order()
            if allow_fallback and provider is None
            else [selected_provider]
        )
        errors = []

        for provider_name in fallback_list:
            client = self.providers.get(provider_name)
            if not client:
                continue

            try:
                logger.info(f"Attempting query routing to primary provider: {provider_name}")
                # Verify that API key exists if it's a paid API
                if provider_name != "local" and not client.api_key:
                    raise ValueError(f"API key for {provider_name} is not set.")

                result = await client.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    history=history,
                    response_format=response_format,
                    model=model,
                )
                logger.info(f"Successfully received response from: {provider_name}")
                return result

            except Exception as e:
                error_msg = f"Provider '{provider_name}' failed. Error: {str(e)}"
                logger.warning(error_msg)
                errors.append(error_msg)
                # Failover to the next provider in list...
                continue
        
        # If all providers fail, raise a custom exception
        raise LLMProviderException(
            message="All configured LLM providers in the gateway failed to generate a response.",
            errors=errors
        )

# Dependency injection helper
_llm_gateway = LLMGateway()

def get_llm_gateway() -> LLMGateway:
    return _llm_gateway
