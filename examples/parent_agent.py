#!/usr/bin/env python3
"""Example: Using RAG agent as a subgraph in a multi-agent system.

This example demonstrates how to integrate the RAG agent as a specialized
node within a larger parent graph that coordinates multiple agents.

Architecture:
    Entry → Router → [RAG Agent | Weather Agent | Calculator] → Response Formatter → END
"""
import os
import httpx
from typing import Literal
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, MessagesState, END

# Import RAG subgraph
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_system.config import RAGConfig
from rag_system.subgraph import create_rag_subgraph


# ============================================================================
# Parent Graph State
# ============================================================================

class ParentState(MessagesState):
    """State for the parent multi-agent system.

    Attributes:
        messages: Chat message history (inherited)
        current_agent: Which specialized agent is currently active
        task_type: Type of task (legal_query, weather, calculation, general)
    """
    current_agent: str = ""
    task_type: str = ""


# ============================================================================
# Router Node
# ============================================================================

def create_router_node(llm: ChatOpenAI):
    """Create a router node that decides which specialized agent to use."""

    ROUTER_PROMPT = """你是一個智慧路由器，負責將使用者的問題分配給最適合的專業代理。

可用的代理：
1. rag_agent - 法律文件問答專家，處理法規、條文相關問題
2. weather_agent - 天氣查詢專家
3. calculator_agent - 數學計算專家
4. general_agent - 一般對話助手

請分析使用者的問題，並選擇最適合的代理。只回覆代理名稱，不要解釋。
"""

    def router_node(state: ParentState) -> dict:
        """Route the question to the appropriate specialized agent."""
        last_message = state['messages'][-1]
        question = last_message.content if hasattr(last_message, 'content') else str(last_message)

        print(f"\n[Router] Analyzing question: {question}")

        # Use LLM to determine routing
        response = llm.invoke([
            {"role": "system", "content": ROUTER_PROMPT},
            {"role": "user", "content": question}
        ])

        agent_choice = response.content.strip().lower()

        # Map to valid agent names
        agent_map = {
            "rag_agent": "rag_agent",
            "weather_agent": "weather_agent",
            "calculator_agent": "calculator_agent",
            "general_agent": "general_agent"
        }

        selected_agent = agent_map.get(agent_choice, "general_agent")
        print(f"[Router] Selected agent: {selected_agent}")

        return {
            "current_agent": selected_agent,
            "task_type": agent_choice
        }

    return router_node


# ============================================================================
# Specialized Agent Nodes (Mock implementations)
# ============================================================================

def create_weather_agent():
    """Mock weather agent (replace with real implementation)."""
    def weather_agent(state: ParentState) -> dict:
        print("[Weather Agent] Processing weather query...")
        response = AIMessage(content="天氣查詢功能尚未實作。這是一個模擬回應。")
        return {"messages": [response]}
    return weather_agent


def create_calculator_agent():
    """Mock calculator agent (replace with real implementation)."""
    def calculator_agent(state: ParentState) -> dict:
        print("[Calculator Agent] Processing calculation...")
        response = AIMessage(content="計算功能尚未實作。這是一個模擬回應。")
        return {"messages": [response]}
    return calculator_agent


def create_general_agent(llm: ChatOpenAI):
    """General conversation agent."""
    def general_agent(state: ParentState) -> dict:
        print("[General Agent] Processing general query...")
        messages = state['messages']
        response = llm.invoke(messages)
        return {"messages": [response]}
    return general_agent


# ============================================================================
# Response Formatter Node
# ============================================================================

def create_response_formatter():
    """Create a node that formats the final response."""
    def response_formatter(state: ParentState) -> dict:
        print("[Response Formatter] Formatting final response...")
        # The messages already contain the agent's response
        # Just mark completion
        return {"current_agent": "completed"}
    return response_formatter


# ============================================================================
# Routing Logic
# ============================================================================

def route_to_agent(state: ParentState) -> Literal["rag_agent", "weather_agent", "calculator_agent", "general_agent"]:
    """Conditional edge: route to the selected agent."""
    agent = state.get("current_agent", "general_agent")
    print(f"[Routing] Directing to: {agent}")
    return agent


# ============================================================================
# Build Parent Graph
# ============================================================================

def build_parent_graph(llm: ChatOpenAI, rag_config: RAGConfig) -> StateGraph:
    """Build the parent multi-agent graph.

    Args:
        llm: Language model for agents
        rag_config: Configuration for RAG subgraph

    Returns:
        Compiled parent graph
    """
    print("Building parent graph with RAG subgraph...")

    # Create the parent graph with ParentState
    graph = StateGraph(ParentState)

    # Create specialized agents
    router = create_router_node(llm)
    rag_subgraph = create_rag_subgraph(llm, rag_config, name="rag_legal_expert")
    weather_agent = create_weather_agent()
    calculator_agent = create_calculator_agent()
    general_agent = create_general_agent(llm)
    formatter = create_response_formatter()

    # Add nodes
    graph.add_node("router", router)
    graph.add_node("rag_agent", rag_subgraph)  # RAG as subgraph
    graph.add_node("weather_agent", weather_agent)
    graph.add_node("calculator_agent", calculator_agent)
    graph.add_node("general_agent", general_agent)
    graph.add_node("formatter", formatter)

    # Set entry point
    graph.set_entry_point("router")

    # Conditional routing after router
    graph.add_conditional_edges(
        "router",
        route_to_agent,
        {
            "rag_agent": "rag_agent",
            "weather_agent": "weather_agent",
            "calculator_agent": "calculator_agent",
            "general_agent": "general_agent"
        }
    )

    # All agents flow to formatter
    graph.add_edge("rag_agent", "formatter")
    graph.add_edge("weather_agent", "formatter")
    graph.add_edge("calculator_agent", "formatter")
    graph.add_edge("general_agent", "formatter")

    # Formatter to END
    graph.add_edge("formatter", END)

    print("Parent graph built successfully")
    return graph.compile()


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Run the parent multi-agent system."""
    load_dotenv()

    # Configuration
    rag_config = RAGConfig.from_env()
    rag_config.validate()

    # Create LLM
    client = httpx.Client(
        verify=rag_config.verify_ssl,
        follow_redirects=True,
        timeout=httpx.Timeout(120.0, connect=10.0)
    )
    llm = ChatOpenAI(
        model=rag_config.chat_model,
        openai_api_key=rag_config.embed_api_key,
        openai_api_base=rag_config.embed_api_base,
        temperature=0,
        http_client=client
    )

    # Build parent graph
    parent_graph = build_parent_graph(llm, rag_config)

    # Test questions for different agents
    test_questions = [
        "陸海空軍懲罰法第24條的內容是什麼？",  # Should route to RAG
        "今天台北的天氣如何？",  # Should route to Weather (mock)
        "計算 123 * 456",  # Should route to Calculator (mock)
        "你好嗎？"  # Should route to General
    ]

    print("\n" + "="*80)
    print("PARENT MULTI-AGENT SYSTEM - DEMO")
    print("="*80)

    for question in test_questions:
        print(f"\n{'='*80}")
        print(f"User Question: {question}")
        print(f"{'='*80}")

        # Initialize state
        initial_state = {
            "messages": [HumanMessage(content=question)],
            "current_agent": "",
            "task_type": ""
        }

        # Run graph
        try:
            final_state = parent_graph.invoke(initial_state)

            # Extract response
            if final_state.get('messages'):
                final_message = final_state['messages'][-1]
                response = final_message.content if hasattr(final_message, 'content') else str(final_message)
                print(f"\n[Final Response]\n{response}")
            else:
                print("\n[Error] No response generated")

        except Exception as e:
            print(f"\n[Error] {str(e)}")

    print("\n" + "="*80)
    print("DEMO COMPLETED")
    print("="*80)


if __name__ == "__main__":
    main()
