"""Google Gemini LLM Adapter."""

import os
from typing import Generator, List, Dict, Any, Optional

from adapters.llm.base import BaseLLMAdapter


class GeminiAdapter(BaseLLMAdapter):
    """
    Adapter for Google's Gemini models.
    
    Requires the GEMINI_API_KEY environment variable to be set.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini adapter.
        
        Args:
            api_key: Gemini API key. If not provided, uses GEMINI_API_KEY env var.
        """
        self._api_key = api_key or os.getenv('GEMINI_API_KEY')
        self._client = None
        
        if self._api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self._api_key)
                self._genai = genai
                self._client = True  # Flag that we're configured
            except ImportError:
                print("Warning: google-generativeai package not installed. Run: pip install google-generativeai")
    
    @property
    def name(self) -> str:
        return "gemini"
    
    @property
    def default_model(self) -> str:
        return "gemini-1.5-flash"
    
    def _convert_messages_to_gemini_format(
        self, 
        messages: List[Dict[str, str]], 
        system_prompt: Optional[str] = None
    ) -> tuple:
        """Convert OpenAI-style messages to Gemini format."""
        history = []
        extracted_system = system_prompt
        user_query = ""
        
        for msg in messages:
            role = msg.get('role', '')
            content = msg.get('content', '')
            
            if role == 'system':
                if not extracted_system:
                    extracted_system = content
            elif role == 'user':
                user_query = content
                history.append({
                    'role': 'user',
                    'parts': [content]
                })
            elif role == 'assistant':
                history.append({
                    'role': 'model',
                    'parts': [content]
                })
        
        # Remove the last user message from history since we'll send it as the query
        if history and history[-1]['role'] == 'user':
            history = history[:-1]
        
        return history, extracted_system, user_query
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate a response using Gemini's API."""
        if not self._client:
            raise RuntimeError("Gemini client not initialized. Check API key and google-generativeai package.")
        
        model_name = model or self.default_model
        
        history, extracted_system, user_query = self._convert_messages_to_gemini_format(
            messages, system_prompt
        )
        
        try:
            # Configure generation settings
            generation_config = {
                'temperature': temperature,
            }
            if max_tokens:
                generation_config['max_output_tokens'] = max_tokens
            
            # Create the model with system instruction
            gemini_model = self._genai.GenerativeModel(
                model_name=model_name,
                system_instruction=extracted_system,
                generation_config=generation_config,
            )
            
            # Start chat with history if available
            chat = gemini_model.start_chat(history=history)
            
            # Send the user query
            response = chat.send_message(user_query)
            
            return response.text
            
        except Exception as e:
            raise RuntimeError(f"Gemini API error: {e}")
    
    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Generator[str, None, None]:
        """Stream a response from Gemini's API."""
        if not self._client:
            raise RuntimeError("Gemini client not initialized. Check API key and google-generativeai package.")
        
        model_name = model or self.default_model
        
        history, extracted_system, user_query = self._convert_messages_to_gemini_format(
            messages, system_prompt
        )
        
        try:
            # Configure generation settings
            generation_config = {
                'temperature': temperature,
            }
            if max_tokens:
                generation_config['max_output_tokens'] = max_tokens
            
            # Create the model with system instruction
            gemini_model = self._genai.GenerativeModel(
                model_name=model_name,
                system_instruction=extracted_system,
                generation_config=generation_config,
            )
            
            # Start chat with history if available
            chat = gemini_model.start_chat(history=history)
            
            # Send the user query with streaming
            response = chat.send_message(user_query, stream=True)
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            raise RuntimeError(f"Gemini streaming error: {e}")
    
    def is_available(self) -> bool:
        """Check if Gemini is properly configured."""
        return self._client is not None
