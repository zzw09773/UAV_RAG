"""Design area routing tool for DATCOM assistant."""
from typing import Callable, List
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from ..common import log
from ..build.db_utils import get_collection_stats

ROUTER_PROMPT_TEMPLATE = """You are an expert routing system for design domains. Based on the engineer's question and the list of available design domain databases, your task is to select the most relevant domain to answer the question.

Engineer's Question: "{query}"

Available Design Domains and Document Counts:
{collections_info}

**Routing Rules:**
1. Prioritize domains with document count > 0
2. If multiple domains have documents, select the most relevant one
3. If all domains have no documents, return the domain name with the highest count
4. Return ONLY the domain name, no additional text

**Output the most suitable design domain name in Traditional Chinese (zh-TW).**"""

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
