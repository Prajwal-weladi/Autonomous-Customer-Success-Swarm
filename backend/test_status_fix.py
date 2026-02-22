from app.agents.triage.agent import run_triage

def test_status_classification():
    print("🧪 Testing Status Classification...")
    
    test_messages = [
        "can you give me the status",
        "what is the status",
        "check status",
        "status",
        "the status please"
    ]
    
    for msg in test_messages:
        result = run_triage(msg)
        print(f"Message: '{msg}' -> Intent: {result['intent']}")
        assert result["intent"] == "order_tracking", f"Failed for '{msg}': detected {result['intent']}"
    
    print("✅ All status tests passed!")

if __name__ == "__main__":
    test_status_classification()
