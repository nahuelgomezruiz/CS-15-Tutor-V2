import requests
import json
import uuid

# Configuration
API_URL = "http://127.0.0.1:5000/api"
STREAM_URL = "http://127.0.0.1:5000/api/stream"

def test_regular_api():
    """Test the regular (non-streaming) API endpoint"""
    print("🧪 Testing regular API endpoint...")
    
    conversation_id = str(uuid.uuid4())
    
    # Test message
    test_message = "How do I implement PassengerQueue?"
    
    payload = {
        "message": test_message,
        "conversationId": conversation_id
    }
    
    try:
        response = requests.post(API_URL, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success!")
            print(f"📝 Response: {data['response'][:200]}...")
            print(f"🔍 RAG Context: {str(data.get('rag_context', 'None'))[:100]}...")
            print(f"💬 Conversation ID: {data['conversation_id']}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"📄 Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

def test_streaming_api():
    """Test the streaming API endpoint"""
    print("\n🧪 Testing streaming API endpoint...")
    
    conversation_id = str(uuid.uuid4())
    
    # Test message
    test_message = "What is a linked list?"
    
    payload = {
        "message": test_message,
        "conversationId": conversation_id
    }
    
    try:
        response = requests.post(STREAM_URL, json=payload, stream=True)
        
        if response.status_code == 200:
            print("✅ Streaming response:")
            print("📝 ", end="", flush=True)
            
            for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                if chunk:
                    print(chunk, end="", flush=True)
            
            print("\n✅ Streaming complete!")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"📄 Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

def test_health_check():
    """Test the health check endpoint"""
    print("\n🧪 Testing health check...")
    
    try:
        response = requests.get("http://127.0.0.1:5000/health")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Health check request failed: {e}")

if __name__ == "__main__":
    print("🚀 Testing Python Flask API...")
    print("📍 Make sure the Flask server is running")
    print("-" * 50)
    
    # Test health check first
    test_health_check()
    
    # Test regular API
    test_regular_api()
    
    # Test streaming API
    test_streaming_api()
    
    print("\n" + "-" * 50)
    print("✅ Testing complete!") 