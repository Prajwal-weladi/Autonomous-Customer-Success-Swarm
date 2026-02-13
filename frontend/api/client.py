import requests
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/v1")

def send_message(conversation_id: str, message: str) -> dict:
    """
    Send message to basic endpoint (deprecated - use send_pipeline_message instead)
    """
    payload = {
        "conversation_id": conversation_id,
        "message": message
    }

    response = requests.post(f"{BACKEND_URL}/message", json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def send_pipeline_message(conversation_id: str, message: str) -> dict:
    """
    Send message through complete pipeline: Triage -> Database -> Policy -> Resolution
    
    Returns:
        dict with full pipeline response including individual agent outputs
    """
    payload = {
        "conversation_id": conversation_id,
        "message": message
    }

    response = requests.post(f"{BACKEND_URL}/pipeline", json=payload, timeout=120)
    response.raise_for_status()
    return response.json()
