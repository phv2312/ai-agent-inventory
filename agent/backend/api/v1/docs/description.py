"""OpenAPI operation descriptions for v1 endpoints."""


class Descriptions:
    CREATE_CONVERSATION = "Create a new conversation."
    LIST_CONVERSATIONS = "List conversations ordered by most recently updated."
    GET_CONVERSATION = "Get a conversation by id."
    UPDATE_CONVERSATION = "Update conversation title."
    DELETE_CONVERSATION = "Delete a conversation and its messages."
    LIST_MESSAGES = (
        "List messages for a conversation including mapping_evidence on assistant rows."
    )

    CHAT_SSE = (
        "Agentic chat over Server-Sent Events. Stream emits lightweight "
        "`chat`, `reasoning`, and optional tail events only. "
        "Citation mapping is persisted on the assistant message after the stream completes."
    )

    CREATE_COLLECTION = "Create a knowledge collection."
    LIST_COLLECTIONS = "List collections with pagination."
    GET_COLLECTION = "Get collection details."
    UPDATE_COLLECTION = "Update collection name or description."
    DELETE_COLLECTION = "Delete a collection and its references."

    UPLOAD_REFERENCE = "Upload a PDF reference and start async indexing."
    GET_REFERENCE = "Get reference metadata and indexing status."
    LIST_REFERENCE_CHUNKS = "List indexed chunks for a completed reference."

    BATCH_CHUNKS = (
        "Batch fetch chunk bodies by id. Optional message_id loads stored "
        "citation snippets for highlight in the evidence panel."
    )
