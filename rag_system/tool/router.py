"""Design area routing tool for DATCOM assistant."""
from typing import Callable, List
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from ..common import log
from ..build.db_utils import get_collection_stats

ROUTER_PROMPT_TEMPLATE = """你是一個設計領域的專家路由系統。根據工程師的問題和可用的設計領域資料庫列表，你的任務是選擇最相關的一個領域來回答問題。

工程師問題: "{query}"

可用的設計領域及其文件數量:
{collections_info}

**路由規則：**
1. 優先選擇文件數量 > 0 的領域
2. 如果多個領域都有文件，選擇最相關的
3. 如果所有領域都沒有文件，返回文件數最多的領域名稱
4. 只回傳領域名稱，不要包含其他文字

請只回傳最適合的設計領域名稱。"""

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
        This tool will analyze available collections and their document counts
        to select the most appropriate one.

        Args:
            query: The engineer's original query.

        Returns:
            The name of the single best design area to use for the query.
            Returns an error message if no design areas are found.
        """
        log(f"Routing engineer query: '{query}'")

        try:
            # Get collection statistics
            stats = get_collection_stats(conn_str)
            if not stats:
                log("No design areas found in the database.")
                return "錯誤: 資料庫中沒有找到任何設計領域。請先建立資料庫。"

            log(f"Found design areas with stats: {stats}")

            # Filter to only non-empty collections
            non_empty = [s for s in stats if s['doc_count'] > 0]

            if not non_empty:
                log("All collections are empty. Returning error.")
                return "錯誤: 所有設計領域資料庫都是空的。請先匯入文件。"

            # Format the collection info for the prompt
            collections_info = "\n".join([
                f"- {s['name']} ({s['doc_count']} 個文件)"
                for s in stats
            ])

            # Create the prompt for the router LLM
            prompt = ROUTER_PROMPT_TEMPLATE.format(
                query=query,
                collections_info=collections_info
            )

            # Ask the LLM to make a choice
            response = llm.invoke(prompt)
            selected_collection = response.content.strip()

            # Validate the LLM's choice
            collection_names = [s['name'] for s in stats]
            if selected_collection in collection_names:
                log(f"Router selected design area: '{selected_collection}'")
                return selected_collection
            else:
                log(f"Router selected invalid area: '{selected_collection}'. Using collection with most docs.")
                # Fallback: return the collection with the most documents
                return non_empty[0]['name']

        except Exception as e:
            error_msg = f"設計領域路由時發生錯誤: {str(e)}"
            log(f"ERROR: {error_msg}")
            return error_msg

    return design_area_router
