"""RAG service for chat-with-bookmarks functionality."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional

from flask import current_app
from sqlalchemy import text

if TYPE_CHECKING:
    from flaskmarks.models import Mark


@dataclass
class ChatSource:
    """Represents a source bookmark used in a response."""
    mark_id: int
    title: str
    url: str
    relevance_score: float


@dataclass
class ChatResponse:
    """Response from the RAG chat system."""
    answer: str
    sources: List[ChatSource]
    tokens_used: int
    error: Optional[str] = None


class RAGService:
    """
    Service for RAG-based chat with bookmarks.

    Uses sentence-transformers for embeddings, pgvector for retrieval,
    and Groq for generation.
    """

    def __init__(self):
        self._llm = None
        self._embedding_service = None

    @property
    def embedding_service(self):
        """Lazy load embedding service."""
        if self._embedding_service is None:
            from .embeddings import EmbeddingService
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    @property
    def llm(self):
        """Lazy load Groq LLM client."""
        if self._llm is None:
            from groq import Groq
            api_key = current_app.config.get('GROQ_API_KEY')
            if not api_key:
                raise ValueError("GROQ_API_KEY not configured")
            self._llm = Groq(api_key=api_key)
        return self._llm

    def retrieve_relevant_marks(
        self,
        query: str,
        user_id: int,
        top_k: Optional[int] = None
    ) -> List[tuple['Mark', float]]:
        """
        Retrieve the most relevant bookmarks for a query.

        Args:
            query: User's question
            user_id: ID of the user (for isolation)
            top_k: Number of results to return

        Returns:
            List of (Mark, similarity_score) tuples
        """
        from flaskmarks.core.extensions import db
        from flaskmarks.models import Mark

        if top_k is None:
            top_k = current_app.config.get('RAG_TOP_K', 5)

        # Generate query embedding
        query_embedding = self.embedding_service.generate_embedding(query)

        # Query pgvector for similar marks owned by the user
        # Using cosine distance (1 - cosine_similarity)
        sql = text("""
            SELECT id, 1 - (embedding <=> :query_embedding::vector) as similarity
            FROM marks
            WHERE owner_id = :user_id
              AND embedding IS NOT NULL
            ORDER BY embedding <=> :query_embedding::vector
            LIMIT :top_k
        """)

        result = db.session.execute(sql, {
            'query_embedding': str(query_embedding),
            'user_id': user_id,
            'top_k': top_k
        })

        mark_scores = [(row.id, row.similarity) for row in result]

        # Fetch full mark objects
        marks_with_scores = []
        for mark_id, score in mark_scores:
            mark = Mark.query.get(mark_id)
            if mark:
                marks_with_scores.append((mark, score))

        return marks_with_scores

    def build_context(
        self,
        marks_with_scores: List[tuple['Mark', float]]
    ) -> str:
        """
        Build context string from retrieved bookmarks.

        Args:
            marks_with_scores: List of (Mark, score) tuples

        Returns:
            Formatted context string for LLM
        """
        from .utils import strip_html_tags, truncate_text

        context_parts = []

        for i, (mark, score) in enumerate(marks_with_scores, 1):
            tags = ', '.join(
                tag.title for tag in mark.tags
            ) if mark.tags else 'none'
            content = truncate_text(
                strip_html_tags(mark.full_html) if mark.full_html else '',
                500
            )

            context_parts.append(f"""
[Bookmark {i}]
Title: {mark.title}
URL: {mark.url}
Tags: {tags}
Description: {mark.description or 'No description'}
Content excerpt: {content}
---""")

        return '\n'.join(context_parts)

    def generate_response(
        self,
        query: str,
        context: str,
        chat_history: Optional[List[dict]] = None
    ) -> tuple[str, int]:
        """
        Generate a response using Groq LLM.

        Args:
            query: User's question
            context: Retrieved bookmark context
            chat_history: Optional list of previous messages

        Returns:
            Tuple of (response_text, tokens_used)
        """
        model = current_app.config.get('GROQ_MODEL', 'llama-3.1-70b-versatile')
        temperature = current_app.config.get('GROQ_TEMPERATURE', 0.7)
        max_tokens = current_app.config.get('GROQ_MAX_TOKENS', 1024)

        system_prompt = """You are a helpful assistant that answers questions based on the user's bookmarks.
Use the provided bookmark context to answer questions accurately.
Always cite which bookmarks you used in your answer by referencing their titles.
If the bookmarks don't contain relevant information, say so clearly.
Be concise but thorough in your responses."""

        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # Add chat history if provided
        if chat_history:
            max_history = current_app.config.get('CHAT_MAX_HISTORY', 10)
            messages.extend(chat_history[-max_history:])

        # Add current query with context
        user_message = f"""Based on these bookmarks from my collection:

{context}

Question: {query}

Please answer based on the information in these bookmarks. Cite which bookmarks you used."""

        messages.append({"role": "user", "content": user_message})

        response = self.llm.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        answer = response.choices[0].message.content
        tokens_used = response.usage.total_tokens

        return answer, tokens_used

    def chat(
        self,
        query: str,
        user_id: int,
        chat_history: Optional[List[dict]] = None
    ) -> ChatResponse:
        """
        Main entry point for chat functionality.

        Args:
            query: User's question
            user_id: ID of the user
            chat_history: Optional previous messages

        Returns:
            ChatResponse with answer, sources, and metadata
        """
        try:
            # Check if RAG is enabled
            if not current_app.config.get('RAG_ENABLED', True):
                return ChatResponse(
                    answer='',
                    sources=[],
                    tokens_used=0,
                    error='Chat feature is currently disabled'
                )

            # Check for API key
            if not current_app.config.get('GROQ_API_KEY'):
                return ChatResponse(
                    answer='',
                    sources=[],
                    tokens_used=0,
                    error='Chat is not configured. Please set GROQ_API_KEY.'
                )

            # Retrieve relevant bookmarks
            marks_with_scores = self.retrieve_relevant_marks(query, user_id)

            if not marks_with_scores:
                return ChatResponse(
                    answer="I couldn't find any relevant bookmarks to answer "
                           "your question. Try adding more bookmarks or "
                           "rephrasing your question.",
                    sources=[],
                    tokens_used=0
                )

            # Build context
            context = self.build_context(marks_with_scores)

            # Generate response
            answer, tokens_used = self.generate_response(
                query, context, chat_history
            )

            # Build sources list
            sources = [
                ChatSource(
                    mark_id=mark.id,
                    title=mark.title,
                    url=mark.url,
                    relevance_score=score
                )
                for mark, score in marks_with_scores
            ]

            return ChatResponse(
                answer=answer,
                sources=sources,
                tokens_used=tokens_used
            )

        except Exception as e:
            current_app.logger.error(f"RAG chat error: {e}")
            return ChatResponse(
                answer='',
                sources=[],
                tokens_used=0,
                error=f"An error occurred: {str(e)}"
            )


# Singleton instance
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Get or create the RAG service singleton."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
