import requests
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/v1/message")

def send_message(conversation_id: str, message: str) -> dict:
    payload = {
        "conversation_id": conversation_id,
        "message": message
    }

    response = requests.post(BACKEND_URL, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()
