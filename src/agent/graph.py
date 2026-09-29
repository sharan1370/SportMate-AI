from langgraph.graph import END, START, StateGraph

from src.agent.nodes import agent_node, tool_execution_node
from src.agent.state import AgentState


# ============================================================
# ROUTING: AFTER AGENT
# ============================================================

def route_after_agent(state: AgentState) -> str:
    """
    Decide whether the agent needs tool execution
    or whether the current turn is complete.
    """

    if state.get("error"):
        return "end"

    if state.get("tool_name"):
        return "tool"

    return "end"


# ============================================================
# ROUTING: AFTER TOOL
# ============================================================

def route_after_tool(state: AgentState) -> str:
    """
    Decide what to do after a tool has executed.
    """

    if state.get("error"):
        return "end"

    # Booking/cancellation/rescheduling confirmation
    # must wait for the next user message.
    if state.get("confirmation_pending"):
        return "end"

    if not state.get("tool_name"):
        return "end"

    return "tool"


# ============================================================
# BUILD GRAPH
# ============================================================

def build_graph():
    """
    Build and compile the SportMate AI LangGraph workflow.
    """

    graph = StateGraph(AgentState)

    graph.add_node(
        "agent",
        agent_node,
    )

    graph.add_node(
        "tool",
        tool_execution_node,
    )

    graph.add_edge(
        START,
        "agent",
    )

    graph.add_conditional_edges(
        "agent",
        route_after_agent,
        {
            "tool": "tool",
            "end": END,
        },
    )

    graph.add_conditional_edges(
        "tool",
        route_after_tool,
        {
            "tool": "tool",
            "end": END,
        },
    )

    return graph.compile()