"""Quality Checker for response validation."""

import json
import re
from typing import Tuple, Optional

from adapters.llm.base import BaseLLMAdapter


class QualityChecker:
    """
    Service for checking response quality.
    
    Validates that responses don't contain:
    - Complete code solutions
    - Pseudocode solutions
    - Invented/inaccurate information
    """
    
    def __init__(self, llm_adapter: BaseLLMAdapter):
        """
        Initialize the quality checker.
        
        Args:
            llm_adapter: LLM adapter to use for quality checking
        """
        self._adapter = llm_adapter
    
    def check_quality(
        self,
        query: str,
        response: str,
        rag_context: str = ""
    ) -> Tuple[int, str]:
        """
        Check response quality for code solutions and invented information.
        
        Args:
            query: Original student query
            response: Assistant's response to check
            rag_context: RAG context that was used
        
        Returns:
            Tuple of (score 1-10, feedback string)
        """
        quality_check_prompt = f"""
You are a quality checker for a CS 15 tutor assistant. Rate the following response on a scale of 1-10.

Student Query: "{query}"
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
            messages = [
                {"role": "system", "content": "You are a quality checker. Return only valid JSON with 'score' and 'feedback' fields."},
                {"role": "user", "content": quality_check_prompt}
            ]
            
            quality_result = self._adapter.generate(
                messages=messages,
                temperature=0.1,
            )
            
            # Try to parse JSON response
            try:
                quality_data = json.loads(quality_result)
                score = quality_data.get('score', 5)
                feedback = quality_data.get('feedback', 'Unable to parse quality feedback')
            except json.JSONDecodeError:
                # Fallback: try to extract score from text
                score_match = re.search(r'score["\s]*:["\s]*(\d+)', quality_result)
                score = int(score_match.group(1)) if score_match else 5
                feedback = quality_result if quality_result else 'Quality check failed to parse'
            
            return score, feedback
            
        except Exception as e:
            print(f"[QualityChecker] Error: {e}")
            return 5, f"Quality check error: {str(e)}"
    
    def generate_enhancement_prompt(self, original_response: str, feedback: str) -> str:
        """
        Generate a prompt to improve a response based on quality feedback.
        
        Args:
            original_response: The original response that failed quality check
            feedback: Quality check feedback
        
        Returns:
            Enhancement prompt string
        """
        return f"""
The following assistant response to a CS 15 student query failed quality checks:

Original Response: "{original_response}"
Quality Feedback: "{feedback}"

Please rewrite the assistant's response so that it avoids the listed issues. Focus on:
1. Not providing complete code solutions
2. Not inventing course/project information

Return only the improved response, nothing else.
"""
