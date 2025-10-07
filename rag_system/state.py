"""GraphState definition for RAG agent workflow."""
from typing import TypedDict, Annotated
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages


class GraphState(MessagesState):
    """State structure for the RAG agent workflow.

    Extends MessagesState to enable parent graph integration while maintaining
    backward compatibility with standalone mode.

    Attributes:
        messages: Chat message history (inherited from MessagesState)
        question: The user's original question (for backward compatibility)
        generation: The final generated answer with citations
        collection: Selected collection name (from router tool)
        retrieved_docs: Documents retrieved from vectorstore
        intent: Routing intent (datcom_generation or general_query)
    """
    question: str = ""
    generation: str = ""
    collection: str = ""
    retrieved_docs: list = []
    intent: str = ""


# Backward compatibility: TypedDict version for legacy code
class LegacyGraphState(TypedDict):
    """Legacy state structure for backward compatibility.

    Use GraphState (MessagesState-based) for new code.

    Attributes:
        question: The user's original question
        generation: The final generated answer with citations
    """
    question: str
    generation: str