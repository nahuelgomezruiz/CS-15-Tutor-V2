"""Base Database Adapter interface."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime


class BaseDatabaseAdapter(ABC):
    """
    Abstract base class for all database adapters.
    
    All database adapters must implement this interface to ensure
    consistent behavior across different database providers.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the database provider."""
        pass
    
    @abstractmethod
    def get_or_create_anonymous_user(self, utln: str) -> Tuple[Dict[str, Any], int]:
        """
        Get or create an anonymous user for a given UTLN.
        
        Args:
            utln: Tufts University Login Name
        
        Returns:
            Tuple of (user_data dict, conversation_count)
        """
        pass
    
    @abstractmethod
    def get_or_create_conversation(
        self, 
        conversation_id: str, 
        user_data: Dict[str, Any], 
        platform: str = 'web'
    ) -> Dict[str, Any]:
        """
        Get or create a conversation.
        
        Args:
            conversation_id: Unique conversation identifier
            user_data: User data dict from get_or_create_anonymous_user
            platform: Platform used ('web' or 'vscode')
        
        Returns:
            Conversation data dict
        """
        pass
    
    @abstractmethod
    def log_message(
        self,
        conversation_data: Dict[str, Any],
        message_type: str,
        content: str,
        rag_context: Optional[str] = None,
        model_used: Optional[str] = None,
        temperature: Optional[float] = None,
        response_time_ms: Optional[int] = None
    ) -> None:
        """
        Log a message (query or response).
        
        Args:
            conversation_data: Conversation data dict
            message_type: 'query' or 'response'
            content: Message content
            rag_context: RAG context used (for responses)
            model_used: Model used for generation
            temperature: Temperature setting
            response_time_ms: Response time in milliseconds
        """
        pass
    
    @abstractmethod
    def get_or_create_health_points(self, user_id: int) -> Dict[str, Any]:
        """
        Get or create health points for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            Health points data dict
        """
        pass
    
    @abstractmethod
    def regenerate_health_points(self, user_id: int) -> Dict[str, Any]:
        """
        Regenerate health points based on time elapsed.
        
        Args:
            user_id: User ID
        
        Returns:
            Updated health status dict
        """
        pass
    
    @abstractmethod
    def consume_health_point(self, user_id: int) -> Tuple[bool, int]:
        """
        Consume a health point for a query.
        
        Args:
            user_id: User ID
        
        Returns:
            Tuple of (success, remaining_points)
        """
        pass
    
    @abstractmethod
    def get_user_health_status(self, user_id: int) -> Dict[str, Any]:
        """
        Get current health status for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            Health status dict with current_points, max_points, can_query, time_until_next_regen
        """
        pass
    
    @abstractmethod
    def get_system_analytics(self) -> Dict[str, Any]:
        """
        Get overall system analytics.
        
        Returns:
            System analytics dict
        """
        pass
    
    def is_available(self) -> bool:
        """
        Check if the database is properly configured and available.
        
        Returns:
            True if the database can be used, False otherwise
        """
        return True
