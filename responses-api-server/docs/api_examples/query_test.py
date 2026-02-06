import os
from llmproxy import generate

# Global variable to store the system prompt from system_prompt.txt
SYSTEM_PROMPT = ""
with open(os.path.join(os.path.dirname(__file__), "system_prompt.txt"), "r") as f:
    SYSTEM_PROMPT = f.read().strip()

if __name__ == '__main__':
    response = generate(model = '4o-mini',
        system = SYSTEM_PROMPT,
        query = 'How do I implement PassengerQueue?',
        temperature=0.7,
        lastk=0,
        session_id='GenericSession',
        rag_usage = True,
        rag_threshold = 0.5,
        rag_k = 3)

    print(f"Response: {response['response']}\n\nRAG Context: {response['rag_context']}")
