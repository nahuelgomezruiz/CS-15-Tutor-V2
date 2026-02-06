"""Main Orchestrator for CS-15 Tutor chat handling."""

import os
import time
from typing import Dict, Any, List, Optional

from adapters.llm.base import BaseLLMAdapter
from adapters.database.base import BaseDatabaseAdapter
from core.rag_service import RAGService
from core.quality_checker import QualityChecker
from core.config import settings


class Orchestrator:
    """
    Main orchestrator for processing chat requests.
    
    Coordinates:
    - RAG retrieval
    - LLM generation
    - Quality checking
    - Database logging
    """
    
    def __init__(
        self,
        llm_adapter: BaseLLMAdapter,
        db_adapter: BaseDatabaseAdapter,
        rag_service: Optional[RAGService] = None,
        quality_checker: Optional[QualityChecker] = None
    ):
        """
        Initialize the orchestrator.
        
        Args:
            llm_adapter: LLM adapter for generation
            db_adapter: Database adapter for logging
            rag_service: RAG service (creates one if not provided)
            quality_checker: Quality checker (creates one if not provided)
        """
        self.llm = llm_adapter
        self.db = db_adapter
        self.rag = rag_service or RAGService()
        self.quality_checker = quality_checker or QualityChecker(llm_adapter)
        
        self._system_prompt = None
        self._load_system_prompt()
    
    def _load_system_prompt(self) -> None:
        """Load the system prompt from file."""
        prompt_path = settings.get_system_prompt_path()
        
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                self._system_prompt = f.read().strip()
                print(f"[Orchestrator] Loaded system prompt from {prompt_path}")
        except FileNotFoundError:
            print(f"[Orchestrator] Warning: system_prompt.txt not found at {prompt_path}")
            self._system_prompt = self._default_system_prompt()
        except IOError as e:
            print(f"[Orchestrator] Warning: Error reading system_prompt.txt: {e}")
            self._system_prompt = self._default_system_prompt()
    
    def _default_system_prompt(self) -> str:
        """Return default system prompt if file not found."""
        return "You are a friendly and brief Teaching Assistant (TA) for CS 15: Data Structures at Tufts University."
    
    @property
    def system_prompt(self) -> str:
        """Get the system prompt, reloading if in development mode."""
        if settings.development_mode:
            self._load_system_prompt()
        return self._system_prompt
    
    def process_query(
        self,
        message: str,
        conversation_id: str,
        conversation_history: List[Dict[str, str]],
        utln: str,
        platform: str,
        accumulated_rag_context: str = ""
    ) -> Dict[str, Any]:
        """
        Process a chat query with RAG retrieval and quality checking.
        
        Args:
            message: User's message
            conversation_id: Unique conversation identifier
            conversation_history: Previous messages in conversation
            utln: User's UTLN
            platform: Platform ('web' or 'vscode')
            accumulated_rag_context: Previously accumulated RAG context
        
        Returns:
            Response dict with:
            - response: Assistant's response
            - rag_context: RAG context used
            - conversation_id: Conversation ID
            - response_time_ms: Response time
            - metadata: Additional metadata
        """
        request_start_time = time.time()
        
        print(f"[Orchestrator] Processing message from {utln} ({platform}): {message[:50]}...")
        
        # Step 1: RAG retrieval
        raw_rag, formatted_rag = self.rag.retrieve_and_format(
            query=message,
            threshold=settings.rag_threshold,
            k=settings.rag_k
        )
        
        # Combine with accumulated context
        full_rag_context = accumulated_rag_context
        if formatted_rag:
            if full_rag_context:
                full_rag_context = full_rag_context + "\n\n" + formatted_rag
            else:
                full_rag_context = formatted_rag
        
        # Step 2: Generate quality-checked response
        final_response = self._generate_quality_checked_response(
            message=message,
            rag_context=full_rag_context,
            conversation_history=conversation_history
        )
        
        # Calculate response time
        response_time_ms = int((time.time() - request_start_time) * 1000)
        
        print(f"[Orchestrator] Generated response length: {len(final_response)}")
        print(f"[Orchestrator] Total request time: {response_time_ms}ms")
        
        return {
            "response": final_response,
            "rag_context": formatted_rag,
            "conversation_id": conversation_id,
            "response_time_ms": response_time_ms,
            "metadata": {
                "processing_stages": ["rag_retrieval", "quality_checked_generation"],
                "quality_checks_performed": True,
                "rag_context_used": bool(formatted_rag),
                "model_used": self.llm.default_model,
                "temperature": settings.default_temperature
            }
        }
    
    def _generate_quality_checked_response(
        self,
        message: str,
        rag_context: str,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """
        Generate response with quality checking and regeneration.
        
        Args:
            message: User's message
            rag_context: Formatted RAG context
            conversation_history: Previous messages
        
        Returns:
            Quality-checked response
        """
        # Initial generation
        response = self._generate_response(message, rag_context, conversation_history)
        
        # Quality check loop
        for attempt in range(settings.max_regeneration_attempts):
            score, feedback = self.quality_checker.check_quality(
                query=message,
                response=response,
                rag_context=rag_context
            )
            
            if score >= settings.quality_threshold:
                print(f"[Orchestrator] Quality check passed (score: {score})")
                return response
            else:
                print(f"[Orchestrator] Quality check failed (score: {score}): {feedback}")
                
                if attempt < settings.max_regeneration_attempts - 1:
                    # Generate enhanced prompt and regenerate
                    enhanced_message = self.quality_checker.generate_enhancement_prompt(
                        response, feedback
                    )
                    response = self._generate_response(
                        enhanced_message, rag_context, conversation_history
                    )
                else:
                    print("[Orchestrator] Max attempts reached, using last response")
                    return response
        
        return "I apologize, but I'm having trouble generating an appropriate response. Please try rephrasing your question."
    
    def _generate_response(
        self,
        message: str,
        rag_context: str,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """
        Generate a single response from the LLM.
        
        Args:
            message: User's message
            rag_context: Formatted RAG context
            conversation_history: Previous messages
        
        Returns:
            Generated response
        """
        # Build the query with RAG context
        query_with_context = f"student query: {message}"
        if rag_context:
            query_with_context += f"\n\n{rag_context}"
        
        # Calculate conversation context
        num_previous_pairs = (len(conversation_history) - 1) // 2 if conversation_history else 0
        
        try:
            # Build messages for the LLM
            messages = self.llm.format_messages(
                query=query_with_context,
                system_prompt=self.system_prompt,
                conversation_history=conversation_history
            )
            
            # Generate response
            response = self.llm.generate(
                messages=messages,
                temperature=settings.default_temperature,
                lastk=num_previous_pairs,  # NatLab-specific
                rag_usage=False,  # We handle RAG separately
            )
            
            return response
            
        except Exception as e:
            print(f"[Orchestrator] Error generating response: {e}")
            return "I apologize, but I encountered an error while generating a response. Please try again."
    
    def log_interaction(
        self,
        utln: str,
        conversation_id: str,
        query: str,
        response: str,
        platform: str,
        rag_context: str = None,
        response_time_ms: int = None
    ) -> Dict[str, Any]:
        """
        Log a complete interaction to the database.
        
        Args:
            utln: User's UTLN
            conversation_id: Conversation identifier
            query: User's query
            response: Assistant's response
            platform: Platform used
            rag_context: RAG context used
            response_time_ms: Response time
        
        Returns:
            Logging result with anonymous_id and metadata
        """
        try:
            # Get or create user
            user_data, conversation_count = self.db.get_or_create_anonymous_user(utln)
            
            # Get or create conversation
            conversation_data = self.db.get_or_create_conversation(
                conversation_id, user_data, platform
            )
            
            # Log the query
            self.db.log_message(
                conversation_data=conversation_data,
                message_type='query',
                content=query
            )
            
            # Log the response
            self.db.log_message(
                conversation_data=conversation_data,
                message_type='response',
                content=response,
                rag_context=rag_context,
                model_used=self.llm.default_model,
                temperature=settings.default_temperature,
                response_time_ms=response_time_ms
            )
            
            return {
                'anonymous_id': user_data['anonymous_id'],
                'conversation_id': conversation_id,
                'platform': platform,
                'is_new_conversation': conversation_data['message_count'] <= 2,
                'user_total_conversations': conversation_count
            }
            
        except Exception as e:
            print(f"[Orchestrator] Error logging interaction: {e}")
            return {}
