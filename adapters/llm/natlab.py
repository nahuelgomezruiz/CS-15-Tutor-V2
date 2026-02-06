"""NatLab LLM Adapter - wrapper for the existing LLMProxy API."""

import json
import os
import requests
from typing import Generator, List, Dict, Any, Optional

from adapters.llm.base import BaseLLMAdapter


class NatLabAdapter(BaseLLMAdapter):
    """
    Adapter for the NatLab LLM Proxy API.
    
    This is the original LLM provider used by CS-15 Tutor,
    providing both generation and RAG retrieval capabilities.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the NatLab adapter.
        
        Args:
            config_path: Path to config.json file. If not provided,
                        looks for NATLAB_API_KEY and NATLAB_ENDPOINT env vars,
                        or falls back to config.json in current directory.
        """
        self._api_key = None
        self._endpoint = None
        self._load_config(config_path)
    
    def _load_config(self, config_path: Optional[str] = None):
        """Load API configuration from environment or config file."""
        # Try environment variables first
        self._api_key = os.getenv('NATLAB_API_KEY')
        self._endpoint = os.getenv('NATLAB_ENDPOINT')
        
        if self._api_key and self._endpoint:
            return
        
        # Fall back to config file
        config_paths = [
            config_path,
            'config.json',
            os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'natlab.json'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'responses-api-server', 'config.json'),
        ]
        
        for path in config_paths:
            if path and os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        config = json.load(f)
                        self._api_key = config.get('apiKey')
                        self._endpoint = config.get('endPoint')
                        if self._api_key and self._endpoint:
                            return
                except (json.JSONDecodeError, IOError):
                    continue
        
        if not self._api_key or not self._endpoint:
            raise ValueError(
                "NatLab configuration not found. Set NATLAB_API_KEY and NATLAB_ENDPOINT "
                "environment variables, or provide a config.json file."
            )
    
    @property
    def name(self) -> str:
        return "natlab"
    
    @property
    def default_model(self) -> str:
        return "4o-mini"
    
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
        Generate a response using the NatLab proxy.
        
        Additional kwargs:
            lastk: Number of previous conversation turns to include
            session_id: Session ID for conversation tracking
            rag_usage: Whether to use RAG (default False for generation)
        """
        model = model or self.default_model
        
        # Extract system prompt from messages if not provided separately
        if system_prompt is None:
            for msg in messages:
                if msg.get('role') == 'system':
                    system_prompt = msg.get('content', '')
                    break
        
        # Get the user query (last user message)
        query = ""
        for msg in reversed(messages):
            if msg.get('role') == 'user':
                query = msg.get('content', '')
                break
        
        headers = {
            'x-api-key': self._api_key,
            'request_type': 'call'
        }
        
        request_data = {
            'model': model,
            'system': system_prompt or '',
            'query': query,
            'temperature': temperature,
            'lastk': kwargs.get('lastk', 0),
            'session_id': kwargs.get('session_id'),
            'rag_threshold': kwargs.get('rag_threshold', 0.5),
            'rag_usage': kwargs.get('rag_usage', False),
            'rag_k': kwargs.get('rag_k', 0)
        }
        
        try:
            response = requests.post(self._endpoint, headers=headers, json=request_data)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('result', result.get('response', ''))
            else:
                raise RuntimeError(f"NatLab API error: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"NatLab request failed: {e}")
    
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
        NatLab doesn't support streaming, so we return the full response at once.
        """
        response = self.generate(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            **kwargs
        )
        yield response
    
    def retrieve(
        self,
        query: str,
        session_id: str = 'GenericSession',
        rag_threshold: float = 0.4,
        rag_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve RAG context from the NatLab proxy.
        
        This is a NatLab-specific method not part of the base interface.
        
        Args:
            query: Search query
            session_id: Session identifier
            rag_threshold: Relevance threshold
            rag_k: Number of results to retrieve
        
        Returns:
            List of retrieved context documents
        """
        headers = {
            'x-api-key': self._api_key,
            'request_type': 'retrieve'
        }
        
        request_data = {
            'query': query,
            'session_id': session_id,
            'rag_threshold': rag_threshold,
            'rag_k': rag_k
        }
        
        try:
            response = requests.post(self._endpoint, headers=headers, json=request_data)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"RAG retrieval error: {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"RAG retrieval failed: {e}")
            return []
    
    def is_available(self) -> bool:
        """Check if NatLab is properly configured."""
        return bool(self._api_key and self._endpoint)
