"""Health Points Service for rate limiting."""

from typing import Dict, Any, Tuple
from adapters.database.base import BaseDatabaseAdapter


class HealthPointsService:
    """
    Service for managing user health points (rate limiting).
    
    Health points regenerate over time:
    - Max: 12 points
    - Regeneration: 1 point per 3 minutes
    - Each query consumes 1 point
    """
    
    def __init__(self, db_adapter: BaseDatabaseAdapter):
        """
        Initialize the health points service.
        
        Args:
            db_adapter: Database adapter for persistence
        """
        self._db = db_adapter
    
    def get_status(self, user_id: int) -> Dict[str, Any]:
        """
        Get current health status for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            Health status dict with:
            - current_points: Current available points
            - max_points: Maximum points
            - can_query: Whether user can make a query
            - time_until_next_regen: Seconds until next point regenerates
        """
        return self._db.get_user_health_status(user_id)
    
    def can_query(self, user_id: int) -> bool:
        """
        Check if a user has enough health points to query.
        
        Args:
            user_id: User ID
        
        Returns:
            True if user can query, False otherwise
        """
        status = self.get_status(user_id)
        return status.get('can_query', False)
    
    def consume(self, user_id: int) -> Tuple[bool, int]:
        """
        Consume a health point for a query.
        
        Args:
            user_id: User ID
        
        Returns:
            Tuple of (success, remaining_points)
        """
        return self._db.consume_health_point(user_id)
    
    def regenerate(self, user_id: int) -> Dict[str, Any]:
        """
        Trigger health point regeneration for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            Updated health status
        """
        return self._db.regenerate_health_points(user_id)
