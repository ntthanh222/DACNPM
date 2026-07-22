import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def check_health():
    res = requests.get(f"{BASE_URL}/health")
    print(f"Health Check: {res.status_code}")
    assert res.status_code == 200, "Health check failed"

def check_chat():
    login_payload = {
        "username": "admin",
        "password": "DevAdmin-[REDACTED]"
    }
    res_login = requests.post(f"{BASE_URL}/api/auth/login", json=login_payload)
    assert res_login.status_code == 200, f"Login failed: {res_login.text}"
    token = res_login.json().get("access_token")

    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Get stream ticket
    ticket_payload = {
        "message": "Hello, how are you?",
        "session_id": "test_session_123"
    }
    res_ticket = requests.post(
        f"{BASE_URL}/api/chatbot/chat/stream-ticket",
        json=ticket_payload,
        headers=headers
    )
    assert res_ticket.status_code == 200, f"Stream ticket failed: {res_ticket.text}"
    ticket = res_ticket.json().get("stream_ticket")
    
    # 2. Get SSE Stream
    res = requests.get(
        f"{BASE_URL}/api/chatbot/chat/stream?stream_ticket={ticket}&message=Hello",
        stream=True
    )
    print(f"Chat Stream GET status: {res.status_code}")
    assert res.status_code == 200, "Chat Stream GET failed"
    
    # Read SSE
    chunks = 0
    for line in res.iter_lines():
        if line:
            decoded = line.decode('utf-8')
            if decoded.startswith("data: "):
                chunks += 1
    
    print(f"Received {chunks} SSE chunks.")
    assert chunks > 0, "No SSE chunks received"

if __name__ == "__main__":
    try:
        check_health()
        check_chat()
        print("API Black-Box Validation Passed!")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
