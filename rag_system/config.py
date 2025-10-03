"""
RAG System Configuration

Centralized configuration management for the RAG system.
All hardcoded values should be defined here as constants or configurable parameters.
"""

from typing import Optional
from dataclasses import dataclass
import os


# ============================================================================
# RETRIEVAL CONFIGURATION
# ============================================================================

# Default number of documents to retrieve
DEFAULT_TOP_K = 10

# Maximum number of documents to retrieve (safety limit)
MAX_TOP_K = 20

# Minimum number of documents to retrieve
MIN_TOP_K = 1

# Default content truncation length for retrieved documents
DEFAULT_CONTENT_MAX_LENGTH = 800

# Maximum content length (safety limit)
MAX_CONTENT_LENGTH = 2000


# ============================================================================
# MODEL CONFIGURATION
# ============================================================================

DEFAULT_EMBED_MODEL = "nvidia/nv-embed-v2"
DEFAULT_CHAT_MODEL = "openai/gpt-oss-20b"
DEFAULT_TEMPERATURE = 0  # Deterministic by default


# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

# Default collection name if not specified
DEFAULT_COLLECTION = "laws"


# ============================================================================
# RAG CONFIGURATION DATACLASS
# ============================================================================

@dataclass
class RAGConfig:
    """
    Configuration container for RAG system.

    This class holds all configurable parameters for the RAG system,
    making it easy to pass configuration around and override defaults.
    """
    # Retrieval settings
    top_k: int = DEFAULT_TOP_K
    content_max_length: int = DEFAULT_CONTENT_MAX_LENGTH

    # Database settings
    conn_string: Optional[str] = None
    default_collection: str = DEFAULT_COLLECTION

    # Model settings
    embed_model: str = DEFAULT_EMBED_MODEL
    chat_model: str = DEFAULT_CHAT_MODEL
    temperature: float = DEFAULT_TEMPERATURE

    # API settings
    embed_api_base: Optional[str] = None
    embed_api_key: Optional[str] = None

    # SSL settings
    verify_ssl: bool = False

    def __post_init__(self):
        """Validate configuration values."""
        # Validate top_k
        if not MIN_TOP_K <= self.top_k <= MAX_TOP_K:
            raise ValueError(
                f"top_k must be between {MIN_TOP_K} and {MAX_TOP_K}, got {self.top_k}"
            )

        # Validate content_max_length
        if not 100 <= self.content_max_length <= MAX_CONTENT_LENGTH:
            raise ValueError(
                f"content_max_length must be between 100 and {MAX_CONTENT_LENGTH}, "
                f"got {self.content_max_length}"
            )

        # Load from environment if not provided
        if not self.conn_string:
            self.conn_string = os.environ.get("PGVECTOR_URL")

        if not self.embed_api_base:
            self.embed_api_base = os.environ.get("EMBED_API_BASE")

        if not self.embed_api_key:
            self.embed_api_key = os.environ.get("EMBED_API_KEY")

    @classmethod
    def from_env(cls) -> "RAGConfig":
        """Create configuration from environment variables."""
        return cls(
            conn_string=os.environ.get("PGVECTOR_URL"),
            embed_api_base=os.environ.get("EMBED_API_BASE"),
            embed_api_key=os.environ.get("EMBED_API_KEY"),
            embed_model=os.environ.get("EMBED_MODEL_NAME", DEFAULT_EMBED_MODEL),
            chat_model=os.environ.get("CHAT_MODEL_NAME", DEFAULT_CHAT_MODEL),
        )

    def validate(self) -> None:
        """Validate that required configuration is present."""
        if not self.conn_string:
            raise ValueError("Database connection string is required")
        if not self.embed_api_base:
            raise ValueError("Embedding API base URL is required")
        if not self.embed_api_key:
            raise ValueError("API key is required")
