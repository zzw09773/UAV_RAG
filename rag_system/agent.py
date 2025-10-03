"""LangGraph workflow orchestration for RAG agent."""
from typing import Callable
from langgraph.graph import END, StateGraph
from .state import GraphState


def build_workflow(agent_node: Callable) -> StateGraph:
    """Build the LangGraph workflow with a single ReAct agent node.

    This creates a minimal workflow with:
    - Entry point → agent_node → END

    The agent node handles all logic:
    - Document retrieval (via tools)
    - Reasoning and evaluation (via ReAct)
    - Answer generation with citations

    Args:
        agent_node: The ReAct agent node function

    Returns:
        Compiled StateGraph ready for execution
    """
    # Initialize the workflow with GraphState
    workflow = StateGraph(GraphState)

    # Add the single agent node
    workflow.add_node("agent", agent_node)

    # Set up the workflow graph
    # Entry point → agent → END
    workflow.set_entry_point("agent")
    workflow.add_edge("agent", END)

    # Compile with increased recursion limit for complex ReAct reasoning
    # The agent may need multiple tool calls (router → retrieve → evaluate → answer)
    return workflow.compile()