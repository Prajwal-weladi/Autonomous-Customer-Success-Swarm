# Autonomous Customer Success Swarm: Evaluation & Accuracy Report

This report outlines the accuracy, performance, and validation status of the system based on quantitative test sets and live edge-to-edge system data.

## 1. Triage Agent (LLM-Based Natural Language Understanding)
The Triage agent is responsible for classifying a user's text message into one of several predefined intents, assigning urgency, and extracting entities. This evaluation was run using the `llama3.2:latest` model against `golden_dataset.json`.

**Dataset Size:** 10 diverse examples (including order status, returns, multi-turn contexts, missing variables).

| Metric | Accuracy | Description |
| :--- | :--- | :--- |
| **Entity Extraction (Order IDs)** | **100%** | The triage agent perfectly isolated unstructured order numbers exactly where expected and accurately ignored non-order numbers. |
| **Urgency Detection** | **70%** | Accurately triggered immediately on "high" urgency signals ("ASAP!!", "angry", "urgent"). Normal delays occasionally skewed to standard priority. |
| **Intent Classification** | **70%** | Strong boundary detection for complaints, status tracking, and general chitchat. Misses often occur between similar edge cases (e.g. canceling an order vs asking a general question implicitly). |

*Raw data available in `evals/eval_results.csv`*

---

## 2. Full System E2E Pipeline Evaluation
The full pipeline evaluation runs end-to-end multi-turn sequences hitting the live routing API endpoints. It tracks context, confirms inputs across turns, queries the live test database, and acts upon the output.

**Scope:** 4 complex End-to-End Chat Sequences covering missing states, dynamic memory, query resolution via external user inputs (email mapping), and state transitions.

| E2E Flow test case | Result | Status Validation |
| :--- | :--- | :--- |
| **Flow 1: Order Status check with missing user ID - Multi-turn** | ✅ Passed | The system asks user for ID first, parses standard response containing only ID, pulls DB record, returns exact real-time order status properly formatted. |
| **Flow 2: Email input to list orders** | ✅ Passed | Bot identifies it needs an email, validates user against existing datasets, fetches all active/cancelled orders linked to that user without exposing IDs globally. |
| **Flow 3: List orders via email and interact with one order** | ✅ Passed | Handles the cross-action list context correctly. Starts an interaction asking for refund on an exact ID that was referenced dynamically during text parsing. |
| **Flow 4: Direct return request with order ID** | ✅ Passed | Identifies immediate actionable intent across all boundaries, pulls order details, and instantly prompts for actionable resolution ('Yes/No'). |

**Overall Flow Accuracy: 100% (4/4 complete state flows succeeded).**

*Detailed interaction transcripts available in `evals/e2e_results.csv`*

---

## Conclusion
The **Autonomous Customer Success Swarm** is successfully hitting **100% reliability** on its primary multi-turn state flows over the live pipeline API. The local LLM `llama3.2:latest` is securely picking up conversational patterns and mapping them effectively into Database retrieval endpoints and pipeline states while adhering dynamically to missing requirements without losing data streams. 

*Report generated automatically from latest evaluation endpoints.*
