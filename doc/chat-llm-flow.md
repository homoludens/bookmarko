# LLM Chat Flow in Flaskmarks

This app uses a Retrieval-Augmented Generation (RAG) flow:
1. Retrieve relevant bookmarks for the user.
2. Send retrieved context plus question to Groq LLM.
3. Return answer with source bookmarks.

## Request Flow

1. Frontend sends `POST /chat/send` with `query` and CSRF token.
   - `flaskmarks/templates/chat/index.html`
2. Backend validates input via `ChatForm` (`3..1000` chars).
   - `flaskmarks/forms/chat.py`
3. Route calls:
   - `rag_service.chat(query, user_id, chat_history)`
   - `flaskmarks/views/chat.py`

## RAG + LLM Flow

Inside `RAGService.chat`:

1. Check feature/config:
   - `RAG_ENABLED`
   - `GROQ_API_KEY`
2. Embed the user query with sentence-transformers.
3. Run pgvector similarity search on `marks.embedding`, scoped by `owner_id` (user isolation).
4. Build context from top matches:
   - title, URL, tags, description, content excerpt
5. Call Groq chat completions with:
   - system prompt
   - recent chat history
   - current question + retrieved context
6. Return:
   - `answer`
   - `sources`
   - `tokens_used`

Relevant code:
- `flaskmarks/core/rag/service.py`
- `flaskmarks/core/rag/embeddings.py`

## Embeddings and Storage

Bookmark model stores vectors in:
- `embedding` (`Vector(384)`)
- `embedding_updated`

Defined in:
- `flaskmarks/models/mark.py`

Database support is enabled by migration:
- `migrations/versions/a1b2c3d4e5f6_add_embedding_column_for_rag.py`

## How Embeddings Are Generated

Embeddings are primarily generated via CLI:
- `flask rag generate-embeddings`

Code:
- `flaskmarks/cli.py`

If no relevant embedded bookmarks exist, chat returns a fallback message.

## Session Chat History

Chat history is stored in session as alternating user/assistant messages.
History size is capped by `CHAT_MAX_HISTORY`.

Code:
- `flaskmarks/views/chat.py`

## Main Config Knobs

From `config.py`:
- `RAG_ENABLED`
- `GROQ_API_KEY`
- `GROQ_MODEL`
- `GROQ_TEMPERATURE`
- `GROQ_MAX_TOKENS`
- `RAG_TOP_K`
- `RAG_SIMILARITY_THRESHOLD`
- `CHAT_MAX_HISTORY`

## Note

`RAG_SIMILARITY_THRESHOLD` is defined in config but currently not applied in retrieval logic; retrieval uses top-K results.
