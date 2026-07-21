# Agent Chat UI

React SPA for the Agent HTTP API v1 — chat, collections, PDF indexing, citations.

## Prerequisites

- Node.js 20+
- Agent API running: `uvicorn agent.api.main:app --port 8080`

## Setup

```bash
cd frontend
npm install
cp .env.example .env
```

Use an empty `VITE_API_BASE_URL` to rely on the Vite dev proxy (`/api` → `localhost:8080`), or set `http://localhost:8080` explicitly.

## Development

```bash
npm run dev
```

Open http://localhost:5173

## Build

```bash
npm run build
```

## Features (v1)

- **Documents**: create collections, upload PDFs, manual refresh indexing status
- **Chunk browser**: completed documents expose **View chunks** ordered by
  descending source page
- **Chat**: SSE streaming with thought process (expanded by default)
- **Citations**: side-panel inspector via `GET /chunks/`
- **Scope**: collection selection per conversation (localStorage), `@doc_name` mentions
