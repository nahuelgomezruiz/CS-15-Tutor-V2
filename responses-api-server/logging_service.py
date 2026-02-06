from database import db_manager, AnonymousUser, Conversation
from typing import Optional, Dict, Any
import time
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TutorLoggingService:
    """
    Service for logging user queries and responses in the CS 15 tutor system.
    Handles user anonymization and conversation tracking.
    """
    
    def __init__(self):
        self.db_manager = db_manager
        logger.info("Tutor logging service initialized")
    
    def log_user_query(self, utln: str, conversation_id: str, query: str, 
                      platform: str = 'web', additional_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Log a user query with anonymization.
        
        Args:
            utln: Tufts University Login Name
            conversation_id: Unique conversation identifier
            query: User's query text
            platform: Platform used ('web' or 'vscode')
            additional_context: Optional metadata (IP, user agent, etc.)
        
        Returns:
            Dictionary with anonymous_id and conversation info
        """
        try:
            # Get or create anonymous user
            user_data, user_conversation_count = self.db_manager.get_or_create_anonymous_user(utln)
            
            # Get or create conversation
            conversation_data = self.db_manager.get_or_create_conversation(conversation_id, user_data, platform)
            
            # Log the query
            self.db_manager.log_message(
                conversation_data=conversation_data,
                message_type='query',
                content=query
            )
            
            logger.info(f"Logged query for user {user_data['anonymous_id']} in conversation {conversation_id} on {platform}")
            
            return {
                'anonymous_id': user_data['anonymous_id'],
                'conversation_id': conversation_id,
                'platform': platform,
                'is_new_conversation': conversation_data['message_count'] == 0,  # New conversation starts at 0
                'user_total_conversations': user_conversation_count
            }
            
        except Exception as e:
            logger.error(f"Error logging user query: {e}")
            return {}
    
    def log_assistant_response(self, conversation_id: str, response: str,
                             rag_context: str = None, model_used: str = '4o-mini',
                             temperature: float = 0.7, response_time_ms: int = None) -> bool:
        """
        Log an assistant response.
        
        Args:
            conversation_id: Unique conversation identifier
            response: Assistant's response text
            rag_context: RAG context used for the response
            model_used: Model used for generation
            temperature: Temperature setting used
            response_time_ms: Response time in milliseconds
        
        Returns:
            True if logged successfully, False otherwise
        """
        try:
            # Find the conversation
            db = self.db_manager.get_session()
            conversation = db.query(Conversation).filter(
                Conversation.conversation_id == conversation_id
            ).first()
            
            if not conversation:
                db.close()
                logger.warning(f"Conversation {conversation_id} not found for response logging")
                return False
            
            # Convert to data dict
            conversation_data = {
                'id': conversation.id,
                'conversation_id': conversation.conversation_id,
                'user_id': conversation.user_id,
                'platform': conversation.platform,
                'created_at': conversation.created_at,
                'last_message_at': conversation.last_message_at,
                'message_count': conversation.message_count,
                'is_active': conversation.is_active
            }
            db.close()
            
            # Log the response
            self.db_manager.log_message(
                conversation_data=conversation_data,
                message_type='response',
                content=response,
                rag_context=rag_context,
                model_used=model_used,
                temperature=temperature,
                response_time_ms=response_time_ms
            )
            
            logger.info(f"Logged response for conversation {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error logging assistant response: {e}")
            return False
    
    def log_conversation_interaction(self, utln: str, conversation_id: str, 
                                   query: str, response: str, platform: str = 'web',
                                   rag_context: str = None, model_used: str = '4o-mini', 
                                   temperature: float = 0.7, response_time_ms: int = None) -> Dict[str, Any]:
        """
        Convenience method to log both query and response in one call.
        
        Args:
            utln: Tufts University Login Name
            conversation_id: Unique conversation identifier
            query: User's query text
            response: Assistant's response text
            platform: Platform used ('web' or 'vscode')
            rag_context: RAG context used for the response
            model_used: Model used for generation
            temperature: Temperature setting used
            response_time_ms: Response time in milliseconds
        
        Returns:
            Dictionary with logging results and user analytics
        """
        start_time = time.time()
        
        # Log the query
        query_result = self.log_user_query(utln, conversation_id, query, platform)
        
        # Log the response
        response_logged = self.log_assistant_response(
            conversation_id, response, rag_context, 
            model_used, temperature, response_time_ms
        )
        
        end_time = time.time()
        logging_time_ms = int((end_time - start_time) * 1000)
        
        result = {
            'query_logged': bool(query_result),
            'response_logged': response_logged,
            'logging_time_ms': logging_time_ms,
            **query_result
        }
        
        logger.info(f"Logged complete interaction for {query_result.get('anonymous_id', 'unknown')} "
                   f"on {platform} in {logging_time_ms}ms")
        
        return result
    
    def get_user_statistics(self, utln: str) -> Dict[str, Any]:
        """
        Get usage statistics for a specific user (by UTLN).
        
        Args:
            utln: Tufts University Login Name
        
        Returns:
            Dictionary with user statistics
        """
        try:
            user_data, conversation_count = self.db_manager.get_or_create_anonymous_user(utln)
            # Create a mock user object with the needed data for analytics
            class MockUser:
                def __init__(self, data):
                    self.id = data['id']
                    self.anonymous_id = data['anonymous_id']
                    self.created_at = data['created_at']
                    self.last_active = data['last_active']
                    
            mock_user = MockUser(user_data)
            return self.db_manager.get_user_analytics(mock_user)
        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            return {}
    
    def get_conversation_history(self, conversation_id: str, 
                               include_rag_context: bool = False) -> Dict[str, Any]:
        """
        Get the complete history of a conversation.
        
        Args:
            conversation_id: Unique conversation identifier
            include_rag_context: Whether to include RAG context in the response
        
        Returns:
            Dictionary with conversation history
        """
        try:
            db = self.db_manager.get_session()
            
            conversation = db.query(Conversation).filter(
                Conversation.conversation_id == conversation_id
            ).first()
            
            if not conversation:
                return {'error': 'Conversation not found'}
            
            messages = []
            for msg in conversation.messages:
                message_data = {
                    'type': msg.message_type,
                    'content': msg.content,
                    'timestamp': msg.created_at.isoformat(),
                    'model_used': msg.model_used,
                    'temperature': msg.temperature,
                    'response_time_ms': msg.response_time_ms
                }
                
                if include_rag_context and msg.rag_context:
                    message_data['rag_context'] = msg.rag_context
                
                messages.append(message_data)
            
            result = {
                'conversation_id': conversation_id,
                'anonymous_user_id': conversation.user.anonymous_id,
                'platform': conversation.platform,
                'created_at': conversation.created_at.isoformat(),
                'last_message_at': conversation.last_message_at.isoformat(),
                'message_count': conversation.message_count,
                'messages': messages
            }
            
            db.close()
            return result
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return {'error': str(e)}
    
    def get_system_analytics(self) -> Dict[str, Any]:
        """
        Get overall system usage analytics.
        
        Returns:
            Dictionary with system-wide statistics
        """
        try:
            return self.db_manager.get_system_analytics()
        except Exception as e:
            logger.error(f"Error getting system analytics: {e}")
            return {}
    
    def analyze_user_engagement(self, days_back: int = 30) -> Dict[str, Any]:
        """
        Analyze user engagement patterns.
        
        Args:
            days_back: Number of days to look back for analysis
        
        Returns:
            Dictionary with engagement analytics
        """
        try:
            db = self.db_manager.get_session()
            
            # Get users who started conversations in the time period
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            users_with_multiple_conversations = db.execute("""
                SELECT anonymous_users.anonymous_id, COUNT(conversations.id) as conv_count,
                       conversations.platform
                FROM anonymous_users 
                JOIN conversations ON anonymous_users.id = conversations.user_id
                WHERE conversations.created_at >= :cutoff_date
                GROUP BY anonymous_users.id, conversations.platform
                HAVING COUNT(conversations.id) > 1
            """, {'cutoff_date': cutoff_date}).fetchall()
            
            total_users_in_period = db.execute("""
                SELECT COUNT(DISTINCT anonymous_users.id)
                FROM anonymous_users 
                JOIN conversations ON anonymous_users.id = conversations.user_id
                WHERE conversations.created_at >= :cutoff_date
            """, {'cutoff_date': cutoff_date}).scalar()
            
            returning_users = len(users_with_multiple_conversations)
            return_rate = (returning_users / total_users_in_period * 100) if total_users_in_period > 0 else 0
            
            db.close()
            
            return {
                'period_days': days_back,
                'total_users_in_period': total_users_in_period,
                'returning_users': returning_users,
                'return_rate_percentage': round(return_rate, 2),
                'users_with_multiple_conversations': [
                    {'anonymous_id': row[0], 'conversation_count': row[1], 'platform': row[2]} 
                    for row in users_with_multiple_conversations
                ]
            }
            
        except Exception as e:
            logger.error(f"Error analyzing user engagement: {e}")
            return {}

# Global logging service instance
logging_service = TutorLoggingService() 