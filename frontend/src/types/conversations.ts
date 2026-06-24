export type ConversationId = string;
export type CollectionId = string;

export interface Conversation {
    id: ConversationId;
    title: string;
    createdAt: string;
    updatedAt: string;
}

export interface ConversationCreateRequest {
    title?: string;
}

export interface ConversationUpdateRequest {
    id: ConversationId;
    title?: string;
}
