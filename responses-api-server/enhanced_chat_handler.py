"""Enhanced chat handler with RAG retrieval and quality checking."""

import time
import os
from typing import Dict, Any, Optional, Tuple
from llmproxy import generate, retrieve
from utils import _retrieve_rag_context, _format_rag_context


class EnhancedChatHandler:
    """Chat handler with quality checking for code solutions and invented info."""
    
    def __init__(self):
        self.base_system_prompt = self._load_system_prompt()
        self.max_regeneration_attempts = 3
    
    def process_chat_request(self, message: str, conversation_id: str, 
                           conversation_history: list, conversation_rag_context: list,
                           utln: str, platform: str) -> Dict[str, Any]:
        """Process chat request with RAG retrieval and quality checking."""
        request_start_time = time.time()
        
        print(f"[INFO] Processing message from {utln} ({platform}): {message[:50]}...")
        
        rag_context = _retrieve_rag_context(message, 0.4, 5)
        final_response = self._generate_quality_checked_response(
            message, rag_context, conversation_history
        )
        
        # Prepare and return response
        return self._prepare_response(
            final_response, conversation_id, request_start_time,
            utln, platform, rag_context
        )
    
    def _generate_quality_checked_response(self, message: str, 
                                         rag_context: list, conversation_history: list) -> str:
        """Generate response with quality checking for code solutions and invented info."""
        rag_context_formatted = _format_rag_context(rag_context) if rag_context else ""
        response = self._generate_response(message, rag_context_formatted, conversation_history)

        for attempt in range(self.max_regeneration_attempts):
            score, feedback = self._check_response_quality(message, response, rag_context_formatted)
            
            if score > 7:
                print(f"[INFO] Quality check passed (score: {score})")
                return response
            else:
                print(f"[WARN] Quality check failed (score: {score}): {feedback}")
                
                if attempt < self.max_regeneration_attempts - 1:
                    enhanced_message = self._enhance_response_with_feedback(response, feedback)
                    response = self._generate_response(enhanced_message, rag_context_formatted, conversation_history)
                else:
                    print(f"[WARN] Max attempts reached, using last response")
                    return response
        
        return "I apologize, but I'm having trouble generating an appropriate response. Please try rephrasing your question."
    
    def _check_response_quality(self, message: str, response: str, rag_context: str) -> Tuple[int, str]:
        """Check response quality for code solutions and invented information."""
        
        quality_check_prompt = f"""
       You are a quality checker for a CS 15 tutor assistant. Rate the following response on a scale of 1-10.

        Student Query: "{message}"
        RAG Context: "{rag_context}"
        Assistant Response: "{response}"

        Check ONLY for these issues (all are NEVER allowed):
        1. COMPLETE CODE SOLUTIONS: Does the response provide full, runnable code solutions to assignments? 
        - Any complete implementation of homework/project functions is a major violation.
        - Short code snippets used only for illustration are acceptable.
        2. PSEUDOCODE SOLUTIONS: Does the response provide pseudocode or step-by-step algorithmic outlines for assignment functions? 
        - Even if the student explicitly requests pseudocode, it must NOT be given.
        3. INVENTED OR INACCURATE INFORMATION: Does the response make up or invent information about CS 15 course details, project requirements, due dates, or implementation specifics that are not in the RAG context? 
        - Adding details not found in the official course materials counts as a major violation.

        Scoring:
        - 9-10: No issues, helpful and accurate
        - 7-8: Minor issues only, overall acceptable
        - 5-6: Noticeable issues, needs improvement
        - 1-4: Major violations (full code, pseudocode, or invented/inaccurate information). Response must be regenerated.

        Return ONLY a JSON object with "score" (integer 1-10) and "feedback" (string explaining issues found).
        """
        
        try:
            quality_result = generate(
                model='4o-mini',
                system="You are a quality checker. Return only valid JSON with 'score' and 'feedback' fields.",
                query=quality_check_prompt,
                temperature=0.1,
                lastk=0,
                rag_usage=False,
            )
            
            if isinstance(quality_result, dict) and 'response' in quality_result:
                quality_text = quality_result['response']
            else:
                quality_text = str(quality_result)
            
            # Try to parse JSON response
            import json
            try:
                quality_data = json.loads(quality_text)
                score = quality_data.get('score', 5)
                feedback = quality_data.get('feedback', 'Unable to parse quality feedback')
            except json.JSONDecodeError:
                # Fallback: try to extract score from text
                import re
                score_match = re.search(r'score["\s]*:["\s]*(\d+)', quality_text)
                score = int(score_match.group(1)) if score_match else 5
                feedback = quality_text if quality_text else 'Quality check failed to parse'
            
            return score, feedback
            
        except Exception as e:
            print(f"❌ Error in quality check: {e}")
            return 5, f"Quality check error: {str(e)}"
    
    def _load_system_prompt(self) -> str:
        """Load the base system prompt from system_prompt.txt"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            prompt_file_path = os.path.join(current_dir, 'system_prompt.txt')
            
            with open(prompt_file_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
                
        except FileNotFoundError:
            print(f"⚠️ Warning: system_prompt.txt not found, using default prompt")
            return "You are a friendly and brief Teaching Assistant (TA) for CS 15: Data Structures at Tufts University."
        except IOError as e:
            print(f"⚠️ Warning: Error reading system_prompt.txt: {e}, using default prompt")
            return "You are a friendly and brief Teaching Assistant (TA) for CS 15: Data Structures at Tufts University."
    
    def _generate_response(self, message: str, rag_context: str, conversation_history: list) -> str:
        """Generate a response using the base system prompt"""
        
        # Calculate conversation history context
        num_previous_pairs = (len(conversation_history) - 1) // 2 if conversation_history else 0
        
        query_with_rag_context = "student query: " + message + "\n\n" + rag_context

        try:
            response = generate(
                model='4o-mini',
                system=self.base_system_prompt,
                query=query_with_rag_context,
                temperature=0.5,
                lastk=num_previous_pairs,
                rag_usage=False,
            )
            
            if isinstance(response, dict) and 'response' in response:
                return response['response']
            else:
                return str(response)
                
        except Exception as e:
            print(f"❌ Error generating response: {e}")
            return "I apologize, but I encountered an error while generating a response. Please try again."
    
    def _enhance_response_with_feedback(self, original_response: str, feedback: str) -> str:
        """Enhance the original message with quality check feedback"""
        
        enhancement_prompt = f"""
        The following assistant response to a CS 15 student query failed quality checks:
    
        Original Response: "{original_response}"
        Quality Feedback: "{feedback}"
        
        Please rewrite the assistant's response so that it avoids the listed issues. Focus on:
        1. Not providing complete code solutions
        2. Not inventing course/project information
        
        Return only the improved response, nothing else.
        """
        
        return enhancement_prompt
    
    def _prepare_response(self, assistant_response: str, conversation_id: str, 
                         request_start_time: float, utln: str, platform: str, rag_context: list) -> Dict[str, Any]:
        """Prepare the final response with metadata"""
        
        response_time_ms = int((time.time() - request_start_time) * 1000)
        
        # Format RAG context for logging
        formatted_rag_context = ""
        if rag_context:
            formatted_rag_context = _format_rag_context(rag_context)
        
        print(f"📄 Generated response length: {len(assistant_response)}")
        print(f"⏱️ Total request time: {response_time_ms}ms")

        return {
            "response": assistant_response,
            "rag_context": formatted_rag_context,
            "conversation_id": conversation_id,
            "category": "general",  # Simplified - no categorization
            "response_time_ms": response_time_ms,
            "enhanced_metadata": {
                "processing_stages": ["rag_retrieval", "quality_checked_generation"],
                "quality_checks_performed": True,
                "rag_context_used": bool(formatted_rag_context)
            }
        } 