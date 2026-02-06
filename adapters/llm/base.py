"""Base LLM Adapter interface."""

from abc import ABC, abstractmethod
from typing import Generator, List, Dict, Any, Optional


class BaseLLMAdapter(ABC):
    """
    Abstract base class for all LLM adapters.
    
    All LLM adapters must implement this interface to ensure
    consistent behavior across different providers.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the LLM provider."""
        pass
    
    @property
    @abstractmethod
    def default_model(self) -> str:
        """Return the default model for this provider."""
        pass
    
    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            model: Model identifier (uses default if not specified)
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response
            system_prompt: Optional system prompt to prepend
            **kwargs: Additional provider-specific parameters
        
        Returns:
            Generated text response
        """
        pass
    
    @abstractmethod
    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Stream a response from the LLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            model: Model identifier (uses default if not specified)
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response
            system_prompt: Optional system prompt to prepend
            **kwargs: Additional provider-specific parameters
        
        Yields:
            Generated text chunks as they become available
        """
        pass
    
    def format_messages(
        self, 
        query: str, 
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """
        Helper to format messages for the LLM.
        
        Args:
            query: The user's query
            system_prompt: Optional system prompt
            conversation_history: Optional previous messages
        
        Returns:
            Formatted list of messages
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        if conversation_history:
            # Skip any existing system messages in history
            for msg in conversation_history:
                if msg.get("role") != "system":
                    messages.append(msg)
        
        messages.append({"role": "user", "content": query})
        
        return messages
    
    def is_available(self) -> bool:
        """
        Check if this adapter is properly configured and available.
        
        Returns:
            True if the adapter can be used, False otherwise
        """
        return True
