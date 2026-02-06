"""Adapters package for LLM and Database integrations."""

from adapters.llm import get_llm_adapter
from adapters.database import get_database_adapter

__all__ = ['get_llm_adapter', 'get_database_adapter']
