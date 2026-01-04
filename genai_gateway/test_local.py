"""Local testing script for GenAI Gateway"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8080"

def test_health():
    """Test health endpoint"""
    print("Testing GET /health...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_generate(prompt: str = "Reply with: OK"):
    """Test generate endpoint"""
    print(f"\nTesting POST /generate...")
    print(f"Prompt: {prompt[:100]}")
    
    try:
        start = time.time()
        response = requests.post(
            f"{BASE_URL}/generate",
            json={"prompt": prompt},
            timeout=60
        )
        latency = time.time() - start
        
        print(f"Status: {response.status_code}")
        print(f"Latency: {latency:.2f}s")
        
        response_data = response.json()
        print(f"Response: {json.dumps(response_data, indent=2)[:500]}")
        
        if response.status_code == 200:
            print(f"\n✅ SUCCESS! Generated {len(response_data.get('text', ''))} characters")
            return True
        else:
            print(f"\n❌ FAILED: {response_data}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    print("=" * 60)
    print("GenAI Gateway Local Test")
    print("=" * 60)
    print(f"Target: {BASE_URL}\n")
    
    # Test health
    health_ok = test_health()
    
    if not health_ok:
        print("\n❌ Health check failed. Is the server running?")
        print("Run: python main.py")
        return
    
    # Test simple generation
    test_generate("Reply with: OK")
    
    # Test story-like generation
    test_generate("""You are a storyteller. Write a 2-sentence scary story about a mirror.

OUTPUT REQUIREMENTS:
- Exactly 2 sentences
- English only
- No markdown""")

if __name__ == "__main__":
    main()




