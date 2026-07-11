"""
LLM service package for hybrid chatbot.

This package provides LLM integration for multiple providers:
- Gemini (Google)
- OpenAI (GPT models)
- Claude (Anthropic)

Usage:
    from llm.gemini_service import GeminiService
    from llm.base_service import LLMService
"""

from llm.base_service import LLMService, LLMServiceException

__all__ = ['LLMService', 'LLMServiceException']
