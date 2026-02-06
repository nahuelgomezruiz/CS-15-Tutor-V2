"""OpenAI LLM Adapter."""

import os
from typing import Generator, List, Dict, Any, Optional

from adapters.llm.base import BaseLLMAdapter


class OpenAIAdapter(BaseLLMAdapter):
    """
    Adapter for OpenAI's GPT models.
    
    Requires the OPENAI_API_KEY environment variable to be set.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the OpenAI adapter.
        
        Args:
            api_key: OpenAI API key. If not provided, uses OPENAI_API_KEY env var.
        """
        self._api_key = api_key or os.getenv('OPENAI_API_KEY')
        self._client = None
        
        if self._api_key:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self._api_key)
            except ImportError:
                print("Warning: openai package not installed. Run: pip install openai")
    
    @property
    def name(self) -> str:
        return "openai"
    
    @property
    def default_model(self) -> str:
        return "gpt-4o-mini"
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate a response using OpenAI's API."""
        if not self._client:
            raise RuntimeError("OpenAI client not initialized. Check API key and openai package.")
        
        model = model or self.default_model
        
        # Prepend system prompt if provided and not already in messages
        formatted_messages = list(messages)
        if system_prompt and not any(m.get('role') == 'system' for m in formatted_messages):
            formatted_messages.insert(0, {"role": "system", "content": system_prompt})
        
        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            return response.choices[0].message.content or ""
            
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}")
    
    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Generator[str, None, None]:
        """Stream a response from OpenAI's API."""
        if not self._client:
            raise RuntimeError("OpenAI client not initialized. Check API key and openai package.")
        
        model = model or self.default_model
        
        # Prepend system prompt if provided and not already in messages
        formatted_messages = list(messages)
        if system_prompt and not any(m.get('role') == 'system' for m in formatted_messages):
            formatted_messages.insert(0, {"role": "system", "content": system_prompt})
        
        try:
            stream = self._client.chat.completions.create(
                model=model,
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            raise RuntimeError(f"OpenAI streaming error: {e}")
    
    def is_available(self) -> bool:
        """Check if OpenAI is properly configured."""
        return self._client is not None
