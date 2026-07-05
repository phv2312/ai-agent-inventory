# AI Agent Inventory

An AI-powered agent inventory — modular components for building production-grade Agentic RAG applications.

[![pre-commit](https://github.com/phv2312/ai-agent-inventory/actions/workflows/precommit.yaml/badge.svg)](https://github.com/phv2312/ai-agent-inventory/actions/workflows/precommit.yaml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
![Static Badge](https://img.shields.io/badge/type%20checked-mypy-039dfc)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)

---

## Demo

### Knowledge Base + Diagram

![Milvus architecture query](assets/screenshots/milvus-query.gif)

Ask questions over indexed documents — the agent retrieves relevant chunks, cites sources inline, and can render architecture diagrams directly in the chat panel.

### Document RAG + Inline Charts

![HPG financial query with chart](assets/screenshots/hpg-query.gif)

Query structured data from uploaded PDFs (e.g. quarterly earnings reports). When a visual helps, the agent generates an interactive chart widget inline alongside cited answers.

---

## Getting started

### Prerequisites

- **Python 3.12+**
- **Node.js 20+** (for the React chat UI)
- **[uv](https://docs.astral.sh/uv/)** — Python package manager

### 1. Backend

```bash
# Install uv (skip if already installed)
pip install uv

# Create .venv and install dependencies (includes dev tools)
uv sync

# Activate the virtual environment
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 2. Environment variables

Copy the template and fill in your keys:

```bash
cp .env.example .env
```

Settings are read from the **process environment**, so load the file before
starting the API:

```bash
set -a && source .env && set +a   # macOS / Linux
```

Optional API settings (prefix `AGENT_API_`):

| Variable | Default | Description |
|:---------|:--------|:------------|
| `AGENT_API_DATA_DIR` | `.agent-api-data` | SQLite DB, uploaded PDFs, and index images |
| `AGENT_API_DATABASE_URL` | *(SQLite in data dir)* | Override with a custom async SQLAlchemy URL |

### 3. Run the API

```bash
uvicorn agent.api.main:app --reload --port 8080
```

- API: http://localhost:8080
- Interactive docs: http://localhost:8080/docs

See [agent/api/docs/integration-guide.md](agent/api/docs/integration-guide.md) for the full HTTP workflow (collections → PDF upload → chat).

### 4. Frontend (chat UI)

```bash
cd frontend
npm install
```

Create `frontend/.env`. Leave `VITE_API_BASE_URL` empty to use the Vite dev
proxy (`/api` → `localhost:8080`), or set it explicitly:

```dotenv
VITE_API_BASE_URL=
```

```bash
npm run dev
```

Open http://localhost:5173

### 5. Development checks (optional)

```bash
# Install git hooks (ruff, mypy)
pre-commit install

# Backend tests
pytest tests/ -q

# Frontend widget-runtime tests + production build
cd frontend && npm run test:widget-runtime && npm run build
```

### 6. Evaluation benchmark

The `evaluation/` package contains the 100-query agent benchmark, Phoenix trace
capture, metric evaluation, and visualization artifact extraction.

See [evaluation/README.md](evaluation/README.md) for commands. Latest run:
run-2 — 50 queries, 94% tool-call accuracy, 31/31 visualizations runnable.

---

## Components

| Component | Description | Implementations |
|:----------|:------------|:----------------|
| chats | Chat model interfaces for interacting with LLM providers | - OpenAI chat<br>- Anthropic chat |
| embeddings | Embedding model implementations for vector representations | - OpenAI embeddings |
| extractors | Utilities for extracting information from various sources | - PDF Extractor |
| models | Pydantic data models and schemas used throughout the system | - Message, Provider stream events |
| rag | Agentic RAG chat strategies with tool-driven retrieval | - AgenticChatStrategy (`ReActAgent` + Responses API) |
| programs | LLM programs that generate structured data using Pydantic models | - Base program framework |
| prompts | Templates and configurations for LLM chat prompts | - Agentic prompts |
| storages | Storage implementations including vector database integrations | - Local storage<br>- Milvus |
| textsplitters | Text chunking and splitting utilities for large documents | - Langchain text splitter |

---

## Roadmap

| Status | Feature |
|:------:|:--------|
| ✅ | Agentic-RAG implementation and React chat UI |
| ✅ | Built-in tools: internal search, web search, reflection |
| ✅ | Inline visual generation integrated into the chat demo |
| 🔲 | Agent skills — sandbox vs. local machine execution (decision pending) |
| 🔲 | Agent memory — define supported memory categories |
| 🔲 | Enhanced extractor — split documents into typed elements (table, section, figure) |
| 🔲 | Hybrid search support |
| 🔲 | Multimodal retrieval |
