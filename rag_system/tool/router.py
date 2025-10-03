"""Design area routing tool for DATCOM assistant."""
from typing import Callable, List
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from ..common import log
from ..build.db_utils import get_collection_names

ROUTER_PROMPT_TEMPLATE = """你是一個戰機設計領域的專家路由系統。根據工程師的問題和可用的設計領域資料庫列表，你的任務是選擇最相關的一個領域來回答問題。

工程師問題: "{query}"

可用的設計領域:
{collections}

設計領域說明：
- 空氣動力學: 機翼設計、升力係數、阻力分析、風洞數據、氣動外型
- 航電系統: 飛控系統、雷達、導航、感測器、航電架構、軟體程式碼
- 材料科學: 複合材料、合金、結構強度、耐熱材料、材料測試數據
- 武器掛載: 飛彈掛架、武器整合、電子作戰系統、掛載配置
- 推進系統: 引擎性能、推力向量、燃油系統、進氣道設計

請只回傳最適合的設計領域名稱，不要包含任何其他文字或解釋。"""

def create_router_tool(llm: ChatOpenAI, conn_str: str) -> Callable:
    """Create a design area routing tool for DATCOM assistant.

    Args:
        llm: The language model to use for making the routing decision.
        conn_str: The database connection string.

    Returns:
        A tool function that can be used by the ReAct agent.
    """
    @tool
    def design_area_router(query: str) -> str:
        """Select the most relevant design area to answer an engineer's query.

        Use this tool FIRST to decide which design area database to search in.
        Based on the engineer's query, this tool will determine the most appropriate
        aircraft design domain (aerodynamics, avionics, materials, weapons, propulsion).

        Args:
            query: The engineer's original query.

        Returns:
            The name of the single best design area to use for the query.
            Returns an error message if no design areas are found.
        """
        log(f"Routing engineer query: '{query}'")

        try:
            collection_list = get_collection_names(conn_str)
            if not collection_list:
                log("No design areas found in the database.")
                return "錯誤: 資料庫中沒有找到任何設計領域。請先建立『空氣動力學』、『航電系統』、『材料科學』、『武器掛載』或『推進系統』等領域的資料庫。"

            log(f"Found design areas: {collection_list}")

            # Format the list for the prompt
            formatted_collections = "\n".join([f"- {name}" for name in collection_list])

            # Create the prompt for the router LLM
            prompt = ROUTER_PROMPT_TEMPLATE.format(
                query=query,
                collections=formatted_collections
            )

            # Ask the LLM to make a choice
            response = llm.invoke(prompt)
            selected_collection = response.content.strip()

            # Validate the LLM's choice
            if selected_collection in collection_list:
                log(f"Router selected design area: '{selected_collection}'")
                return selected_collection
            else:
                log(f"Router selected an invalid design area: '{selected_collection}'. Falling back to first available.")
                # Fallback strategy: return the first design area if LLM hallucinates
                return collection_list[0]

        except Exception as e:
            error_msg = f"設計領域路由時發生錯誤: {str(e)}"
            log(f"ERROR: {error_msg}")
            return error_msg

    return design_area_router
