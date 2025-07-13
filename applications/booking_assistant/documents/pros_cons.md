# Pros & Cons

## Pros

- The codebase can be applied to other applications as well. Each component/service is decoupled from the others, making it easier to reuse.

- Supports streaming and SSE events (StreamData), which can be easily integrated with backend or frontend services.

- Asynchronous coding provides better concurrency performance.

- The chat workflow supports advanced techniques such as LangGraph, RAG, and LLM structured parsers.

- Pre-commit hooks with *mypy* and *ruff* help maintain and ensure the correctness of the repository.

## Cons

- Indexing, if possible, should be implemented with a message queue (such as RabbitMQ) to improve efficiency when handling uploads of many documents simultaneously.

- Unit testing and integration with CI are needed.

- Use of real samples and databases (such as PostgreSQL) instead of dummy ticket information.

- Lack of monitoring and profiling.

- Use a more powerful extractors which use deep learning such as docling, Azure Document Intelligence, ...
