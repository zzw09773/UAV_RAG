"""DATCOM archive retrieval tool for aircraft design assistant."""
from typing import Callable, Optional
from langchain.tools import tool
from .shared import get_vectorstore
from ..common import log
from ..config import DEFAULT_TOP_K, DEFAULT_CONTENT_MAX_LENGTH


def create_retrieve_tool(
    conn_str: str,
    embed_api_base: str,
    embed_api_key: str,
    embed_model: str,
    verify_ssl: bool,
    top_k: int = DEFAULT_TOP_K,
    content_max_length: int = DEFAULT_CONTENT_MAX_LENGTH
) -> Callable:
    """Create a DATCOM archive retrieval tool for searching design documents and code.

    Args:
        conn_str: The database connection string.
        embed_api_base: Embedding API base URL.
        embed_api_key: Embedding API key.
        embed_model: Embedding model name.
        verify_ssl: Flag to verify SSL.
        top_k: Number of documents to retrieve (default: from config.DEFAULT_TOP_K)
        content_max_length: Maximum length for document content (default: from config.DEFAULT_CONTENT_MAX_LENGTH)

    Returns:
        A tool function that can be used by the ReAct agent.
    """
    @tool
    def retrieve_datcom_archive(query: str, design_area: str) -> str:
        """Search for relevant aircraft design documents, performance data, and code in a specific design area.

        Use this tool to find historical design documents, wind tunnel data, performance reports,
        and source code from past aircraft projects.
        You MUST specify which design area to search in.

        Args:
            query: The engineering query or technical search terms. Use specific technical keywords, aircraft models, or component names.
            design_area: The name of the design area to search within (e.g., '空氣動力學', '航電系統').
                        You should determine this using the design_area_router tool first.

        Returns:
            Formatted design documents with technical data and source citations, or an error message.
        """
        log(f"Retrieving DATCOM archive for query: '{query}' in design area: '{design_area}'")

        try:
            # Get a vectorstore instance for the dynamically specified design area
            vectorstore = get_vectorstore(
                connection_string=conn_str,
                collection_name=design_area,
                api_base=embed_api_base,
                api_key=embed_api_key,
                embed_model=embed_model,
                verify_ssl=verify_ssl
            )

            documents = vectorstore.similarity_search(query, k=top_k)

            if not documents:
                log(f"No documents retrieved from design area '{design_area}'")
                return f"在『{design_area}』領域中找不到相關的設計文件或程式碼。建議重新檢查查詢關鍵字或嘗試其他設計領域。"

            log(f"Retrieved {len(documents)} design documents from '{design_area}'")

            # Format documents for LLM consumption
            result_parts = []
            for i, doc in enumerate(documents, 1):
                source = doc.metadata.get('source', 'unknown')
                page = doc.metadata.get('page', '?')
                section = doc.metadata.get('section', '')
                line = doc.metadata.get('line', '')
                content = doc.page_content

                if len(content) > content_max_length:
                    content = content[:content_max_length] + "..."

                # Format location info
                location = f"頁碼: {page}"
                if section:
                    location += f", 章節: {section}"
                if line:
                    location += f", Line {line}"

                formatted_doc = (
                    f"=== 文件 {i} (來自『{design_area}』領域) ===\n"
                    f"來源: {source}, {location}\n"
                    f"內容:\n{content}\n"
                )
                result_parts.append(formatted_doc)

            return "\n---\n".join(result_parts)

        except Exception as e:
            error_msg = f"從『{design_area}』領域檢索文件時發生錯誤: {str(e)}"
            log(f"ERROR: {error_msg}")
            return error_msg

    return retrieve_datcom_archive
