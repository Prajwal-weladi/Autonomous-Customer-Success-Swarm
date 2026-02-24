import sys
import os
import json
import csv
from pathlib import Path

# Ensure the backend directory is in the PYTHONPATH so module imports work
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.agents.triage.agent import run_triage

DATASET_PATH = Path(__file__).parent / "golden_dataset.json"
RESULTS_PATH = Path(__file__).parent / "eval_results.csv"

def evaluate_triage():
    if not DATASET_PATH.exists():
        print(f"Error: Dataset not found at {DATASET_PATH}")
        return

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    results = []
    correct_intents = 0
    correct_urgencies = 0
    correct_entities = 0
    total = len(dataset)

    print(f"Starting Evaluation on {total} test cases...\n")

    for i, test_case in enumerate(dataset):
        query = test_case.get("user_query", "")
        expected_intent = test_case.get("expected_intent")
        expected_urgency = test_case.get("expected_urgency")
        expected_order_id = test_case.get("expected_order_id")

        print(f"Test {i+1}/{total}: '{query}'")
        
        # Run triage agent
        triage_out = run_triage(query)
        
        actual_intent = triage_out.get("intent")
        actual_urgency = triage_out.get("urgency")
        actual_order_id = triage_out.get("order_id")

        intent_match = (actual_intent == expected_intent)
        urgency_match = (actual_urgency == expected_urgency)
        
        # Normalize order ID types
        actual_order_id_str = str(actual_order_id) if actual_order_id else None
        expected_order_id_str = str(expected_order_id) if expected_order_id else None
        
        entity_match = (actual_order_id_str == expected_order_id_str)
        
        if intent_match:
            correct_intents += 1
        else:
            print(f"  ❌ Intent Mismatch: Expected '{expected_intent}', got '{actual_intent}'")
            
        if urgency_match:
            correct_urgencies += 1
        else:
            print(f"  ❌ Urgency Mismatch: Expected '{expected_urgency}', got '{actual_urgency}'")
            
        if entity_match:
            correct_entities += 1
        else:
            print(f"  ❌ Entity Mismatch: Expected '{expected_order_id_str}', got '{actual_order_id_str}'")

        results.append({
            "query": query,
            "expected_intent": expected_intent,
            "actual_intent": actual_intent,
            "intent_match": intent_match,
            "expected_urgency": expected_urgency,
            "actual_urgency": actual_urgency,
            "urgency_match": urgency_match,
            "expected_order_id": expected_order_id_str,
            "actual_order_id": actual_order_id_str,
            "entity_match": entity_match
        })
        print("---")

    intent_accuracy = (correct_intents / total) * 100
    urgency_accuracy = (correct_urgencies / total) * 100
    entity_accuracy = (correct_entities / total) * 100

    print("\n================ EVALUATION SUMMARY ================")
    print(f"Intent Accuracy   : {intent_accuracy:.2f}% ({correct_intents}/{total})")
    print(f"Urgency Accuracy  : {urgency_accuracy:.2f}% ({correct_urgencies}/{total})")
    print(f"Entity Extraction : {entity_accuracy:.2f}% ({correct_entities}/{total})")
    print("=====================================================\n")

    # Save to CSV
    with open(RESULTS_PATH, "w", newline="", encoding="utf-8") as csvfile:
        if results:
            fieldnames = results[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
    
    print(f"Detailed results saved to: {RESULTS_PATH}")

if __name__ == "__main__":
    evaluate_triage()
