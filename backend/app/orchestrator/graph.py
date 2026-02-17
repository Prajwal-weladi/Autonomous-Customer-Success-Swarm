from langgraph.graph import StateGraph, END
from app.orchestrator.state import ConversationState
from app.utils.logger import get_logger

from app.agents.triage.agent import triage_agent
from app.agents.database.agent import database_agent
from app.agents.policy.agent import policy_agent
from app.agents.resolution.agent import resolution_agent

logger = get_logger(__name__)


def should_continue_to_database(state) -> str:
    """Route from triage to database or handoff"""
    current_state = state.get("current_state")
    if current_state == "HUMAN_HANDOFF":
        logger.info("🔀 Routing: triage → END (handoff)")
        return "end"
    if current_state == "DATA_FETCH":
        logger.info("🔀 Routing: triage → database")
        return "database"
    logger.warning(f"🔀 Routing: triage → END (unexpected state: {current_state})")
    return "end"


def should_continue_to_policy(state) -> str:
    """Route from database to policy or handoff"""
    current_state = state.get("current_state")
    if current_state == "HUMAN_HANDOFF":
        logger.info("🔀 Routing: database → END (handoff)")
        return "end"
    if current_state == "POLICY_CHECK":
        logger.info("🔀 Routing: database → policy")
        return "policy"
    logger.warning(f"🔀 Routing: database → END (unexpected state: {current_state})")
    return "end"


def should_continue_to_resolution(state) -> str:
    """Route from policy to resolution or handoff"""
    current_state = state.get("current_state")
    if current_state == "HUMAN_HANDOFF":
        logger.info("🔀 Routing: policy → END (handoff)")
        return "end"
    if current_state == "RESOLUTION":
        logger.info("🔀 Routing: policy → resolution")
        return "resolution"
    logger.warning(f"🔀 Routing: policy → END (unexpected state: {current_state})")
    return "end"


def should_end(state) -> str:
    """Route from resolution to end"""
    current_state = state.get("current_state")
    if current_state == "COMPLETED":
        logger.info("🔀 Routing: resolution → END (completed)")
        return "end"
    if current_state == "HUMAN_HANDOFF":
        logger.info("🔀 Routing: resolution → END (handoff)")
        return "end"
    logger.info("🔀 Routing: resolution → END")
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