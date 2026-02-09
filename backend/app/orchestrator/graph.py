from langgraph.graph import StateGraph, END
from app.orchestrator.state import ConversationState

from app.agents.triage.agent import triage_agent
from app.agents.database.agent import database_agent
from app.agents.policy.agent import policy_agent
from app.agents.resolution.agent import resolution_agent


def should_continue_to_database(state) -> str:
    """Route from triage to database or handoff"""
    if state.get("current_state") == "HUMAN_HANDOFF":
        return "end"
    if state.get("current_state") == "DATA_FETCH":
        return "database"
    return "end"


def should_continue_to_policy(state) -> str:
    """Route from database to policy or handoff"""
    if state.get("current_state") == "HUMAN_HANDOFF":
        return "end"
    if state.get("current_state") == "POLICY_CHECK":
        return "policy"
    return "end"


def should_continue_to_resolution(state) -> str:
    """Route from policy to resolution or handoff"""
    if state.get("current_state") == "HUMAN_HANDOFF":
        return "end"
    if state.get("current_state") == "RESOLUTION":
        return "resolution"
    return "end"


def should_end(state) -> str:
    """Route from resolution to end"""
    if state.get("current_state") == "COMPLETED":
        return "end"
    if state.get("current_state") == "HUMAN_HANDOFF":
        return "end"
    return "end"


def build_graph():
    """
    Builds the LangGraph workflow with conditional edges to prevent loops.
    
    Flow:
    triage -> database -> policy -> resolution -> end
    
    Each step can also route to "end" if handoff is needed.
    """
    graph = StateGraph(ConversationState)

    # Add all agent nodes
    graph.add_node("triage", triage_agent)
    graph.add_node("database", database_agent)
    graph.add_node("policy", policy_agent)
    graph.add_node("resolution", resolution_agent)

    # Set entry point
    graph.set_entry_point("triage")

    # Add conditional edges to prevent loops
    graph.add_conditional_edges(
        "triage",
        should_continue_to_database,
        {
            "database": "database",
            "end": END
        }
    )

    graph.add_conditional_edges(
        "database",
        should_continue_to_policy,
        {
            "policy": "policy",
            "end": END
        }
    )

    graph.add_conditional_edges(
        "policy",
        should_continue_to_resolution,
        {
            "resolution": "resolution",
            "end": END
        }
    )

    graph.add_conditional_edges(
        "resolution",
        should_end,
        {
            "end": END
        }
    )

    return graph.compile()