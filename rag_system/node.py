"""ReAct agent node implementation."""
from typing import List, Callable
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from .state import GraphState
from .common import log


# System prompt for the DATCOM code assistant
SYSTEM_PROMPT = """You are a "DATCOM Code Assistant Expert."
- Use tools to answer questions. Your primary tools are `design_area_router` and `retrieve_datcom_archive`.
- You must use `design_area_router` first to select a domain.
- Base all answers on retrieved documents and cite sources in the format: (Source: filename, section/line).
- If no information is found, state that. Do not speculate.
- Output MUST be in Traditional Chinese (zh-TW)."""


def create_agent_node(llm: ChatOpenAI, tools: List[Callable]) -> Callable:
    """Create a ReAct agent node for the workflow.

    Args:
        llm: The language model to use for the agent
        tools: List of tools available to the agent (e.g., retrieve_legal_documents)

    Returns:
        A node function that can be added to the LangGraph workflow
    """
    # Create the ReAct agent with system prompt
    agent_executor = create_react_agent(
        llm,
        tools,
        prompt=SYSTEM_PROMPT
    )

    def agent_node(state: GraphState) -> dict:
        """ReAct agent node - the only node in the workflow.

        This node:
        1. Takes the user's question from state (supports both 'question' and 'messages')
        2. Uses ReAct reasoning (Thought-Action-Observation) to decide which tools to call
        3. Iteratively retrieves documents and reasons about them
        4. Generates a final answer with source citations
        5. Returns the answer in the state

        Args:
            state: Current graph state containing the question or messages

        Returns:
            Updated state dict with the generated answer and messages
        """
        log("--- REACT AGENT NODE ---")

        # Support both standalone mode (question) and subgraph mode (messages)
        if state.get('question'):
            # Standalone mode: use 'question' field
            question = state['question']
            log(f"Processing question (standalone mode): '{question}'")
            messages_input = [("user", question)]
        elif state.get('messages'):
            # Subgraph mode: extract from messages
            last_message = state['messages'][-1]
            question = last_message.content if hasattr(last_message, 'content') else str(last_message)
            log(f"Processing question (subgraph mode): '{question}'")
            messages_input = state['messages']
        else:
            error_msg = "No question or messages found in state"
            log(f"ERROR: {error_msg}")
            return {"generation": f"錯誤: {error_msg}"}

        # Truncate message history to keep context size under control
        if len(messages_input) > 4:
            log(f"Message history has {len(messages_input)} messages. Truncating to the last 4.")
            # Keep the last 4 messages (user/assistant/user/assistant)
            messages_input = messages_input[-4:]

        try:
            # Invoke the ReAct agent
            result = agent_executor.invoke({
                "messages": messages_input
            })

            # Extract the final answer from the agent's messages
            # The last message should be the agent's final response
            final_answer = result['messages'][-1].content

            log(f"Agent completed. Answer length: {len(final_answer)} chars")

            # Return both generation and messages for compatibility
            return {
                "generation": final_answer,
                "messages": result['messages']
            }

        except Exception as e:
            error_msg = f"處理問題時發生錯誤: {str(e)}"
            log(f"ERROR in agent_node: {error_msg}")
            return {"generation": f"抱歉，{error_msg}"}

    return agent_node