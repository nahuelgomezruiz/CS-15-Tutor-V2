"""Anthropic LLM Adapter."""

import os
from typing import Generator, List, Dict, Any, Optional

from adapters.llm.base import BaseLLMAdapter


class AnthropicAdapter(BaseLLMAdapter):
    """
    Adapter for Anthropic's Claude models.
    
    Requires the ANTHROPIC_API_KEY environment variable to be set.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Anthropic adapter.
        
        Args:
            api_key: Anthropic API key. If not provided, uses ANTHROPIC_API_KEY env var.
        """
        self._api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self._client = None
        
        if self._api_key:
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self._api_key)
            except ImportError:
                print("Warning: anthropic package not installed. Run: pip install anthropic")
    
    @property
    def name(self) -> str:
        return "anthropic"
    
    @property
    def default_model(self) -> str:
        return "claude-3-5-sonnet-20241022"
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate a response using Anthropic's API."""
        if not self._client:
            raise RuntimeError("Anthropic client not initialized. Check API key and anthropic package.")
        
        model = model or self.default_model
        max_tokens = max_tokens or 4096
        
        # Extract system prompt from messages if not provided separately
        formatted_messages = []
        extracted_system = system_prompt
        
        for msg in messages:
            if msg.get('role') == 'system':
                if not extracted_system:
                    extracted_system = msg.get('content', '')
            else:
                formatted_messages.append(msg)
        
        try:
            response = self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=extracted_system or "",
                messages=formatted_messages,
                temperature=temperature,
            )
            
            # Extract text from content blocks
            return "".join(
                block.text for block in response.content 
                if hasattr(block, 'text')
            )
            
        except Exception as e:
            raise RuntimeError(f"Anthropic API error: {e}")
    
    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Generator[str, None, None]:
        """Stream a response from Anthropic's API."""
        if not self._client:
            raise RuntimeError("Anthropic client not initialized. Check API key and anthropic package.")
        
        model = model or self.default_model
        max_tokens = max_tokens or 4096
        
        # Extract system prompt from messages if not provided separately
        formatted_messages = []
        extracted_system = system_prompt
        
        for msg in messages:
            if msg.get('role') == 'system':
                if not extracted_system:
                    extracted_system = msg.get('content', '')
            else:
                formatted_messages.append(msg)
        
        try:
            with self._client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                system=extracted_system or "",
                messages=formatted_messages,
                temperature=temperature,
            ) as stream:
                for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            raise RuntimeError(f"Anthropic streaming error: {e}")
    
    def is_available(self) -> bool:
        """Check if Anthropic is properly configured."""
        return self._client is not None
