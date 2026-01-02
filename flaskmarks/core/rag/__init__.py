"""
RAG (Retrieval-Augmented Generation) module for Flaskmarks.

Provides chat-with-bookmarks functionality using:
- sentence-transformers for embeddings
- pgvector for vector storage
- llama-index for RAG orchestration
- Groq for LLM generation
"""
from __future__ import annotations

from .service import RAGService, get_rag_service
from .embeddings import EmbeddingService

__all__ = ['RAGService', 'EmbeddingService', 'get_rag_service']
