"""LangGraph workflow orchestration for RAG agent."""
from typing import Callable, Literal
from langgraph.graph import END, StateGraph
from .state import GraphState


def should_route_to_datcom(state: GraphState) -> Literal["datcom_sequence", "general_agent"]:
    """Router function to decide the next node based on intent."""
    if state.get("intent") == "datcom_generation":
        return "datcom_sequence"
    return "general_agent"


def build_workflow(
    router_node: Callable,
    datcom_node: Callable,
    general_agent_node: Callable
) -> StateGraph:
    """Build the LangGraph workflow with a router and specialized nodes.

    This creates a branching workflow:
    - Entry point -> router_node
    - router_node -> datcom_node (if intent is datcom_generation) -> END
    - router_node -> general_agent_node (if intent is general_query) -> END

    Args:
        router_node: The node that determines the user's intent.
        datcom_node: The node that runs the fixed DATCOM generation sequence.
        general_agent_node: The ReAct agent node for all other general queries.

    Returns:
        Compiled StateGraph ready for execution.
    """
    # Initialize the workflow with GraphState
    workflow = StateGraph(GraphState)

    # Add the nodes
    workflow.add_node("router", router_node)
    workflow.add_node("datcom_sequence", datcom_node)
    workflow.add_node("general_agent", general_agent_node)

    # Set up the workflow graph
    workflow.set_entry_point("router")

    # Add the conditional routing
    workflow.add_conditional_edges(
        "router",
        should_route_to_datcom,
        {
            "datcom_sequence": "datcom_sequence",
            "general_agent": "general_agent",
        },
    )

    # Add edges from the specialized nodes to the end
    workflow.add_edge("datcom_sequence", END)
    workflow.add_edge("general_agent", END)

    # Compile with increased recursion limit for complex ReAct reasoning
    return workflow.compile()
