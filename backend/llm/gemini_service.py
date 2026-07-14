"""
Gemini LLM service implementation.

This module provides integration with Google's Gemini API for LLM capabilities.
Uses the new google-genai package (v2.8+) instead of deprecated google-generativeai.
"""

import logging
import time
from typing import List, Dict, Optional
from google import genai
from google.genai import types
from backend.llm.base_service import LLMService, LLMServiceException
from backend.core.config import settings

logger = logging.getLogger(__name__)


class GeminiService(LLMService):
    """
    Google Gemini API implementation for LLM service.

    Uses the new google-genai package with models like gemini-2.5-flash.
    Optimized for Vietnamese language responses with security knowledge context.
    """

    def __init__(self):
        """Initialize Gemini service with API key from configuration."""
        try:
            api_key = settings.llm_api_key
            if not api_key:
                raise ValueError("LLM_API_KEY not configured in settings")

            # Initialize client with new API
            self.client = genai.Client(api_key=api_key)
            self.model_name = settings.llm_model

            logger.info(f"✅ Gemini service initialized with model: {self.model_name}")

        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini service: {e}")
            raise LLMServiceException(
                message="Failed to initialize Gemini service",
                provider="gemini",
                original_error=e
            )

    def generate_response(
        self,
        message: str,
        context: Optional[str] = None,
        history: Optional[List[Dict]] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate response using Gemini API.

        Args:
            message: User's current message
            context: Optional RAG context from vector store
            history: Optional conversation history for context
            system_prompt: Optional system instructions

        Returns:
            str: Generated response text

        Raises:
            LLMServiceException: If API call fails after max retries
        """
        max_retries = 3
        base_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                # Build the full prompt with all context
                full_prompt = self._build_prompt(message, context, history, system_prompt)

                logger.debug(f"Sending request to Gemini (prompt length: {len(full_prompt)})")

                # Configure generation parameters
                generate_config = types.GenerateContentConfig(
                    max_output_tokens=settings.llm_max_tokens,
                    temperature=settings.llm_temperature,
                )

                # Add system instruction if provided
                if system_prompt:
                    generate_config.system_instruction = system_prompt

                # Generate response
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=full_prompt,
                    config=generate_config
                )

                if not response or not response.text:
                    raise LLMServiceException("Empty response from Gemini API")

                logger.info(f"✅ Gemini response received (length: {len(response.text)})")
                return response.text

            except LLMServiceException:
                raise
            except Exception as e:
                error_str = str(e).lower()
                is_rate_limit = any(code in error_str for code in ['429', 'resource_exhausted', 'quota'])

                if is_rate_limit and attempt < max_retries - 1:
                    # Calculate exponential backoff delay
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"⚠️ Gemini rate limit hit (attempt {attempt + 1}/{max_retries}). "
                                   f"Retrying in {delay}s... Error: {e}")
                    time.sleep(delay)
                else:
                    # Either not a rate limit error or reached max retries
                    if is_rate_limit:
                        logger.error(f"❌ Gemini rate limit reached after {max_retries} attempts: {e}")
                    else:
                        logger.error(f"❌ Gemini API error: {e}")
                    raise LLMServiceException(
                        message="Failed to generate response with Gemini",
                        provider="gemini",
                        original_error=e
                    )

    def _build_prompt(
        self,
        message: str,
        context: Optional[str],
        history: Optional[List[Dict]],
        system_prompt: Optional[str]
    ) -> str:
        """
        Build comprehensive prompt with all available context.

        Combines system prompt, RAG context, conversation history,
        and current message into a well-structured prompt.
        """
        parts = []

        # Note: System prompt is handled separately via config.system_instruction
        # but we can also include it in the content for clarity

        # RAG context (knowledge base)
        if context:
            parts.append(f"=== KIẾN THỨC THAM KHẢO ===\n{context}\n")

        # Conversation history (for multi-turn context)
        if history and len(history) > 0:
            parts.append("=== LỊCH SỬ HỘI THOẠI GẦN ĐÂY ===")
            for item in history:
                role = "👤 Người dùng" if item['role'] == 'user' else "🤖 Trợ lý"
                parts.append(f"{role}: {item['content']}")
            parts.append("")  # Empty line separator

        # Current message
        parts.append(f"=== CÂU HỎI HIỆN TẠI ===\n{message}")

        full_prompt = "\n\n".join(parts)

        logger.debug(f"Built prompt with {len(parts)} sections")
        return full_prompt

    def health_check(self) -> bool:
        """
        Check if Gemini service is accessible.

        Returns:
            bool: True if service is working, False otherwise
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents="Test"
            )
            return True
        except Exception as e:
            logger.warning(f"Gemini health check failed: {e}")
            return False

    def get_model_info(self) -> Dict[str, str]:
        """
        Get information about current Gemini configuration.

        Returns:
            Dict with provider, model, and status information
        """
        return {
            'provider': 'gemini',
            'model': self.model_name,
            'status': 'active' if self.health_check() else 'inactive'
        }


def get_gemini_service() -> GeminiService:
    """
    Factory function to get or create Gemini service instance.

    Returns:
        GeminiService: Configured Gemini service instance
    """
    return GeminiService()


# Global instance (lazy initialization)
_gemini_service: Optional[GeminiService] = None


def get_gemini_service_singleton() -> GeminiService:
    """
    Get or create global Gemini service singleton instance.

    Returns:
        GeminiService: Global Gemini service instance
    """
    global _gemini_service
    if _gemini_service is None:
        logger.info("Initializing global Gemini service...")
        _gemini_service = GeminiService()
    return _gemini_service
