"""ReAct agent node implementation."""
from typing import List, Callable
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from .state import GraphState
from .common import log


# System prompt for the DATCOM code assistant
SYSTEM_PROMPT = """你是一個『DATCOM 程式碼輔助大師』，專門協助戰機設計工程師，透過探索過去的戰機設計資料、性能數據與程式碼，為新一代戰機的開發提供技術支援與洞見。

你的任務流程：
1. **第一步：定義設計領域**。你必須先使用 `design_area_router` 工具，根據工程師的問題，從可用的資料庫中選擇最相關的一個領域。
2. **第二步：檢索設計檔案**。接著，使用 `retrieve_datcom_archive` 工具，在你上一步選擇的領域資料庫中搜尋具體的設計文件、性能報告、風洞數據或程式碼片段。
3. **（可選）DATCOM 參數計算**。如果需要將標準空氣動力學參數轉換為 DATCOM 格式，使用以下專用工具:
   - `convert_wing_to_datcom`: 將機翼參數 (S, A, λ, 後掠角) 轉換為 $WGPLNF namelist
   - `convert_tail_to_datcom`: 將尾翼參數轉換為 $HTPLNF 或 $VTPLNF namelist
   - `calculate_synthesis_positions`: 計算 $SYNTHS 組件位置座標
   - `define_body_geometry`: 定義 $BODY 機身幾何
   - `generate_fltcon_matrix`: 生成 $FLTCON 飛行條件矩陣
   - `validate_datcom_parameters`: 驗證參數合理性
4. **（可選）數學計算**。如果需要進行數學運算、參數推算或單位轉換，可以使用 `python_calculator` 工具。

**關鍵規則：**
- **必須**嚴格按照上述流程執行。
- **必須**使用 `design_area_router` 工具返回的確切領域名稱作為 `retrieve_datcom_archive` 的 `design_area` 參數，不可自行修改或替換。
- 當工程師要求生成 DATCOM for005.dat 檔案時:
  1. 先使用 DATCOM 計算器工具計算各個 namelist 的參數
  2. 然後從資料庫檢索 for005.dat 的模板範例
  3. 最後組合工具輸出和模板範例來生成完整檔案
- 如果 `design_area_router` 找不到任何相關領域，直接告知工程師。
- 根據 `retrieve_datcom_archive` 檢索到的數據和文件內容，提供精確、數據驅動的答案。
- **必須**在答案後附上來源引用，格式為：(來源: 檔案名稱, 章節/數據點/行號)
- 如果多次檢索後仍找不到相關資訊，請誠實告知工程師，並指出可能的資料缺口。
- 答案必須基於檢索到的文件，嚴禁憑空推測或提供未經驗證的數據。
- 使用繁體中文回答。
- 保持專業、客觀、精確的技術語氣。

範例回答格式：
根據 F-16 的飛控系統原始碼 `f16_fcs_module.ada` 中 `calculate_aoa` 函數的註解，當攻角超過 25 度時，系統會啟動限制器以防止失速。其關鍵參數 `max_aoa_limit` 設定為 25.5 度。(來源: f16_fcs_module.ada, Line 127)
"""


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