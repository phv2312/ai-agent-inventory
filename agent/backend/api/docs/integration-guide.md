# Agent API Integration Guide

End-to-end flow for the Agent HTTP API v1.

## Prerequisites

- Python 3.12+ with project dependencies installed
- `.env` with OpenAI Azure and Milvus keys
- API running: `uvicorn agent.backend.api.main:app --port 8080`

## Flow

1. **Create a collection** — `POST /api/v1/collections/`
2. **Upload a PDF reference** — `POST /api/v1/references/` (multipart)
3. **Poll reference status** — `GET /api/v1/references/{id}` until `status=completed`
4. **Create a conversation** — `POST /api/v1/conversations/`
5. **Chat with SSE** — `POST /api/v1/chats/chat` with `collection_ids` or `@doc_name` mentions
6. **Review a global plan when interrupted** — approve or revise through `POST /api/v1/chats/{id}/interruptions/resume`; cancel through `POST /api/v1/chats/{id}/interruptions`
7. **Load evidence** — `GET /api/v1/conversations/{id}/messages` → read `mapping_evidence`
8. **Fetch chunk bodies** — `GET /api/v1/chunks/?chunk_ids=...&snippets=...`

## Endpoint reference

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/conversations/` | Create conversation |
| GET | `/api/v1/conversations/{id}/messages` | Message history |
| POST | `/api/v1/chats/chat` | Agentic SSE chat |
| GET | `/api/v1/chats/{id}/interruptions` | Restore pending plan review |
| POST | `/api/v1/chats/{id}/interruptions/resume` | Approve or revise and resume the pending plan |
| POST | `/api/v1/chats/{id}/interruptions` | Cancel a pending plan; also retained for compatible approve/revise clients |
| POST | `/api/v1/collections/` | Create collection |
| POST | `/api/v1/references/` | Upload PDF |
| GET | `/api/v1/references/{id}` | Index status |
| GET | `/api/v1/chunks/` | Batch chunk lookup + highlights |

See `/docs` for request/response examples.

### Global-agent interruption flow

Broad or multi-step requests may be handed from the root orchestrator to the
global agent. The stream then emits `event: interruption` with a structured
plan, state version, and interruption IDs. The backend persists one pending run
per conversation, so clients can restore it with the GET endpoint after a
refresh or process restart.

Submit the exact version and interruption IDs with one decision:

Clients can set the chat form field `global_query=true` to start the global
agent directly. The bundled frontend sets this field when a message begins with
`/global` and removes the prefix from the submitted query.

- `approve` resumes the run and streams the final answer.
- `revise` requires non-empty `feedback` and streams a replacement plan.
- `cancel` removes the pending run without creating an assistant message.

New chat requests for that conversation return HTTP 409 until the pending run
is completed or cancelled.
