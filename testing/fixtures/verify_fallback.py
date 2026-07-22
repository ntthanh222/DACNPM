import requests
import subprocess
import time
import sys

BASE_URL = "http://localhost:8000"

def get_token():
    login_payload = {
        "username": "admin",
        "password": "DevAdmin-[REDACTED]"
    }
    res = requests.post(f"{BASE_URL}/api/auth/login", json=login_payload)
    if res.status_code == 200:
        return res.json().get("access_token")
    return None

def check_chat_fallback(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Get stream ticket
    ticket_payload = {
        "message": "Hello, how are you?",
        "session_id": "test_session_fallback"
    }
    res_ticket = requests.post(
        f"{BASE_URL}/api/chatbot/chat/stream-ticket",
        json=ticket_payload,
        headers=headers
    )
    if res_ticket.status_code != 200:
        print(f"Failed to get ticket: {res_ticket.text}")
        return False
    ticket = res_ticket.json().get("stream_ticket")
    
    # 2. Get SSE Stream
    res = requests.get(
        f"{BASE_URL}/api/chatbot/chat/stream?stream_ticket={ticket}&message=Hello",
        stream=True
    )
    if res.status_code != 200:
        print(f"Chat Stream failed: {res.status_code}")
        return False
        
    chunks = 0
    content = ""
    for line in res.iter_lines():
        if line:
            decoded = line.decode('utf-8')
            if decoded.startswith("data: "):
                chunks += 1
                try:
                    import json
                    data = json.loads(decoded[6:])
                    if 'token' in data:
                        content += data['token']
                except:
                    pass
    print(f"Received {chunks} SSE chunks in fallback.")
    print(f"Response: {content}")
    # Even if it's fallback, it should return chunks and not fail.
    return chunks > 0

if __name__ == "__main__":
    print("Testing Fallback Mechanism by stopping Rasa...")
    subprocess.run(["docker", "compose", "stop", "rasa", "rasa-actions"], check=True)
    time.sleep(2) # Give it a moment
    
    try:
        token = get_token()
        if not token:
            print("Login failed")
            sys.exit(1)
            
        success = check_chat_fallback(token)
        if success:
            print("Fallback Test PASSED")
        else:
            print("Fallback Test FAILED")
            sys.exit(1)
    finally:
        print("Restarting Rasa...")
        subprocess.run(["docker", "compose", "start", "rasa", "rasa-actions"], check=True)
