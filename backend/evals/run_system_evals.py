import sys
import os
import csv
from pathlib import Path
import requests

# Ensure the backend directory is in the PYTHONPATH
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

DATASET_PATH = Path(__file__).parent / "e2e_dataset.csv"
RESULTS_PATH = Path(__file__).parent / "e2e_results.csv"
BASE_URL = "http://127.0.0.1:8000/v1/message"

# Test data covering the different cases
E2E_CASES = [
    {
        "description": "Order Status check with missing user ID - Multi-turn",
        "turn1": "I want to check the status of my order",
        "turn2": "287899092720",
        "expected_flow": "Order status provided for 287899092720",
        "expected_contains": ["Order Update", "Cancelled"] # Adjust based on actual test output
    },
    {
        "description": "Email input to list orders",
        "turn1": "Can you list the orders under prajwalweladi1@gmail.com?",
        "turn2": None,
        "user_email": "prajwalweladi1@gmail.com",
        "expected_flow": "Lists orders for email",
        "expected_contains": ["287899092720"] 
    },
    {
        "description": "List orders via email and interact with one order",
        "turn1": "Fetch my orders for prajwalweladi1@gmail.com",
        "turn2": "I need a refund for order 287899092720",
        "user_email": "prajwalweladi1@gmail.com",
        "expected_flow": "Handles refund for dynamically listed order",
        "expected_contains": ["refund", "Yes", "confirm"]
    },
     {
        "description": "Direct return request with order ID",
        "turn1": "I want to return my order 287899092720",
        "turn2": None,
        "expected_flow": "Processes return for 287899092720",
        "expected_contains": ["return", "confirm"] 
    },
]

def post_message(conv_id: str, message: str, user_email: str = None) -> dict:
    req_body = {"conversation_id": conv_id, "message": message}
    if user_email:
        req_body["user_email"] = user_email
        
    resp = requests.post(
        BASE_URL,
        json=req_body,
        timeout=120,
    )
    if resp.status_code != 200:
       raise Exception(f"HTTP {resp.status_code}: {resp.text}")
    return resp.json()

def evaluate_system():
    # Check if server is running
    try:
        requests.get("http://127.0.0.1:8000", timeout=10)
    except requests.exceptions.ConnectionError:
        print("❌ Error: API server is not running at http://127.0.0.1:8000")
        print("Please start the server first using: uvicorn app.main:app")
        return

    results = []
    success_count = 0
    total = len(E2E_CASES)

    print(f"Starting System E2E Evaluation on {total} test flows...\n")

    for i, case in enumerate(E2E_CASES):
        print(f"--- Flow {i+1}/{total}: {case['description']} ---")
        import uuid
        conv_id = str(uuid.uuid4())
        
        try:
            user_email = case.get('user_email')
            
            # Turn 1
            print(f"  User: {case['turn1']}")
            resp1 = post_message(conv_id, case['turn1'], user_email=user_email)
            reply1 = resp1.get("reply", "")
            print(f"  Bot:  {reply1}")
            
            final_reply = reply1
            
            # Turn 2
            if case['turn2']:
                print(f"  User: {case['turn2']}")
                resp2 = post_message(conv_id, case['turn2'], user_email=user_email)
                reply2 = resp2.get("reply", "")
                print(f"  Bot:  {reply2}")
                final_reply = reply2

            # Verification based on final reply
            is_success = all(exp.lower() in final_reply.lower() for exp in case['expected_contains'])
            
            if is_success:
                print("  ✅ Flow Succeeded")
                success_count += 1
            else:
                print(f"  ❌ Flow Failed. Expected to contain: {case['expected_contains']}")
                
            results.append({
                "description": case["description"],
                "success": is_success,
                "final_bot_reply": final_reply,
            })
            
        except Exception as e:
            print(f"  ❌ Flow Failed with Exception: {e}")
            results.append({
                "description": case["description"],
                "success": False,
                "final_bot_reply": str(e),
            })
            
        print()

    accuracy = (success_count / total) * 100
    print("\n================ SYSTEM EVALUATION SUMMARY ================")
    print(f"Overall Flow Accuracy : {accuracy:.2f}% ({success_count}/{total})")
    print("=============================================================\n")

    # Save to CSV
    with open(RESULTS_PATH, "w", newline="", encoding="utf-8") as csvfile:
        if results:
            fieldnames = results[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
    
    print(f"Detailed E2E results saved to: {RESULTS_PATH}")

if __name__ == "__main__":
    evaluate_system()
