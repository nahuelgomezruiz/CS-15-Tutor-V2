from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import os
import json
import re
from llmproxy import generate, retrieve
from typing import Dict, List
import time
import urllib.parse

# Import our new services
from auth_service import auth_service
from logging_service import logging_service
from database import db_manager
from enhanced_chat_handler import EnhancedChatHandler

def escape_for_json(text: str) -> str:
    """
    Escape characters in text to ensure JSON compatibility for LLMProxy API calls.
    
    This function handles the escaping requirements mentioned in the LLMProxy documentation
    to prevent JSON parsing errors when text contains unescaped quotes or HTML tags.
    
    Args:
        text (str): The input text that may contain characters needing escaping
        
    Returns:
        str: The escaped text safe for JSON encoding
    """
    if not isinstance(text, str):
        return str(text)
    
    # Escape backslashes first (must be done before escaping quotes)
    escaped = text.replace('\\', '\\\\')
    
    # Escape double quotes
    escaped = escaped.replace('"', '\\"')
    
    # Escape other control characters that could break JSON
    escaped = escaped.replace('\n', '\\n')
    escaped = escaped.replace('\r', '\\r')
    escaped = escaped.replace('\t', '\\t')
    escaped = escaped.replace('\b', '\\b')
    escaped = escaped.replace('\f', '\\f')
    
    return escaped

app = Flask(__name__)
CORS(app, origins=[
    'https://www.eecs.tufts.edu',
    'https://eecs.tufts.edu', 
    'https://cs-15-tutor.onrender.com',
    'https://www.cs.tufts.edu',
    'https://cs.tufts.edu',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:5000',
    'http://127.0.0.1:5000'
])  # Enable CORS for specific origins

# Store conversations in memory (key is conversationId)
conversations: Dict[str, List[Dict[str, str]]] = {}

# Store accumulated RAG context for each conversation (key is conversationId)
conversation_rag_context: Dict[str, List[Dict]] = {}

# Cache the system prompt at startup to avoid file I/O on every new conversation
CACHED_SYSTEM_PROMPT = None

# Enhanced chat handler instance
enhanced_handler = EnhancedChatHandler()

# Simple accumulator for formatted RAG context strings per conversation
formatted_rag_accumulator: Dict[str, str] = {}

def load_system_prompt() -> str:
    """Load the system prompt from cache or file if not cached, or reload if in development mode"""
    global CACHED_SYSTEM_PROMPT
    
    # Check if we're in development mode
    development_mode = os.getenv('DEVELOPMENT_MODE', '').lower() == 'true'
    
    if CACHED_SYSTEM_PROMPT is None or development_mode:
        prompt_path = os.path.join(os.path.dirname(__file__), "system_prompt.txt")
        with open(prompt_path, "r") as f:
            CACHED_SYSTEM_PROMPT = f.read().strip()
        
        if development_mode:
            print("🔄 System prompt reloaded from file (development mode)")
        else:
            print("📄 System prompt loaded and cached")
    
    return CACHED_SYSTEM_PROMPT

# Preload system prompt at startup
load_system_prompt()



"""
name:        health_check
description: endpoint to check if the server is running
parameters:  none
returns:     a json object with a status key and a value of "healthy"
"""
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

"""
name:        vscode_auth_endpoint
description: endpoint for VSCode extension authentication
parameters:  none (uses query parameters)
returns:     authentication status or redirect
"""
@app.route('/vscode-auth', methods=['GET', 'POST'])
def vscode_auth_endpoint():
    """Handle VSCode extension authentication"""
    try:
        if request.method == 'GET':
            session_id = request.args.get('session_id')
            
            if not session_id:
                # VSCode extension requesting a new session ID
                login_url = auth_service.generate_vscode_login_url('http://127.0.0.1:3000')
                # Extract session_id from the URL
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
            utln, platform = auth_service.authenticate_request(request)
            if not utln:
                return jsonify({"error": "Authentication required"}), 401
            
            # Create VSCode token
            token = auth_service.handle_vscode_login_callback(session_id, utln)
            if token:
                return jsonify({"token": token, "utln": utln})
            else:
                return jsonify({"error": "Authentication failed"}), 401
                
    except Exception as e:
        print(f"❌ Error in VSCode auth: {e}")
        return jsonify({"error": "Authentication error"}), 500

"""
name:        vscode_direct_auth
description: endpoint for direct VSCode authentication with username/password
parameters:  username and password in JSON body
returns:     JWT token if successful
"""
@app.route('/vscode-direct-auth', methods=['POST'])
def vscode_direct_auth():
    """Handle direct VSCode authentication with credentials"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON data required"}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        auth_method = data.get('auth_method', 'ldap')
        
        if not username:
            return jsonify({"error": "Username is required"}), 400
        
        # Check if this is a username-only auth request (from VSCode extension with dev headers)
        is_username_only_auth = (auth_method == 'username_only' or 
                                request.headers.get('X-Development-Mode') == 'true')
        
        if is_username_only_auth:
            # Username-only authentication for VSCode extension
            # Since VSCode already validated credentials via SSH to Tufts,
            # we trust any user who can reach this point
            
            # Validate username format (Tufts username format)
            if len(username) >= 3 and re.match(r'^[a-zA-Z][a-zA-Z0-9]{2,15}$', username):
                # Create a token for the user
                token = auth_service.create_vscode_auth_token(username.lower())
                if token:
                    print(f"✅ VSCode username-only auth successful for user: {username}")
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
            # Original LDAP authentication for web app (requires password)
            if not password:
                return jsonify({"error": "Password is required for LDAP authentication"}), 400
                
            token = auth_service.authenticate_vscode_user(username, password)
            
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
        print(f"❌ Error in direct VSCode auth: {e}")
        return jsonify({"error": "Authentication error"}), 500

"""
name:        vscode_auth_status
description: endpoint to check VSCode authentication status
parameters:  session_id as query parameter
returns:     authentication status
"""
@app.route('/vscode-auth-status', methods=['GET'])
def vscode_auth_status():
    """Check VSCode authentication status"""
    try:
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({"error": "Missing session_id"}), 400
        
        status = auth_service.get_vscode_session_status(session_id)
        return jsonify(status)
        
    except Exception as e:
        print(f"❌ Error checking auth status: {e}")
        return jsonify({"error": "Status check failed"}), 500

"""
name:        analytics_endpoint
description: endpoint to get system analytics (admin only)
parameters:  none
returns:     system analytics data
"""
@app.route('/analytics', methods=['GET'])
def analytics_endpoint():
    """Get system analytics (admin endpoint)"""
    try:
        # Authenticate request
        utln, platform = auth_service.authenticate_request(request)
        if not utln:
            return jsonify({"error": "Authentication required"}), 401
        
        # For now, allow any authenticated user to view analytics
        # In production, you might want to restrict this to admins
        analytics = logging_service.get_system_analytics()
        engagement = logging_service.analyze_user_engagement()
        
        return jsonify({
            "system_analytics": analytics,
            "engagement_analytics": engagement
        })
        
    except Exception as e:
        print(f"❌ Error getting analytics: {e}")
        return jsonify({"error": "Analytics error"}), 500

"""
name:        health_status_endpoint
description: endpoint to get user's health points status
parameters:  none (uses authentication)
returns:     health points status
"""
@app.route('/health-status', methods=['GET'])
def health_status_endpoint():
    """Get user's health points status"""
    try:
        # Authenticate request
        utln, platform = auth_service.authenticate_request(request)
        if not utln: 
            return jsonify({"error": "Authentication required"}), 401
        
        # Get user data
        user_data, _ = db_manager.get_or_create_anonymous_user(utln)
        
        # Get health status
        health_status = db_manager.get_user_health_status(user_data['id'])
        
        return jsonify(health_status)
        
    except Exception as e:
        print(f"❌ Error getting health status: {e}")
        return jsonify({"error": "Health status error"}), 500

"""
name:        chat_handler
description: endpoint to handle the chat request and return a message-response
parameters:  a json object with a message key and a conversationId key
returns:     a json object with a response key and a rag_context key
"""
@app.route('/api', methods=['POST'])
def chat_handler():
    request_start_time = time.time()
    
    try:
        # Authenticate request first
        utln, platform = auth_service.authenticate_request(request)
        if not utln:
            return jsonify({"error": "Authentication required. Please log in with your Tufts credentials."}), 401
        
        # Authorization handled by .htaccess - if we get here, user is authenticated
        
        data = request.get_json()
        message = data.get('message', '')
        conversation_id = data.get('conversationId', 'default')
        
        print(f"📝 Processing message from {utln} ({platform}): {message}")
        print(f"💬 Conversation ID: {conversation_id}")
        
        if not message.strip():
            return jsonify({"error": "Message is required"}), 400
        
        # Get user data for health points
        user_data, _ = db_manager.get_or_create_anonymous_user(utln)
        
        # Check and consume health point
        can_query, remaining_points = db_manager.consume_health_point(user_data['id'])
        if not can_query:
            health_status = db_manager.get_user_health_status(user_data['id'])
            return jsonify({
                "error": "You have run out of queries. Please wait for your health points to regenerate.",
                "health_status": health_status
            }), 429  # Too Many Requests
        
        print(f"💚 Health points consumed. Remaining: {remaining_points}")
        
        # Log the user query
        query_log_result = logging_service.log_user_query(
            utln=utln,
            conversation_id=conversation_id,
            query=message,
            platform=platform
        )
        
        # Initialize conversation if it doesn't exist
        base_system_prompt = load_system_prompt()
        if conversation_id not in conversations:
            conversations[conversation_id] = [
                {"role": "system", "content": base_system_prompt}
            ]
            conversation_rag_context[conversation_id] = []
            print(f"🆕 Initialized new conversation: {conversation_id}")
        
        # In development mode, always update the base system prompt
        development_mode = os.getenv('DEVELOPMENT_MODE', '').lower() == 'true'
        if development_mode:
            update_conversation_system_prompt(conversation_id, base_system_prompt)
        
        # Use EnhancedChatHandler to process the request
        conversation_history = conversations[conversation_id]
        
        # Get accumulated formatted RAG context for this conversation
        accumulated_context = formatted_rag_accumulator.get(conversation_id, "")
        
        enhanced_result = enhanced_handler.process_chat_request(
            message=message,
            conversation_id=conversation_id,
            conversation_history=conversation_history,
            conversation_rag_context=[],  # Enhanced handler doesn't use this anymore
            utln=utln,
            platform=platform
        )
        
        assistant_response = enhanced_result.get("response", "")
        accumulated_rag_context = enhanced_result.get("rag_context", "")
        response_time_ms = enhanced_result.get("response_time_ms")

        # Accumulate formatted RAG context into system prompt for this conversation
        if accumulated_rag_context:
            previous = formatted_rag_accumulator.get(conversation_id, "")
            combined = previous + ("\n\n" if previous else "") + accumulated_rag_context
            formatted_rag_accumulator[conversation_id] = combined
            enhanced_system_prompt = f"{base_system_prompt}\n\n{combined}"
            conversations[conversation_id][0]["content"] = enhanced_system_prompt
        
        # Maintain in-memory conversation history
        conversation_history.append({"role": "user", "content": message})
        conversation_history.append({"role": "assistant", "content": assistant_response})
        
        # Log the assistant response
        logging_service.log_assistant_response(
            conversation_id=conversation_id,
            response=assistant_response,
            rag_context=accumulated_rag_context,
            model_used='4o-mini',
            temperature=0.5,
            response_time_ms=response_time_ms
        )
        
        print(f"📄 Generated response length: {len(assistant_response)}")
        if response_time_ms is not None:
            print(f"⏱️ Total request time: {response_time_ms}ms")
        print(f"👤 User analytics: {query_log_result}")
        
        # Get updated health status
        health_status = db_manager.get_user_health_status(user_data['id'])
        
        # return the response 
        return jsonify({
            "response": assistant_response,
            "rag_context": accumulated_rag_context,
            "conversation_id": conversation_id,
            "category": enhanced_result.get("category"),
            "user_info": {
                "anonymous_id": query_log_result.get('anonymous_id'),
                "platform": platform,
                "is_new_conversation": query_log_result.get('is_new_conversation', False)
            },
            "health_status": health_status
        })
        
    except Exception as error:
        print(f"❌ Error processing request: {error}")
        return jsonify({"error": "Sorry, an error occurred while processing your request."}), 500

"""
name:        chat_handler_stream
description: endpoint to handle chat requests with streaming status updates
parameters:  a json object with a message key and a conversationId key
returns:     Server-Sent Events stream with status updates and final response
"""
@app.route('/api/stream', methods=['POST'])
def chat_handler_stream():
    request_start_time = time.time()
    
    # Authenticate request first
    utln, platform = auth_service.authenticate_request(request)
    if not utln:
        def error_stream():
            yield f'data: {json.dumps({"status": "error", "error": "Authentication required. Please log in with your Tufts credentials."})}\n\n'
        return Response(stream_with_context(error_stream()), mimetype='text/event-stream')
    
    # Authorization handled by .htaccess - if we get here, user is authenticated
    
    data = request.get_json()
    message = data.get('message', '')
    conversation_id = data.get('conversationId', 'default')
    
    def generate_events():
        try:
            print(f"📝 Processing message from {utln} ({platform}): {message}")
            print(f"💬 Conversation ID: {conversation_id}")
            
            if not message.strip():
                yield f'data: {json.dumps({"error": "Message is required"})}\n\n'
                return
            
            # Get user data for health points
            user_data, _ = db_manager.get_or_create_anonymous_user(utln)
            
            # Check and consume health point
            can_query, remaining_points = db_manager.consume_health_point(user_data['id'])
            if not can_query:
                health_status = db_manager.get_user_health_status(user_data['id'])
                yield f'data: {json.dumps({"error": "You have run out of queries. Please wait for your health points to regenerate.", "health_status": health_status})}\n\n'
                return
            
            print(f"💚 Health points consumed. Remaining: {remaining_points}")
            
            # Log the user query
            query_log_result = logging_service.log_user_query(
                utln=utln,
                conversation_id=conversation_id,
                query=message,
                platform=platform
            )
            
            # Initialize conversation if it doesn't exist
            base_system_prompt = load_system_prompt()
            if conversation_id not in conversations:
                conversations[conversation_id] = [
                    {"role": "system", "content": base_system_prompt}
                ]
                conversation_rag_context[conversation_id] = []
                print(f"🆕 Initialized new conversation: {conversation_id}")
            
            # In development mode, always update the base system prompt
            development_mode = os.getenv('DEVELOPMENT_MODE', '').lower() == 'true'
            if development_mode:
                update_conversation_system_prompt(conversation_id, base_system_prompt)
            
            # Send status: loading
            yield f'data: {json.dumps({"status": "loading", "message": "Looking at course content..."})}\n\n'
            
            # Send status: thinking
            yield f'data: {json.dumps({"status": "thinking", "message": "Thinking..."})}\n\n'
            
            # Use EnhancedChatHandler
            conversation_history = conversations[conversation_id]
            
            # Get accumulated formatted RAG context for this conversation
            accumulated_context = formatted_rag_accumulator.get(conversation_id, "")
            
            enhanced_result = enhanced_handler.process_chat_request(
                message=message,
                conversation_id=conversation_id,
                conversation_history=conversation_history,
                conversation_rag_context=[],  # Enhanced handler doesn't use this anymore
                utln=utln,
                platform=platform
            )
            assistant_response = enhanced_result.get("response", "")
            accumulated_rag_context = enhanced_result.get("rag_context", "")
            response_time_ms = enhanced_result.get("response_time_ms")

            # Accumulate formatted RAG context into system prompt for this conversation
            if accumulated_rag_context:
                previous = formatted_rag_accumulator.get(conversation_id, "")
                combined = previous + ("\n\n" if previous else "") + accumulated_rag_context
                formatted_rag_accumulator[conversation_id] = combined
                enhanced_system_prompt = f"{base_system_prompt}\n\n{combined}"
                conversations[conversation_id][0]["content"] = enhanced_system_prompt
            
            # Maintain in-memory conversation history
            conversation_history.append({"role": "user", "content": message})
            conversation_history.append({"role": "assistant", "content": assistant_response})
            
            # Log the assistant response
            logging_service.log_assistant_response(
                conversation_id=conversation_id,
                response=assistant_response,
                rag_context=accumulated_rag_context,
                model_used='4o-mini',
                temperature=0.5,
                response_time_ms=response_time_ms
            )
            
            print(f"📄 Generated response length: {len(assistant_response)}")
            if response_time_ms is not None:
                print(f"⏱️ Total request time: {response_time_ms}ms")
            print(f"👤 User analytics: {query_log_result}")
            
            # Get updated health status
            health_status = db_manager.get_user_health_status(user_data['id'])
            
            # Send final response
            response_data = {
                "status": "complete", 
                "response": assistant_response, 
                "rag_context": accumulated_rag_context, 
                "conversation_id": conversation_id,
                "category": enhanced_result.get("category"),
                "user_info": {
                    "anonymous_id": query_log_result.get('anonymous_id'),
                    "platform": platform,
                    "is_new_conversation": query_log_result.get('is_new_conversation', False)
                },
                "health_status": health_status
            }
            yield f'data: {json.dumps(response_data)}\n\n'
            
        except Exception as error:
            print(f"❌ Error processing request: {error}")
            yield f'data: {json.dumps({"status": "error", "error": "Sorry, an error occurred while processing your request."})}\n\n'
    
    return Response(
        stream_with_context(generate_events()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )

""" 
name:        rag_context_string_simple
description: create a context string from retrieve's return value
parameters:  rag_context - the return value from retrieve()
returns:     str - formatted context string
"""
def rag_context_string_simple(rag_context):
    context_string = ""
    
    i = 1
    for collection in rag_context:
        if not context_string:
            context_string = """The following is additional context that may be
                             helpful in answering the query. Use them only
                             if it is relevant to the user's query."""
        
        context_string += """
        #{} {}
        """.format(i, collection['doc_summary'])
        j = 1
        for chunk in collection['chunks']:
            context_string += """
            #{}.{} {}
            """.format(i, j, chunk)
            j += 1
        i += 1 
    return context_string

"""
name:        update_conversation_system_prompt
description: update the system prompt in conversation history with accumulated RAG context
parameters:  conversation_id - the conversation ID
             base_system_prompt - the original system prompt
returns:     none
"""
def update_conversation_system_prompt(conversation_id, base_system_prompt):
    if conversation_id not in conversation_rag_context or not conversation_rag_context[conversation_id]:
        # No RAG context accumulated yet, keep original system prompt
        conversations[conversation_id][0]["content"] = base_system_prompt
        return
    
    # Format all accumulated RAG context
    accumulated_context = rag_context_string_simple(conversation_rag_context[conversation_id])
    
    # Update the system prompt with accumulated context
    enhanced_system_prompt = f"{base_system_prompt}\n\n{accumulated_context}"
    conversations[conversation_id][0]["content"] = enhanced_system_prompt

if __name__ == '__main__':
    print("🚀 Starting Python Flask API server with authentication and logging...")
    print("📍 Available endpoints:")
    print("   POST /api - Main chat endpoint (requires authentication)")
    print("   POST /api/stream - Streaming chat endpoint (requires authentication)")
    print("   GET /health - Health check")
    print("   GET/POST /vscode-auth - VSCode extension authentication (browser-based)")
    print("   POST /vscode-direct-auth - VSCode extension authentication (form-based)")
    print("   GET /vscode-auth-status - Check VSCode auth status")
    print("   GET /analytics - System analytics (authenticated users)")
    print("   GET /health-status - Get user's health points status")
    print("🔐 Authentication: Web app uses .htaccess, VSCode uses JWT tokens with LDAP")
    print("📊 Logging: All interactions are logged with user anonymization")
    
    # Run the Flask app (127.0.0.1 for local development)
    app.run(host='0.0.0.0', port=5000, debug=False) 