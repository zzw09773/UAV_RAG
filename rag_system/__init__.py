"""
RAG System with Agentic Capabilities

A clean, modular RAG system with build and query separation:

Build Module (rag_system.build):
- Document preprocessing and chunking
- Vector database indexing
- Export and utilities

Query Module (rag_system.query):
- Agentic RAG with self-evaluation
- Collection routing
- Interactive and programmatic interfaces

Usage:
    # Building indexes
    from rag_system.build import preprocess_main, indexer_main

    # Querying with Agentic RAG
    from rag_system.query import RagApplication
"""

from .common import log, set_quiet_mode, LocalApiEmbeddings

__version__ = "2.0.0"
__author__ = "RAG System Team"
__all__ = ["log", "set_quiet_mode", "LocalApiEmbeddings"]