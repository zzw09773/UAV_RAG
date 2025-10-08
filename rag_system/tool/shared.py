"""Shared utilities for RAG tools."""
from langchain.vectorstores.pgvector import PGVector
from ..common import LocalApiEmbeddings


def get_vectorstore(
    connection_string: str,
    collection_name: str,
    api_base: str,
    api_key: str,
    embed_model: str,
    verify_ssl: bool = False
) -> PGVector:
    """Create and return a PGVector vectorstore instance.

    Args:
        connection_string: PostgreSQL connection string
        collection_name: Name of the PGVector collection
        api_base: API base URL for embeddings
        api_key: API key for embeddings
        embed_model: Name of the embedding model
        verify_ssl: Whether to verify SSL certificates

    Returns:
        Configured PGVector vectorstore instance
    """
    embedder = LocalApiEmbeddings(
        api_base,
        api_key,
        embed_model,
        verify_ssl=verify_ssl
    )

    return PGVector(
        embedding_function=embedder,
        collection_name=collection_name,
        connection_string=connection_string,
        use_jsonb=True  # 使用 JSONB 儲存 metadata
    )