# Agent API Integration Guide

End-to-end flow for the Agent HTTP API v1.

## Prerequisites

- Python 3.12+ with project dependencies installed
- `.env` with OpenAI Azure, Milvus, and optional Tavily keys
- API running: `uvicorn agent.api.main:app --port 8080`

## Flow

1. **Create a collection** — `POST /api/v1/collections/`
2. **Upload a PDF reference** — `POST /api/v1/references/` (multipart)
3. **Poll reference status** — `GET /api/v1/references/{id}` until `status=completed`
4. **Create a conversation** — `POST /api/v1/conversations/`
5. **Chat with SSE** — `POST /api/v1/chats/chat` with `collection_ids` or `@doc_name` mentions
6. **Load evidence** — `GET /api/v1/conversations/{id}/messages` → read `mapping_evidence`
7. **Fetch chunk bodies** — `GET /api/v1/chunks/?chunk_ids=...&snippets=...`

## Endpoint reference

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/conversations/` | Create conversation |
| GET | `/api/v1/conversations/{id}/messages` | Message history |
| POST | `/api/v1/chats/chat` | Agentic SSE chat |
| POST | `/api/v1/collections/` | Create collection |
| POST | `/api/v1/references/` | Upload PDF |
| GET | `/api/v1/references/{id}` | Index status |
| GET | `/api/v1/chunks/` | Batch chunk lookup + highlights |

See `/docs` for request/response examples.
