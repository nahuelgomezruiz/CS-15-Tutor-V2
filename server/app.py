"""Flask application factory."""

from flask import Flask
from flask_cors import CORS

from core.config import settings
from core.orchestrator import Orchestrator
from core.auth_service import AuthService
from adapters.llm import get_llm_adapter
from adapters.database import get_database_adapter


def create_app(config_override: dict = None) -> Flask:
    """
    Create and configure the Flask application.
    
    Args:
        config_override: Optional configuration overrides
    
    Returns:
        Configured Flask application
    """
    app = Flask(__name__)
    
    # Apply configuration overrides
    if config_override:
        app.config.update(config_override)
    
    # Configure CORS
    CORS(app, origins=settings.cors_origins)
    
    # Initialize adapters
    llm_adapter = get_llm_adapter(settings.llm_provider)
    db_adapter = get_database_adapter(settings.database_provider)
    auth_service = AuthService()
    
    # Initialize orchestrator
    orchestrator = Orchestrator(
        llm_adapter=llm_adapter,
        db_adapter=db_adapter
    )
    
    # Store in app config for route access
    app.config['llm_adapter'] = llm_adapter
    app.config['db_adapter'] = db_adapter
    app.config['auth_service'] = auth_service
    app.config['orchestrator'] = orchestrator
    
    # Register blueprints
    from server.routes.chat import chat_bp
    from server.routes.auth import auth_bp
    from server.routes.health import health_bp
    
    app.register_blueprint(chat_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(health_bp)
    
    return app


def main():
    """Run the application."""
    print("Starting CS-15 Tutor API server...")
    print(f"LLM Provider: {settings.llm_provider}")
    print(f"Database Provider: {settings.database_provider}")
    print(f"Development Mode: {settings.development_mode}")
    print()
    print("Available endpoints:")
    print("   POST /api - Main chat endpoint")
    print("   POST /api/stream - Streaming chat endpoint")
    print("   GET /health - Health check")
    print("   GET/POST /vscode-auth - VSCode authentication")
    print("   POST /vscode-direct-auth - VSCode direct authentication")
    print("   GET /vscode-auth-status - VSCode auth status")
    print("   GET /analytics - System analytics")
    print("   GET /health-status - User health points status")
    print()
    
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=settings.debug)


if __name__ == '__main__':
    main()
