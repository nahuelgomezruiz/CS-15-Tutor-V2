"""Authentication routes."""

import re
import urllib.parse
from flask import Blueprint, request, jsonify, current_app

auth_bp = Blueprint('auth', __name__)


def get_auth():
    """Get the auth service from app context."""
    return current_app.config['auth_service']


@auth_bp.route('/vscode-auth', methods=['GET', 'POST'])
def vscode_auth_endpoint():
    """Handle VSCode extension authentication."""
    try:
        auth = get_auth()
        
        if request.method == 'GET':
            session_id = request.args.get('session_id')
            
            if not session_id:
                # VSCode extension requesting a new session ID
                login_url = auth.generate_vscode_login_url('http://127.0.0.1:3000')
                parsed_url = urllib.parse.urlparse(login_url)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                session_id = query_params.get('session_id', [None])[0]
                
                if session_id:
                    return jsonify({
                        "session_id": session_id,
                        "login_url": login_url
                    })
                else:
                    return jsonify({"error": "Failed to generate session"}), 500
            else:
                # Web browser accessing the authentication page
                return jsonify({
                    "message": "VSCode authentication pending",
                    "session_id": session_id,
                    "instructions": "Please authenticate via the web interface"
                })
        
        elif request.method == 'POST':
            # Handle authentication callback
            data = request.get_json()
            session_id = data.get('session_id')
            
            # Get UTLN from web authentication
            utln, platform = auth.authenticate_request(request)
            if not utln:
                return jsonify({"error": "Authentication required"}), 401
            
            # Create VSCode token
            token = auth.handle_vscode_login_callback(session_id, utln)
            if token:
                return jsonify({"token": token, "utln": utln})
            else:
                return jsonify({"error": "Authentication failed"}), 401
                
    except Exception as e:
        print(f"[Auth] Error in VSCode auth: {e}")
        return jsonify({"error": "Authentication error"}), 500


@auth_bp.route('/vscode-direct-auth', methods=['POST'])
def vscode_direct_auth():
    """Handle direct VSCode authentication with credentials."""
    try:
        auth = get_auth()
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON data required"}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        auth_method = data.get('auth_method', 'ldap')
        
        if not username:
            return jsonify({"error": "Username is required"}), 400
        
        # Check if this is a username-only auth request
        is_username_only_auth = (auth_method == 'username_only' or 
                                request.headers.get('X-Development-Mode') == 'true')
        
        if is_username_only_auth:
            # Username-only authentication for VSCode extension
            if len(username) >= 3 and re.match(r'^[a-zA-Z][a-zA-Z0-9]{2,15}$', username):
                token = auth.create_vscode_auth_token(username.lower())
                if token:
                    print(f"[Auth] VSCode username-only auth successful for: {username}")
                    return jsonify({
                        "success": True,
                        "token": token,
                        "username": username.lower(),
                        "message": "Authentication successful"
                    })
                else:
                    return jsonify({
                        "success": False,
                        "error": "Failed to create authentication token"
                    }), 500
            else:
                return jsonify({
                    "success": False,
                    "error": "Invalid username format"
                }), 401
        else:
            # Original LDAP authentication
            if not password:
                return jsonify({"error": "Password is required for LDAP authentication"}), 400
            
            token = auth.authenticate_vscode_user(username, password)
            
            if token:
                return jsonify({
                    "success": True,
                    "token": token,
                    "username": username.lower(),
                    "message": "Authentication successful"
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Invalid credentials or user not authorized for CS 15"
                }), 401
            
    except Exception as e:
        print(f"[Auth] Error in direct VSCode auth: {e}")
        return jsonify({"error": "Authentication error"}), 500


@auth_bp.route('/vscode-auth-status', methods=['GET'])
def vscode_auth_status():
    """Check VSCode authentication status."""
    try:
        auth = get_auth()
        
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({"error": "Missing session_id"}), 400
        
        status = auth.get_vscode_session_status(session_id)
        return jsonify(status)
        
    except Exception as e:
        print(f"[Auth] Error checking auth status: {e}")
        return jsonify({"error": "Status check failed"}), 500
