from langgraph.graph import StateGraph
from app.orchestrator.state import ConversationState

from app.agents.triage.agent import triage_agent
from app.agents.database.agent import database_agent
from app.agents.policy.agent import policy_agent
from app.agents.resolution.agent import resolution_agent

def build_graph():
    graph = StateGraph(ConversationState)

    graph.add_node("triage", triage_agent)
    graph.add_node("database", database_agent)
    graph.add_node("policy", policy_agent)
    graph.add_node("resolution", resolution_agent)

    graph.set_entry_point("triage")

    graph.add_edge("triage", "database")
    graph.add_edge("database", "policy")
    graph.add_edge("policy", "resolution")
    graph.add_edge("resolution", "__end__")

    return graph.compile()
