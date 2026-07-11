"""
Knowledge Base Package (Phase 3.2)

Provides semantic graph search capabilities for complex security queries.
"""
from .graph_client import SecurityKnowledgeGraph, get_knowledge_base_singleton

__all__ = ['SecurityKnowledgeGraph', 'get_knowledge_base_singleton']
