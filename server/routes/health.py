"""Health check and analytics routes."""

from flask import Blueprint, request, jsonify, current_app

health_bp = Blueprint('health', __name__)


def get_auth():
    """Get the auth service from app context."""
    return current_app.config['auth_service']


def get_db():
    """Get the database adapter from app context."""
    return current_app.config['db_adapter']


@health_bp.route('/', methods=['GET'])
def root():
    """Root endpoint - API information."""
    return jsonify({
        "name": "CS-15 Tutor API",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "chat": "POST /api",
            "chat_stream": "POST /api/stream",
            "health": "GET /health",
            "health_status": "GET /health-status",
            "analytics": "GET /analytics",
            "vscode_auth": "GET/POST /vscode-auth",
            "vscode_direct_auth": "POST /vscode-direct-auth"
        },
        "documentation": "See README.md for full API documentation"
    }), 200


@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200


@health_bp.route('/health-status', methods=['GET'])
def health_status_endpoint():
    """Get user's health points status."""
    try:
        auth = get_auth()
        db = get_db()
        
        # Authenticate request
        utln, platform = auth.authenticate_request(request)
        if not utln:
            return jsonify({"error": "Authentication required"}), 401
        
        # Get user data
        user_data, _ = db.get_or_create_anonymous_user(utln)
        
        # Get health status
        health_status = db.get_user_health_status(user_data['id'])
        
        return jsonify(health_status)
        
    except Exception as e:
        print(f"[Health] Error getting health status: {e}")
        return jsonify({"error": "Health status error"}), 500


@health_bp.route('/analytics', methods=['GET'])
def analytics_endpoint():
    """Get system analytics (admin endpoint)."""
    try:
        auth = get_auth()
        db = get_db()
        
        # Authenticate request
        utln, platform = auth.authenticate_request(request)
        if not utln:
            return jsonify({"error": "Authentication required"}), 401
        
        # Get analytics
        analytics = db.get_system_analytics()
        
        return jsonify({
            "system_analytics": analytics
        })
        
    except Exception as e:
        print(f"[Health] Error getting analytics: {e}")
        return jsonify({"error": "Analytics error"}), 500
