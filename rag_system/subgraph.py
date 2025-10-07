"""Subgraph wrapper for RAG agent integration into parent graphs.

This module provides the interface to use the RAG agent as a subgraph node
within a larger multi-agent system.
"""
from typing import Optional, Callable
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph

from .state import GraphState
from .config import RAGConfig
from .tool import create_retrieve_tool, create_router_tool, create_metadata_search_tool, create_datcom_calculator_tools
from .node import create_agent_node
from .router_node import create_intent_router_node
from .datcom_node import create_datcom_sequence_node
from .agent import build_workflow
from .common import log


def create_rag_subgraph(
    llm: ChatOpenAI,
    config: RAGConfig,
    name: str = "rag_agent"
) -> StateGraph:
    """Create a RAG agent subgraph that can be embedded in a parent graph.

    This function wraps the existing RAG agent workflow into a subgraph-compatible
    format that can be added as a node to a parent StateGraph.

    Args:
        llm: The language model to use for the agent
        config: RAG system configuration
        name: Name for the subgraph (default: "rag_agent")

    Returns:
        Compiled StateGraph that can be used as a subgraph node
    """
    log(f"Creating RAG subgraph: {name}")

    # 1. Create tools
    # Tools for the general agent
    general_tools = [
        create_router_tool(llm, config.conn_string),
        create_retrieve_tool(
            conn_str=config.conn_string,
            embed_api_base=config.embed_api_base,
            embed_api_key=config.embed_api_key,
            embed_model=config.embed_model,
            verify_ssl=config.verify_ssl,
            top_k=config.top_k,
            content_max_length=config.content_max_length
        ),
        create_metadata_search_tool(conn_str=config.conn_string)
    ]
    
    # DATCOM tools are used by both the general agent (for simple queries)
    # and the specialized DATCOM node.
    datcom_tools = create_datcom_calculator_tools()
    all_tools = general_tools + datcom_tools

    # 2. Create nodes
    router_node = create_intent_router_node(llm)
    datcom_node = create_datcom_sequence_node(llm)
    general_agent_node = create_agent_node(llm, all_tools)

    # 3. Build and compile the branching workflow
    workflow = build_workflow(
        router_node=router_node,
        datcom_node=datcom_node,
        general_agent_node=general_agent_node
    )

    log(f"RAG subgraph '{name}' created successfully with routing")
    return workflow


def create_rag_subgraph_from_args(
    llm: ChatOpenAI,
    conn_string: str,
    embed_api_base: str,
    embed_api_key: str,
    llm_api_base: Optional[str] = None,
    embed_model: str = "nvidia/nv-embed-v2",
    verify_ssl: bool = False,
    top_k: int = 10,
    content_max_length: int = 800,
    name: str = "rag_agent"
) -> StateGraph:
    """Create RAG subgraph from individual arguments (convenience wrapper)."""
    config = RAGConfig(
        conn_string=conn_string,
        embed_api_base=embed_api_base,
        llm_api_base=llm_api_base,
        embed_api_key=embed_api_key,
        embed_model=embed_model,
        verify_ssl=verify_ssl,
        top_k=top_k,
        content_max_length=content_max_length
    )

    return create_rag_subgraph(llm, config, name)


# Convenience function for testing/debugging
def test_subgraph_standalone(question: str, config: RAGConfig):
    """Test the subgraph in standalone mode."""
    import httpx
    from .common import set_quiet_mode

    set_quiet_mode(False)  # Enable logging for debugging

    # Create LLM
    client = httpx.Client(
        verify=config.verify_ssl,
        follow_redirects=True,
        timeout=httpx.Timeout(120.0, connect=10.0)
    )
    
    api_base = config.llm_api_base or config.embed_api_base
    log(f"Initializing ChatOpenAI for subgraph test with API base: {api_base}")

    llm = ChatOpenAI(
        model=config.chat_model,
        openai_api_key=config.embed_api_key,
        openai_api_base=api_base,
        temperature=config.temperature,
        http_client=client
    )

    # Create subgraph
    subgraph = create_rag_subgraph(llm, config, name="test_rag")

    # Test with question
    initial_state = {
        "question": question,
        "generation": "",
        "messages": [("user", question)] # Initialize messages for the router
    }

    log(f"Testing subgraph with question: {question}")
    result = subgraph.invoke(
        initial_state,
        config={"recursion_limit": 50}
    )

    log("Subgraph test completed")
    return result


if __name__ == "__main__":
    """Quick test of subgraph functionality."""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    # Test configuration
    config = RAGConfig.from_env()
    config.validate()

    # Test with a general question
    print("--- TESTING GENERAL QUERY ---")
    general_question = "FLTCON namelist 用來定義什麼？"
    general_result = test_subgraph_standalone(general_question, config)
    print("\n=== General Test Result ===")
    print(f"Question: {general_result.get('question', 'N/A')}")
    print(f"Answer: {general_result.get('generation', 'N/A')}")

    # Test with a DATCOM generation question
    print("\n--- TESTING DATCOM GENERATION QUERY ---")
    datcom_question = """根據參數生成完整 DATCOM .dat:
機翼: S=530 ft², A=2.8, λ=0.3, 後掠角45°
飛行: Mach 0.8, 高度10000 ft, 攻角-2到10度每2度, 重量40000 lbs  
機身: 長63 ft, 最大直徑3 ft
位置: XCG=25 ft, XW=18.5 ft, XH=49 ft"""
    datcom_result = test_subgraph_standalone(datcom_question, config)
    print("\n=== DATCOM Test Result ===")
    print(f"Question: {datcom_question}")
    print(f"Answer: {datcom_result.get('generation', 'N/A')}")
