import type { ContentBlock } from './contentBlocks';
import { apiBlockToContentBlock } from './contentBlocks';

export const STREAM_EVENT = {
    CHAT: 'chat',
    REASONING: 'reasoning',
    NAME_SUGGESTION: 'name-suggestion',
    ERROR: 'error',
    BLOCK_OPEN: 'block-open',
    BLOCK_DELTA: 'block-delta',
    BLOCK_CLOSE: 'block-close',
} as const;

export type StreamEventName = (typeof STREAM_EVENT)[keyof typeof STREAM_EVENT];

export const MESSAGE_ROLE = {
    USER: 'user',
    ASSISTANT: 'assistant',
} as const;

export type MessageRole = (typeof MESSAGE_ROLE)[keyof typeof MESSAGE_ROLE];

export const USER_FEEDBACK = {
    NEUTRAL: 'neutral',
} as const;

export type UserFeedback = (typeof USER_FEEDBACK)[keyof typeof USER_FEEDBACK];

export interface ApiMessage {
    id: string;
    conversationId: string;
    role: MessageRole;
    content: string;
    contentBlocks?: Array<{
        id: string;
        type: string;
        order: number;
        status: string;
        text?: string | null;
        title?: string | null;
        loadingMessages?: string[];
        widgetCode?: string | null;
        errorMessage?: string | null;
    }>;
    mappingEvidence: Record<string, string> | null;
    createdAt: string;
}

export interface ChatMessage {
    id: string;
    content: string;
    role: MessageRole;
    reasoning?: string;
    feedback: UserFeedback;
    mappingEvidence?: Record<string, string> | null;
    contentBlocks: ContentBlock[];
}

function flattenTextBlocks(blocks: ContentBlock[]): string {
    return blocks
        .filter((b) => b.type === 'text')
        .sort((a, b) => a.order - b.order)
        .map((b) => b.text ?? '')
        .join('');
}

export function apiMessageToChatMessage(msg: ApiMessage): ChatMessage {
    const contentBlocks = (msg.contentBlocks ?? []).map(apiBlockToContentBlock);
    const content =
        contentBlocks.length > 0 ? flattenTextBlocks(contentBlocks) : msg.content;
    return {
        id: msg.id,
        content,
        role: msg.role,
        feedback: USER_FEEDBACK.NEUTRAL,
        mappingEvidence: msg.mappingEvidence,
        contentBlocks,
    };
}
