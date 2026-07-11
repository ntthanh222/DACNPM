"""
Base LLM service interface for all LLM providers.

This module defines the abstract interface that all LLM service implementations
must follow, ensuring consistency across different providers (Gemini, OpenAI, Claude, etc.)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class LLMService(ABC):
    """
    Abstract base class for LLM service implementations.

    All LLM providers (Gemini, OpenAI, Claude, etc.) must implement this interface
    to ensure consistent behavior across the application.
    """

    @abstractmethod
    def generate_response(
        self,
        message: str,
        context: Optional[str] = None,
        history: Optional[List[Dict]] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate a response from the LLM.

        Args:
            message: The user's current message
            context: Optional RAG context or additional information
            history: Optional conversation history as list of {'role': 'user/assistant', 'content': '...'}
            system_prompt: Optional system prompt to guide the LLM's behavior

        Returns:
            str: The generated response text

        Raises:
            Exception: If the API call fails or returns an error
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the LLM service is accessible and working.

        Returns:
            bool: True if service is healthy, False otherwise
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, str]:
        """
        Get information about the current model configuration.

        Returns:
            Dict with keys: provider, model, status
        """
        pass


class LLMServiceException(Exception):
    """Custom exception for LLM service errors"""

    def __init__(self, message: str, provider: str = "", original_error: Exception = None):
        self.message = message
        self.provider = provider
        self.original_error = original_error
        super().__init__(f"[{provider}] {message}" if provider else message)
