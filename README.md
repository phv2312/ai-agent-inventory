# AI Agent Inventory

An AI-powered agent inventory, include various components help build AI Agentic application effectively

[![pre-commit](https://github.com/phv2312/ai-agent-inventory/actions/workflows/precommit.yaml/badge.svg)](https://github.com/phv2312/ai-agent-inventory/actions/workflows/precommit.yaml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
![Static Badge](https://img.shields.io/badge/type%20checked-mypy-039dfc)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)

## Installation

```
pip install uv
uv sync
source ./venv/bin/activate
```

## Components

| Component | Description | Implementations |
|:----------|:------------|:----------------|
| chats | Contains implementations of chat model interfaces and utilities for interacting with LLM chat models like ChatGPT | - OpenAI chat<br>- Anthropic chat |
| embeddings | Houses embedding model implementations for transforming text into vector representations | - OpenAI embeddings |
| extractors | Contains utilities for extracting information and data from various sources | - PDF Extractor |
| models | Contains Pydantic data models and schemas that define the structure of data used throughout the system | - Message, Provider stream events |
| rag | Agentic RAG chat strategies with tool-driven retrieval | - AgenticChatStrategy (ReAct + Responses API) |
| structs | Application-level stream event wrappers for UI consumers | - StreamChatData, StreamReasoningData |
| programs | Houses LLM programs that generate structured data using Pydantic models | - Base program framework |
| prompts | Contains templates and configurations for LLM chat prompts | - Agentic prompts |
| searches | Implements search functionality, likely including vector and semantic search capabilities | - Tavily search<br>- DuckDuckGo search |
| storages | Contains storage implementations, possibly including vector database integrations | - Local storage<br>- Milvus |
| text_splitters | Implements text chunking and splitting utilities for processing large text documents | - Langchain text splitter |
