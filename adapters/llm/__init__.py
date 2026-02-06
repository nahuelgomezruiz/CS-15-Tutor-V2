"""LLM Adapters package."""

from adapters.llm.base import BaseLLMAdapter
from adapters.llm.natlab import NatLabAdapter
from adapters.llm.openai_adapter import OpenAIAdapter
from adapters.llm.anthropic_adapter import AnthropicAdapter
from adapters.llm.gemini_adapter import GeminiAdapter


def get_llm_adapter(provider: str = None) -> BaseLLMAdapter:
    """
    Factory function to get the appropriate LLM adapter based on provider.
    
    Args:
        provider: LLM provider name ('natlab', 'openai', 'anthropic', 'gemini')
                 If None, uses LLM_PROVIDER environment variable, defaults to 'natlab'
    
    Returns:
        An instance of the appropriate LLM adapter
    """
    import os
    
    if provider is None:
        provider = os.getenv('LLM_PROVIDER', 'natlab').lower()
    
    adapters = {
        'natlab': NatLabAdapter,
        'openai': OpenAIAdapter,
        'anthropic': AnthropicAdapter,
        'gemini': GeminiAdapter,
    }
    
    adapter_class = adapters.get(provider)
    if adapter_class is None:
        raise ValueError(f"Unknown LLM provider: {provider}. Available: {list(adapters.keys())}")
    
    return adapter_class()


__all__ = [
    'BaseLLMAdapter',
    'NatLabAdapter', 
    'OpenAIAdapter',
    'AnthropicAdapter',
    'GeminiAdapter',
    'get_llm_adapter',
]
