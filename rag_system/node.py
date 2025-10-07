"""ReAct agent node implementation."""
from typing import List, Callable
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from .state import GraphState
from .common import log


# General purpose system prompt
SYSTEM_PROMPT = """You are a helpful assistant expert in aerodynamic analysis and legal document search.
You have access to a variety of tools to help answer user questions.
Based on the user's query, select the best tool or sequence of tools to provide a comprehensive answer."""


def _build_standard_format(tool_responses, ai_responses):
    """Build standard formatted output for tool responses."""
    import json
    answer_parts = ["# 🎯 查詢結果\n"]
    answer_parts.append("根據您的查詢,以下是各工具執行結果:\n")
    
    for idx, tr in enumerate(tool_responses, 1):
        tool_name = tr['name']
        tool_content = tr['content']
        
        answer_parts.append(f"\n## {idx}. 【{tool_name}】\n")
        
        try:
            data = json.loads(tool_content)
            if isinstance(data, dict):
                if 'error' in data:
                    answer_parts.append(f"⚠️ 錯誤: {data['error']}\n")
                else:
                    for key, value in data.items():
                        if key.startswith('_'):
                            continue
                        if isinstance(value, dict):
                            answer_parts.append(f"\n**{key}**:\n")
                            for k, v in value.items():
                                answer_parts.append(f"  - {k}: {v}\n")
                        elif isinstance(value, list):
                            answer_parts.append(f"**{key}**: {value}\n")
                        else:
                            answer_parts.append(f"**{key}** = {value}\n")
            else:
                answer_parts.append(str(data))
        except json.JSONDecodeError:
            answer_parts.append(tool_content)
        
        answer_parts.append("\n---\n")
    
    if ai_responses:
        answer_parts.append("\n## 💡 補充說明:\n")
        for ai_resp in ai_responses:
            answer_parts.append(ai_resp + "\n")
    
    answer_parts.append(f"\n✅ 共執行了 {len(tool_responses)} 個工具,完成查詢。\n")
    
    return "".join(answer_parts)


def create_agent_node(llm: ChatOpenAI, tools: List[Callable]) -> Callable:
    """Create a ReAct agent node for the workflow."""
    agent_executor = create_react_agent(
        llm,
        tools,
        prompt=SYSTEM_PROMPT
    )

    def agent_node(state: GraphState) -> dict:
        """ReAct agent node for general queries."""
        log("--- GENERAL AGENT NODE ---")

        question = state['question']
        # The router ensures the message history is initialized
        messages_input = state['messages']

        # Truncate message history to keep context size under control
        if len(messages_input) > 4:
            log(f"Message history has {len(messages_input)} messages. Truncating to the last 4.")
            messages_input = messages_input[-4:]

        try:
            result = agent_executor.invoke({
                "messages": messages_input
            })

            tool_responses = []
            ai_responses = []
            
            for i, msg in enumerate(result['messages']):
                if type(msg).__name__ == 'ToolMessage':
                    tool_responses.append({
                        'name': getattr(msg, 'name', 'unknown_tool'),
                        'content': msg.content
                    })
                elif type(msg).__name__ == 'AIMessage' and msg.content.strip():
                    ai_responses.append(msg.content.strip())

            final_llm_answer = result['messages'][-1].content if result['messages'] else ""
            
            if not final_llm_answer.strip() or len(final_llm_answer.strip()) < 10:
                log("LLM final answer is empty or too short. Building answer from tool responses...")
                if tool_responses:
                    final_answer = _build_standard_format(tool_responses, ai_responses)
                else:
                    final_answer = "執行了查詢,但沒有獲得有效的工具回應結果。"
            else:
                final_answer = final_llm_answer

            return {
                "generation": final_answer,
                "messages": result['messages']
            }

        except Exception as e:
            error_msg = f"處理問題時發生錯誤: {str(e)}"
            log(f"ERROR in agent_node: {error_msg}")
            import traceback
            log(f"Traceback: {traceback.format_exc()}")
            return {"generation": f"抱歉，{error_msg}"}

    return agent_node
