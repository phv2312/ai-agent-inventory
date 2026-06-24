import { BASE_URL } from './env';
import type {
    BlockClosePayload,
    BlockDeltaPayload,
    BlockOpenPayload,
} from '../../types/contentBlocks';
import { STREAM_EVENT } from '../../types/messages';

export interface ChatStreamPayload {
    conversationId: string;
    message: string;
    collectionIds: string[];
    topK?: number;
    numHistoryInteractions?: number;
    systemPrompt?: string;
}

export interface ChatData {
    content: string;
    role: 'assistant';
    idx?: number;
}

export interface NameSuggestionData {
    name: string;
}

export interface ErrorStreamData {
    code: string;
    message: string;
}

export interface ChatStreamEvent {
    event: 'chat';
    data: ChatData[];
}

export interface ReasoningStreamEvent {
    event: 'reasoning';
    data: ChatData[];
}

export interface BlockOpenStreamEvent {
    event: 'block-open';
    data: BlockOpenPayload;
}

export interface BlockDeltaStreamEvent {
    event: 'block-delta';
    data: BlockDeltaPayload;
}

export interface BlockCloseStreamEvent {
    event: 'block-close';
    data: BlockClosePayload;
}

export interface NameSuggestionStreamEvent {
    event: 'name-suggestion';
    data: NameSuggestionData;
}

export interface ErrorStreamEvent {
    event: 'error';
    data: ErrorStreamData;
}

export type SSEEvent =
    | ChatStreamEvent
    | ReasoningStreamEvent
    | BlockOpenStreamEvent
    | BlockDeltaStreamEvent
    | BlockCloseStreamEvent
    | NameSuggestionStreamEvent
    | ErrorStreamEvent;

const BLOCK_EVENTS = new Set<string>([
    STREAM_EVENT.BLOCK_OPEN,
    STREAM_EVENT.BLOCK_DELTA,
    STREAM_EVENT.BLOCK_CLOSE,
]);

export async function* streamChatResponse(
    payload: ChatStreamPayload,
    signal?: AbortSignal,
): AsyncGenerator<SSEEvent, void, unknown> {
    const formData = new FormData();
    formData.append('conversation_id', payload.conversationId);
    formData.append('message', payload.message);
    formData.append('top_k', String(payload.topK ?? 10));
    formData.append('num_history_interactions', String(payload.numHistoryInteractions ?? 5));
    formData.append('web_search_enabled', 'false');
    if (payload.systemPrompt) {
        formData.append('system_prompt', payload.systemPrompt);
    }
    for (const id of payload.collectionIds) {
        formData.append('collection_ids', id);
    }

    const response = await fetch(`${BASE_URL}/api/v1/chats/chat`, {
        method: 'POST',
        headers: {
            Accept: 'text/event-stream',
            'Cache-Control': 'no-cache',
        },
        body: formData,
        signal,
    });

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    if (!reader) {
        throw new Error('No response body');
    }

    let currentEvent = 'unknown';
    let lineBuffer = '';

    const parseDataLine = (dataStr: string): SSEEvent | undefined => {
        try {
            const data = JSON.parse(dataStr);
            if (
                currentEvent === STREAM_EVENT.CHAT
                || currentEvent === STREAM_EVENT.REASONING
            ) {
                return { event: currentEvent, data } as SSEEvent;
            }
            if (BLOCK_EVENTS.has(currentEvent)) {
                return { event: currentEvent, data } as SSEEvent;
            }
            if (
                currentEvent === STREAM_EVENT.NAME_SUGGESTION
                || currentEvent === STREAM_EVENT.ERROR
            ) {
                return { event: currentEvent, data } as SSEEvent;
            }
        } catch (e) {
            console.warn('Failed to parse SSE data:', dataStr.slice(0, 200));
            console.error(e);
        }
        return undefined;
    };

    const processSseLine = (rawLine: string): SSEEvent | undefined => {
        const line = rawLine.endsWith('\r') ? rawLine.slice(0, -1) : rawLine;
        if (line.trim() === '') return undefined;
        if (line.startsWith('event: ')) {
            currentEvent = line.substring(7).trim();
            return undefined;
        }
        if (!line.startsWith('data: ')) return undefined;
        return parseDataLine(line.substring(6).trim());
    };

    try {
        while (true) {
            const { done, value } = await reader.read();
            lineBuffer += decoder.decode(value ?? new Uint8Array(0), { stream: !done });

            let newlineIdx: number;
            while ((newlineIdx = lineBuffer.indexOf('\n')) !== -1) {
                const completeLine = lineBuffer.slice(0, newlineIdx);
                lineBuffer = lineBuffer.slice(newlineIdx + 1);
                const ev = processSseLine(completeLine);
                if (ev) yield ev;
            }

            if (done) {
                if (lineBuffer.length > 0) {
                    const ev = processSseLine(lineBuffer);
                    if (ev) yield ev;
                }
                break;
            }
        }
    } finally {
        reader.releaseLock();
    }
}
