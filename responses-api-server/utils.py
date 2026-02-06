from llmproxy import retrieve

def _retrieve_rag_context(message: str, threshold: float, k: int) -> list:
    """Retrieve RAG context for the query"""
    try:
        print(f"🔍 Attempting RAG retrieval for query: '{message}'")
        rag_context = retrieve(
            query=message,
            session_id='GenericSession',
            rag_threshold=threshold,
            rag_k=k 
        )
        
        if rag_context and isinstance(rag_context, list) and len(rag_context) > 0:
            print(f"📄 Retrieved RAG context: {len(rag_context)} collections")
            return rag_context
        else:
            print(f"📭 No RAG context found")
            return []
            
    except Exception as e:
        print(f"⚠️ Error retrieving RAG context: {e}")
        return []

def _format_rag_context(rag_context: list) -> str:
    """Format RAG context for use in prompts"""
    if not rag_context:
        return ""
    
    context_string = "The following is additional context that may be helpful in answering the user's query.\n\n"
    
    for i, collection in enumerate(rag_context, 1):
        context_string += f"#{i} {collection.get('doc_summary', '')}\n"
        for j, chunk in enumerate(collection.get('chunks', []), 1):
            context_string += f"#{i}.{j} {chunk}\n"
    
    return context_string