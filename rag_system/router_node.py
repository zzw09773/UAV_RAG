"""
Intent routing node for the RAG agent.
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from .state import GraphState
from .common import log

ROUTER_SYSTEM_PROMPT = """You are an expert at routing a user's request to the correct workflow.
Based on the user's question, you must decide whether it is a "datcom_generation" request or a "general_query".

**Analysis Steps:**
1. Look for keywords related to **generation**, such as "generate", "create", "make", "生成", "產生", "建立".
2. Look for a significant number of specific aerodynamic parameters (e.g., S=..., A=..., Mach=..., XCG=...).
3. If generation keywords OR multiple specific parameters are present, classify as "datcom_generation".
4. Otherwise, classify as "general_query".

**Examples:**
- User query: "為 XX 生成 .dat or DATCOM。參數: 機翼 S=530 ft², A=2.8..." -> **datcom_generation** (Contains "生成" and many parameters)
- User query: "Create a DATCOM file for a custom UAV with wing area 50 and aspect ratio 3." -> **datcom_generation** (Contains "Create" and parameters)
- User query: "MiG-17的DATCOM" -> **general_query** (Lacks generation keywords and specific parameters. This is a retrieval/search request.)
- User query: "What is the purpose of the FLTCON namelist?" -> **general_query** (This is a definition question.)
- User query: "explain the body geometry of the F-4" -> **general_query** (This is a search/explanation request.)

You must respond with ONLY the name of the route, either "datcom_generation" or "general_query".
"""

def create_intent_router_node(llm: ChatOpenAI) -> callable:
    """
    Creates a node that routes the user's query to the correct workflow.

    Args:
        llm: The language model to use for routing.

    Returns:
        A node function for the graph.
    """
    # Use simple string output parser for better compatibility
    prompt = ChatPromptTemplate.from_messages([
        ("system", ROUTER_SYSTEM_PROMPT),
        ("human", "{question}"),
    ])
    
    router = prompt | llm | StrOutputParser()

    def intent_router_node(state: GraphState) -> dict:
        """
        Routes the user's request to the correct workflow.

        Args:
            state: The current graph state.

        Returns:
            A dictionary with the updated intent and initialized messages.
        """
        from langchain_core.messages import HumanMessage
        
        log("--- ROUTING INTENT ---")
        question = state["question"]
        log(f"Routing question: {question}")

        result = router.invoke({"question": question})
        
        # Clean up the result and validate
        route = result.strip().lower()
        if "datcom" in route:
            route = "datcom_generation"
        elif "general" in route:
            route = "general_query"
        else:
            # Default to general_query if unclear
            log(f"Warning: Unclear routing result '{result}', defaulting to general_query")
            route = "general_query"
        
        log(f"Routing decision: {route}")
        
        # Initialize messages if not present
        update_dict = {"intent": route}
        if not state.get("messages"):
            update_dict["messages"] = [HumanMessage(content=question)]
        
        return update_dict

    return intent_router_node
