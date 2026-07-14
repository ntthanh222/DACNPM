"""
LLM service package for hybrid chatbot.

This package provides LLM integration for multiple providers:
- Gemini (Google)
- OpenAI (GPT models)
- Claude (Anthropic)

Usage:
    from backend.llm.gemini_service import GeminiService
    from backend.llm.base_service import LLMService
"""

from backend.llm.base_service import LLMService, LLMServiceException

__all__ = ['LLMService', 'LLMServiceException']
