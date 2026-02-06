"""Chat API routes."""

import json
import time
from typing import Dict, List
from flask import Blueprint, request, jsonify, Response, stream_with_context, current_app

chat_bp = Blueprint('chat', __name__)

# In-memory conversation storage
conversations: Dict[str, List[Dict[str, str]]] = {}
formatted_rag_accumulator: Dict[str, str] = {}


def get_orchestrator():
    """Get the orchestrator from app context."""
    return current_app.config['orchestrator']


def get_db():
    """Get the database adapter from app context."""
    return current_app.config['db_adapter']


def get_auth():
    """Get the auth service from app context."""
    return current_app.config['auth_service']


@chat_bp.route('/api', methods=['POST'])
def chat_handler():
    """Main chat endpoint (non-streaming)."""
    request_start_time = time.time()
    
    try:
        auth = get_auth()
        orchestrator = get_orchestrator()
        db = get_db()
        
        # Authenticate request
        utln, platform = auth.authenticate_request(request)
        if not utln:
            return jsonify({"error": "Authentication required. Please log in with your Tufts credentials."}), 401
        
        data = request.get_json()
        message = data.get('message', '')
        conversation_id = data.get('conversationId', 'default')
        
        print(f"[Chat] Processing message from {utln} ({platform}): {message[:50]}...")
        
        if not message.strip():
            return jsonify({"error": "Message is required"}), 400
        
        # Get user data for health points
        user_data, _ = db.get_or_create_anonymous_user(utln)
        
        # Check and consume health point
        can_query, remaining_points = db.consume_health_point(user_data['id'])
        if not can_query:
            health_status = db.get_user_health_status(user_data['id'])
            return jsonify({
                "error": "You have run out of queries. Please wait for your health points to regenerate.",
                "health_status": health_status
            }), 429
        
        print(f"[Chat] Health points consumed. Remaining: {remaining_points}")
        
        # Initialize conversation if needed
        base_system_prompt = orchestrator.system_prompt
        if conversation_id not in conversations:
            conversations[conversation_id] = [
                {"role": "system", "content": base_system_prompt}
            ]
            formatted_rag_accumulator[conversation_id] = ""
            print(f"[Chat] Initialized new conversation: {conversation_id}")
        
        # Get accumulated RAG context
        accumulated_context = formatted_rag_accumulator.get(conversation_id, "")
        
        # Process the query
        result = orchestrator.process_query(
            message=message,
            conversation_id=conversation_id,
            conversation_history=conversations[conversation_id],
            utln=utln,
            platform=platform,
            accumulated_rag_context=accumulated_context
        )
        
        assistant_response = result.get("response", "")
        new_rag_context = result.get("rag_context", "")
        response_time_ms = result.get("response_time_ms")
        
        # Accumulate RAG context
        if new_rag_context:
            previous = formatted_rag_accumulator.get(conversation_id, "")
            combined = previous + ("\n\n" if previous else "") + new_rag_context
            formatted_rag_accumulator[conversation_id] = combined
            enhanced_system_prompt = f"{base_system_prompt}\n\n{combined}"
            conversations[conversation_id][0]["content"] = enhanced_system_prompt
        
        # Update conversation history
        conversations[conversation_id].append({"role": "user", "content": message})
        conversations[conversation_id].append({"role": "assistant", "content": assistant_response})
        
        # Log interaction
        log_result = orchestrator.log_interaction(
            utln=utln,
            conversation_id=conversation_id,
            query=message,
            response=assistant_response,
            platform=platform,
            rag_context=new_rag_context,
            response_time_ms=response_time_ms
        )
        
        # Get updated health status
        health_status = db.get_user_health_status(user_data['id'])
        
        return jsonify({
            "response": assistant_response,
            "rag_context": new_rag_context,
            "conversation_id": conversation_id,
            "user_info": {
                "anonymous_id": log_result.get('anonymous_id'),
                "platform": platform,
                "is_new_conversation": log_result.get('is_new_conversation', False)
            },
            "health_status": health_status
        })
        
    except Exception as error:
        print(f"[Chat] Error: {error}")
        return jsonify({"error": "Sorry, an error occurred while processing your request."}), 500


@chat_bp.route('/api/stream', methods=['POST'])
def chat_handler_stream():
    """Streaming chat endpoint with status updates."""
    auth = get_auth()
    
    # Authenticate request
    utln, platform = auth.authenticate_request(request)
    if not utln:
        def error_stream():
            yield f'data: {json.dumps({"status": "error", "error": "Authentication required. Please log in with your Tufts credentials."})}\n\n'
        return Response(stream_with_context(error_stream()), mimetype='text/event-stream')
    
    data = request.get_json()
    message = data.get('message', '')
    conversation_id = data.get('conversationId', 'default')
    
    def generate_events():
        try:
            orchestrator = get_orchestrator()
            db = get_db()
            
            print(f"[Chat] Streaming message from {utln} ({platform}): {message[:50]}...")
            
            if not message.strip():
                yield f'data: {json.dumps({"error": "Message is required"})}\n\n'
                return
            
            # Get user data for health points
            user_data, _ = db.get_or_create_anonymous_user(utln)
            
            # Check and consume health point
            can_query, remaining_points = db.consume_health_point(user_data['id'])
            if not can_query:
                health_status = db.get_user_health_status(user_data['id'])
                yield f'data: {json.dumps({"error": "You have run out of queries.", "health_status": health_status})}\n\n'
                return
            
            # Initialize conversation if needed
            base_system_prompt = orchestrator.system_prompt
            if conversation_id not in conversations:
                conversations[conversation_id] = [
                    {"role": "system", "content": base_system_prompt}
                ]
                formatted_rag_accumulator[conversation_id] = ""
            
            # Send status updates
            yield f'data: {json.dumps({"status": "loading", "message": "Looking at course content..."})}\n\n'
            yield f'data: {json.dumps({"status": "thinking", "message": "Thinking..."})}\n\n'
            
            # Get accumulated RAG context
            accumulated_context = formatted_rag_accumulator.get(conversation_id, "")
            
            # Process the query
            result = orchestrator.process_query(
                message=message,
                conversation_id=conversation_id,
                conversation_history=conversations[conversation_id],
                utln=utln,
                platform=platform,
                accumulated_rag_context=accumulated_context
            )
            
            assistant_response = result.get("response", "")
            new_rag_context = result.get("rag_context", "")
            response_time_ms = result.get("response_time_ms")
            
            # Accumulate RAG context
            if new_rag_context:
                previous = formatted_rag_accumulator.get(conversation_id, "")
                combined = previous + ("\n\n" if previous else "") + new_rag_context
                formatted_rag_accumulator[conversation_id] = combined
                enhanced_system_prompt = f"{base_system_prompt}\n\n{combined}"
                conversations[conversation_id][0]["content"] = enhanced_system_prompt
            
            # Update conversation history
            conversations[conversation_id].append({"role": "user", "content": message})
            conversations[conversation_id].append({"role": "assistant", "content": assistant_response})
            
            # Log interaction
            log_result = orchestrator.log_interaction(
                utln=utln,
                conversation_id=conversation_id,
                query=message,
                response=assistant_response,
                platform=platform,
                rag_context=new_rag_context,
                response_time_ms=response_time_ms
            )
            
            # Get updated health status
            health_status = db.get_user_health_status(user_data['id'])
            
            # Send final response
            response_data = {
                "status": "complete",
                "response": assistant_response,
                "rag_context": new_rag_context,
                "conversation_id": conversation_id,
                "user_info": {
                    "anonymous_id": log_result.get('anonymous_id'),
                    "platform": platform,
                    "is_new_conversation": log_result.get('is_new_conversation', False)
                },
                "health_status": health_status
            }
            yield f'data: {json.dumps(response_data)}\n\n'
            
        except Exception as error:
            print(f"[Chat] Stream error: {error}")
            yield f'data: {json.dumps({"status": "error", "error": "Sorry, an error occurred."})}\n\n'
    
    return Response(
        stream_with_context(generate_events()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )
