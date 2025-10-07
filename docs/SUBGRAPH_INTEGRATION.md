# RAG Subgraph Integration Guide

This guide explains how to integrate the RAG system as a specialized subgraph node into a larger supervisor agent built with LangGraph.

## 1. Core Concept

The RAG system is designed to be a self-contained "expert" that can be plugged into a larger multi-agent workflow. It exposes a single entry point, `create_rag_subgraph`, which returns a compiled LangGraph `StateGraph` object.

This subgraph handles all the complexity of routing, retrieval, and answer generation internally. The supervisor agent only needs to delegate a task to it and receive the final answer.

**Internal Flow:**
1.  The subgraph receives the state from the supervisor, expecting the user's query in the `messages` list.
2.  The internal ReAct agent (`agent_node`) is invoked.
3.  The agent uses its specialized tools (`design_area_router`, `retrieve_datcom_archive`, etc.) to reason and find information.
4.  After its internal process is complete, it populates the `generation` field in its state with the final, citable answer.
5.  The subgraph returns control to the parent graph.

## 2. Configuration

The RAG subgraph requires specific environment variables to be set for its dependencies (database and APIs). Ensure the supervisor's environment has a `.env` file or that these variables are exported.

**Required `.env` variables:**

```env
# URL for the PostgreSQL database with pgvector enabled.
PGVECTOR_URL="postgresql+psycopg2://postgres:postgres@localhost:5433/postgres"

# API credentials for the embedding and chat models.
EMBED_API_KEY="your_api_key_here"
EMBED_API_BASE="https://your_api_server/v1"

# (Optional) Specify model names if they differ from the defaults.
EMBED_MODEL_NAME="nvidia/nv-embed-v2"
CHAT_MODEL_NAME="openai/gpt-oss-20b"
```

The subgraph is configured via a `RAGConfig` object. The easiest way to create this is by using the class method `RAGConfig.from_env()`.

## 3. Integration Steps

Here is a practical example of how to add the RAG subgraph to a supervisor agent.

### Step 1: Import Necessary Components

In your supervisor agent's main file, you will need to import the `create_rag_subgraph` function and the `RAGConfig` class.

```python
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState

# Imports from the RAG system
from rag_system.subgraph import create_rag_subgraph
from rag_system.config import RAGConfig
```

### Step 2: Initialize the LLM and RAG Subgraph

The `create_rag_subgraph` function requires an LLM instance and a configuration object.

```python
# Assume the parent graph's LLM is already initialized.
# This LLM will be used by the RAG agent for its internal reasoning.
llm = ChatOpenAI(model="openai/gpt-oss-20b", temperature=0)

# Create the RAG configuration from environment variables.
rag_config = RAGConfig.from_env()
rag_config.validate() # Ensures all required variables are present.

# Create the RAG subgraph node.
rag_node = create_rag_subgraph(llm, rag_config, name="datcom_expert")
```

### Step 3: Add the Subgraph to the Supervisor Graph

Add the `rag_node` to your supervisor's `StateGraph` just like any other node.

```python
# Define the state for the supervisor agent. It must be compatible with MessagesState.
class SupervisorState(MessagesState):
    # Add any other fields your supervisor needs.
    pass

# Create the supervisor graph.
supervisor_graph = StateGraph(SupervisorState)

# Add the RAG subgraph as a callable node.
supervisor_graph.add_node("datcom_expert", rag_node)

# ... define other nodes and edges for your supervisor ...
```

### Step 4: Route Tasks to the Subgraph

Your supervisor's routing logic will decide when to call the RAG expert. When it does, the state is passed directly to the node.

```python
# Example of an edge that routes to the RAG node.
supervisor_graph.add_conditional_edges(
    "router_node",
    lambda state: "datcom_expert" if should_delegate_to_rag(state) else "other_tool",
    {"datcom_expert": "datcom_expert", "other_tool": "other_tool_node"}
)

# The subgraph node should typically route back to a central node in the supervisor
# to evaluate the result and continue the process.
supervisor_graph.add_edge("datcom_expert", "supervisor_evaluator_node")
```

## 4. Data Flow: Input and Output

The RAG subgraph communicates via the shared `GraphState`.

-   **Input**: The supervisor must ensure the user's question is the **last message** in the `messages` list of the state object before calling the RAG node.
-   **Output**: After the RAG node finishes, the `generation` field in the state will contain the final answer as a string. The `messages` list will also be updated with the agent's internal steps and final answer, which can be useful for debugging.

**Example Invocation from Supervisor:**

```python
# This is what the state might look like before calling the RAG node.
# The supervisor has appended the user's request to the message history.
state = {
    "messages": [
        ("user", "What is the purpose of the FLTCON namelist in a DATCOM for005.dat file?")
    ]
}

# The supervisor invokes the RAG node (LangGraph handles this).
# result_state = rag_node.invoke(state)

# After the node returns, the state will be updated.
# result_state["generation"] will contain the answer.
# e.g., "The FLTCON namelist is used to define the flight conditions... (Source: datcom_manual.pdf, page 52)"
```
