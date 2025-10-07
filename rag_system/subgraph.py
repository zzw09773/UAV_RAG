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

    Example:
        >>> from langchain_openai import ChatOpenAI
        >>> from rag_system.config import RAGConfig
        >>> from rag_system.subgraph import create_rag_subgraph
        >>>
        >>> llm = ChatOpenAI(model="gpt-4", temperature=0)
        >>> config = RAGConfig.from_env()
        >>> rag_subgraph = create_rag_subgraph(llm, config)
        >>>
        >>> # Use in parent graph
        >>> from langgraph.graph import StateGraph, MessagesState
        >>> parent_graph = StateGraph(MessagesState)
        >>> parent_graph.add_node("rag_agent", rag_subgraph)
    """
    log(f"Creating RAG subgraph: {name}")

    # Create tools with config
    router_tool = create_router_tool(llm, config.conn_string)
    retrieve_tool = create_retrieve_tool(
        conn_str=config.conn_string,
        embed_api_base=config.embed_api_base,
        embed_api_key=config.embed_api_key,
        embed_model=config.embed_model,
        verify_ssl=config.verify_ssl,
        top_k=config.top_k,
        content_max_length=config.content_max_length
    )
    metadata_search_tool = create_metadata_search_tool(
        conn_str=config.conn_string
    )
    
    # Create DATCOM calculator tools
    datcom_tools = create_datcom_calculator_tools()
    
    # Combine all tools
    tools = [router_tool, retrieve_tool, metadata_search_tool] + datcom_tools

    # Create agent node
    agent_node = create_agent_node(llm, tools)

    # Build and compile workflow
    workflow = build_workflow(agent_node)

    log(f"RAG subgraph '{name}' created successfully")
    return workflow


def create_rag_subgraph_from_args(
    llm: ChatOpenAI,
    conn_string: str,
    embed_api_base: str,
    embed_api_key: str,
    embed_model: str = "nvidia/nv-embed-v2",
    verify_ssl: bool = False,
    top_k: int = 10,
    content_max_length: int = 800,
    name: str = "rag_agent"
) -> StateGraph:
    """Create RAG subgraph from individual arguments (convenience wrapper).

    Args:
        llm: The language model to use
        conn_string: PostgreSQL connection string
        embed_api_base: Embedding API base URL
        embed_api_key: Embedding API key
        embed_model: Embedding model name
        verify_ssl: Whether to verify SSL certificates
        top_k: Number of documents to retrieve
        content_max_length: Max content length for retrieved docs
        name: Subgraph name

    Returns:
        Compiled StateGraph ready for use as subgraph
    """
    config = RAGConfig(
        conn_string=conn_string,
        embed_api_base=embed_api_base,
        embed_api_key=embed_api_key,
        embed_model=embed_model,
        verify_ssl=verify_ssl,
        top_k=top_k,
        content_max_length=content_max_length
    )

    return create_rag_subgraph(llm, config, name)


# Convenience function for testing/debugging
def test_subgraph_standalone(question: str, config: RAGConfig):
    """Test the subgraph in standalone mode.

    Args:
        question: Question to ask
        config: RAG configuration

    Returns:
        Final state after processing
    """
    import httpx
    from .common import set_quiet_mode

    set_quiet_mode(False)  # Enable logging for debugging

    # Create LLM
    client = httpx.Client(
        verify=config.verify_ssl,
        follow_redirects=True,
        timeout=httpx.Timeout(120.0, connect=10.0)
    )
    llm = ChatOpenAI(
        model=config.chat_model,
        openai_api_key=config.embed_api_key,
        openai_api_base=config.embed_api_base,
        temperature=config.temperature,
        http_client=client
    )

    # Create subgraph
    subgraph = create_rag_subgraph(llm, config, name="test_rag")

    # Test with question
    initial_state = {
        "question": question,
        "generation": "",
        "messages": []
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

    # Run test
    question = "陸海空軍懲罰法第24條"
    result = test_subgraph_standalone(question, config)

    print("\n=== Test Result ===")
    print(f"Question: {result.get('question', 'N/A')}")
    print(f"Answer: {result.get('generation', 'N/A')}")
    print(f"Messages: {len(result.get('messages', []))} messages")
