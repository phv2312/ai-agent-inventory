import { BASE_URL } from './env';
import type {
    BlockClosePayload,
    BlockDeltaPayload,
    BlockOpenPayload,
} from '../../types/contentBlocks';
import { STREAM_EVENT } from '../../types/messages';
import { toCamelCaseObject } from '../../utils/case';

export interface ChatStreamPayload {
    conversationId: string;
    message: string;
    collectionIds: string[];
    topK?: number;
    numHistoryInteractions?: number;
    systemPrompt?: string;
    globalQuery?: boolean;
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

export interface PlanSection {
    title: string;
    purpose: string;
}

export interface AgentPlan {
    query: string;
    sections: PlanSection[];
}

export interface AgentInterruption {
    id: string;
    agent: string;
    toolName: string;
    plan: AgentPlan | null;
    arguments: Record<string, unknown>;
}

export interface InterruptionData {
    conversationId: string;
    version: number;
    interruptions: AgentInterruption[];
}

export type InterruptionDecision = 'approve' | 'revise' | 'cancel';

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

export interface InterruptionStreamEvent {
    event: 'interruption';
    data: InterruptionData;
}

export interface InterruptionResolvedStreamEvent {
    event: 'interruption-resolved';
    data: {
        conversationId: string;
        version: number;
        status: 'cancelled';
    };
}

export type SSEEvent =
    | ChatStreamEvent
    | ReasoningStreamEvent
    | BlockOpenStreamEvent
    | BlockDeltaStreamEvent
    | BlockCloseStreamEvent
    | NameSuggestionStreamEvent
    | ErrorStreamEvent
    | InterruptionStreamEvent
    | InterruptionResolvedStreamEvent;

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
    formData.append('global_query', String(payload.globalQuery ?? false));
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

    yield* readSseResponse(response);
}

export async function getPendingInterruption(
    conversationId: string,
): Promise<InterruptionData | null> {
    const response = await fetch(
        `${BASE_URL}/api/v1/chats/${conversationId}/interruptions`,
        { headers: { Accept: 'application/json' } },
    );
    if (response.status === 404) return null;
    if (!response.ok) {
        throw new Error(await response.text());
    }
    return toCamelCaseObject(await response.json()) as InterruptionData;
}

export async function* respondToInterruption(
    interruption: InterruptionData,
    decision: InterruptionDecision,
    feedback: string,
    signal?: AbortSignal,
): AsyncGenerator<SSEEvent, void, unknown> {
    const interruptionPath =
        decision === 'cancel'
            ? `${interruption.conversationId}/interruptions`
            : `${interruption.conversationId}/interruptions/resume`;
    const response = await fetch(
        `${BASE_URL}/api/v1/chats/${interruptionPath}`,
        {
            method: 'POST',
            headers: {
                Accept: 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                version: interruption.version,
                interruption_ids: interruption.interruptions.map((item) => item.id),
                decision,
                feedback: decision === 'revise' ? feedback : null,
            }),
            signal,
        },
    );
    yield* readSseResponse(response);
}

async function* readSseResponse(
    response: Response,
): AsyncGenerator<SSEEvent, void, unknown> {
    if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || `HTTP error! status: ${response.status}`);
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
            if (
                currentEvent === STREAM_EVENT.INTERRUPTION
                || currentEvent === STREAM_EVENT.INTERRUPTION_RESOLVED
            ) {
                return {
                    event: currentEvent,
                    data: toCamelCaseObject(data),
                } as SSEEvent;
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
