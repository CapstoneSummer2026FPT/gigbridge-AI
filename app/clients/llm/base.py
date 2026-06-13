from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseLLMClient(ABC):
    """Abstract base class defining interface for all LLM client providers"""
    
    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        response_format: Optional[Any] = None
    ) -> str:
        """
        Send a completion request to the LLM model.
        
        Args:
            system_prompt: Instruction rules for the assistant.
            user_prompt: Main query input.
            history: Optional list of chat history messages.
            response_format: Optional Pydantic model class for structured outputs.
        """
        pass
