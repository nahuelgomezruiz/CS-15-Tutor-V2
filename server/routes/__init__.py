"""Route blueprints package."""

from server.routes.chat import chat_bp
from server.routes.auth import auth_bp
from server.routes.health import health_bp

__all__ = ['chat_bp', 'auth_bp', 'health_bp']
