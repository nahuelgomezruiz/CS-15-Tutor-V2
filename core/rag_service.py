"""RAG (Retrieval-Augmented Generation) Service."""

from typing import List, Dict, Any, Optional
from adapters.llm.natlab import NatLabAdapter


class RAGService:
    """
    Service for retrieving and formatting RAG context.
    
    RAG retrieval is specific to the NatLab adapter which provides
    this capability. Other LLM providers don't have built-in RAG.
    """
    
    def __init__(self, natlab_adapter: Optional[NatLabAdapter] = None):
        """
        Initialize the RAG service.
        
        Args:
            natlab_adapter: NatLab adapter for RAG retrieval.
                           If not provided, creates one automatically.
        """
        if natlab_adapter is None:
            try:
                self._adapter = NatLabAdapter()
            except ValueError:
                print("Warning: NatLab adapter not configured. RAG will be disabled.")
                self._adapter = None
        else:
            self._adapter = natlab_adapter
    
    def retrieve(
        self,
        query: str,
        threshold: float = 0.4,
        k: int = 5,
        session_id: str = 'GenericSession'
    ) -> List[Dict[str, Any]]:
        """
        Retrieve RAG context for a query.
        
        Args:
            query: Search query
            threshold: Relevance threshold (0.0 to 1.0)
            k: Number of results to retrieve
            session_id: Session identifier for tracking
        
        Returns:
            List of retrieved context documents with structure:
            [{'doc_summary': str, 'chunks': List[str]}, ...]
        """
        if not self._adapter:
            return []
        
        try:
            print(f"[RAG] Retrieving context for: '{query[:50]}...'")
            
            rag_context = self._adapter.retrieve(
                query=query,
                session_id=session_id,
                rag_threshold=threshold,
                rag_k=k
            )
            
            if rag_context and isinstance(rag_context, list) and len(rag_context) > 0:
                print(f"[RAG] Retrieved {len(rag_context)} collections")
                return rag_context
            else:
                print("[RAG] No context found")
                return []
                
        except Exception as e:
            print(f"[RAG] Error retrieving context: {e}")
            return []
    
    def format_context(self, rag_context: List[Dict[str, Any]]) -> str:
        """
        Format RAG context for use in prompts.
        
        Args:
            rag_context: List of context documents from retrieve()
        
        Returns:
            Formatted context string for injection into prompts
        """
        if not rag_context:
            return ""
        
        context_string = "The following is additional context that may be helpful in answering the user's query.\n\n"
        
        for i, collection in enumerate(rag_context, 1):
            doc_summary = collection.get('doc_summary', '')
            context_string += f"#{i} {doc_summary}\n"
            
            for j, chunk in enumerate(collection.get('chunks', []), 1):
                context_string += f"#{i}.{j} {chunk}\n"
        
        return context_string
    
    def retrieve_and_format(
        self,
        query: str,
        threshold: float = 0.4,
        k: int = 5,
        session_id: str = 'GenericSession'
    ) -> tuple:
        """
        Convenience method to retrieve and format context in one call.
        
        Args:
            query: Search query
            threshold: Relevance threshold
            k: Number of results
            session_id: Session identifier
        
        Returns:
            Tuple of (raw_context, formatted_context_string)
        """
        raw_context = self.retrieve(query, threshold, k, session_id)
        formatted_context = self.format_context(raw_context)
        return raw_context, formatted_context
    
    def is_available(self) -> bool:
        """Check if RAG service is available."""
        return self._adapter is not None and self._adapter.is_available()
