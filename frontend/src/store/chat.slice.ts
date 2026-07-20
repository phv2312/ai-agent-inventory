import { createAsyncThunk, createSlice, type PayloadAction } from '@reduxjs/toolkit';
import { getMessagesByConversation } from '../services/api/conversation';
import type {
    BlockClosePayload,
    BlockDeltaPayload,
    BlockOpenPayload,
    ContentBlock,
} from '../types/contentBlocks';
import { CONTENT_BLOCK_TYPE } from '../types/contentBlocks';
import {
    apiMessageToChatMessage,
    MESSAGE_ROLE,
    type ChatMessage,
} from '../types/messages';
import {
    loadMessageReasoning,
    saveMessageReasoning,
} from '../utils/reasoningStorage';

export const fetchMessagesByConversation = createAsyncThunk(
    'chat/fetchMessagesByConversation',
    async (conversationId: string, { rejectWithValue }) => {
        try {
            const messages = await getMessagesByConversation(conversationId);
            return messages.map((msg) => apiMessageToChatMessage(msg));
        } catch (error) {
            return rejectWithValue(
                error instanceof Error ? error.message : 'Failed to fetch messages',
            );
        }
    },
);

interface ChatState {
    messages: ChatMessage[];
    streamingMessageIdx: number | null;
    isStreaming: boolean;
    isLoadingMessages: boolean;
    error: string | null;
    reasoningExpanded: boolean;
    streamingUsesBlocks: boolean;
}

const initialState: ChatState = {
    messages: [],
    streamingMessageIdx: null,
    isStreaming: false,
    isLoadingMessages: false,
    error: null,
    reasoningExpanded: true,
    streamingUsesBlocks: false,
};

function getStreamingMessage(state: ChatState): ChatMessage | null {
    if (state.streamingMessageIdx === null) return null;
    return state.messages[state.streamingMessageIdx] ?? null;
}

export const chatSlice = createSlice({
    name: 'chat',
    initialState,
    reducers: {
        clearMessages(state) {
            state.messages = [];
            state.streamingMessageIdx = null;
            state.error = null;
            state.isLoadingMessages = false;
            state.streamingUsesBlocks = false;
        },
        addUserMessage(state, action: PayloadAction<ChatMessage>) {
            state.messages.push(action.payload);
        },
        addAssistantMessage(state, action: PayloadAction<ChatMessage>) {
            state.messages.push({
                ...action.payload,
                reasoning: '',
                contentBlocks: action.payload.contentBlocks ?? [],
            });
            state.streamingMessageIdx = state.messages.length - 1;
            state.reasoningExpanded = true;
            state.streamingUsesBlocks = false;
        },
        appendAssistantContent(state, action: PayloadAction<string>) {
            if (state.streamingMessageIdx === null || state.streamingUsesBlocks) {
                return;
            }
            state.messages[state.streamingMessageIdx].content += action.payload;
        },
        openContentBlock(state, action: PayloadAction<BlockOpenPayload>) {
            const msg = getStreamingMessage(state);
            if (!msg) return;
            state.streamingUsesBlocks = true;
            const payload = action.payload;
            const block: ContentBlock = {
                type: payload.type,
                order: payload.order,
                status: payload.status,
                text: payload.type === CONTENT_BLOCK_TYPE.TEXT ? '' : null,
                textChunks: payload.type === CONTENT_BLOCK_TYPE.TEXT ? [] : undefined,
                widgetCode:
                    payload.type === CONTENT_BLOCK_TYPE.VISUAL_WIDGET ? '' : null,
                widgetCodeChunks:
                    payload.type === CONTENT_BLOCK_TYPE.VISUAL_WIDGET ? [] : undefined,
            };
            msg.contentBlocks = [...msg.contentBlocks, block].sort(
                (a, b) => a.order - b.order,
            );
        },
        appendContentBlockDelta(state, action: PayloadAction<BlockDeltaPayload>) {
            const msg = getStreamingMessage(state);
            if (!msg) return;
            const { order, content } = action.payload;
            const block = msg.contentBlocks.find((item) => item.order === order);
            if (!block) return;
            if (block.type === CONTENT_BLOCK_TYPE.TEXT) {
                block.textChunks ??= [];
                block.textChunks.push(content ?? '');
                return;
            }
            block.widgetCodeChunks ??= [];
            block.widgetCodeChunks.push(content ?? '');
        },
        closeContentBlock(state, action: PayloadAction<BlockClosePayload>) {
            const msg = getStreamingMessage(state);
            if (!msg) return;
            const {
                order,
                status,
                error_message: errorMessage,
            } = action.payload;
            msg.contentBlocks = msg.contentBlocks.map((block) =>
                block.order === order
                    ? {
                          ...block,
                          status,
                          errorMessage: errorMessage ?? null,
                      }
                    : block,
            );
        },
        appendAssistantReasoningContent(state, action: PayloadAction<string>) {
            if (state.streamingMessageIdx === null) return;
            const idx = state.streamingMessageIdx;
            const msg = state.messages[idx];
            msg.reasoning = (msg.reasoning ?? '') + action.payload;
            saveMessageReasoning(msg.id, msg.reasoning);
        },
        setReasoningExpanded(state, action: PayloadAction<boolean>) {
            state.reasoningExpanded = action.payload;
        },
        startStreaming(state) {
            state.isStreaming = true;
            state.error = null;
            state.reasoningExpanded = true;
            state.streamingUsesBlocks = false;
        },
        stopStreaming(state) {
            state.streamingMessageIdx = null;
            state.isStreaming = false;
            state.streamingUsesBlocks = false;
        },
        setStreamingError(state, action: PayloadAction<string>) {
            state.error = action.payload;
            state.isStreaming = false;
            state.streamingMessageIdx = null;
            state.streamingUsesBlocks = false;
        },
        clearError(state) {
            state.error = null;
        },
    },
    extraReducers: (builder) => {
        builder
            .addCase(fetchMessagesByConversation.pending, (state) => {
                if (!state.isStreaming) {
                    state.isLoadingMessages = true;
                }
            })
            .addCase(fetchMessagesByConversation.rejected, (state) => {
                state.isLoadingMessages = false;
            })
            .addCase(fetchMessagesByConversation.fulfilled, (state, action) => {
            if (state.isStreaming) {
                state.isLoadingMessages = false;
                return;
            }

            const prevMessages = state.messages;
            const serverIds = new Set(action.payload.map((msg) => msg.id));
            const reasoningById = new Map<string, string>();
            const orphanedReasoning: string[] = [];

            for (const msg of prevMessages) {
                if (!msg.reasoning?.trim()) continue;
                reasoningById.set(msg.id, msg.reasoning);
                if (!serverIds.has(msg.id)) {
                    orphanedReasoning.push(msg.reasoning);
                }
            }

            const merged = action.payload.map((msg) => {
                const preserved = reasoningById.get(msg.id);
                if (preserved) {
                    return { ...msg, reasoning: preserved };
                }
                const cached = loadMessageReasoning(msg.id);
                if (cached?.trim()) {
                    return { ...msg, reasoning: cached };
                }
                return msg;
            });

            if (orphanedReasoning.length > 0) {
                let orphanIdx = orphanedReasoning.length - 1;
                for (let i = merged.length - 1; i >= 0 && orphanIdx >= 0; i--) {
                    if (
                        merged[i].role === MESSAGE_ROLE.ASSISTANT
                        && !merged[i].reasoning?.trim()
                    ) {
                        const reasoning = orphanedReasoning[orphanIdx];
                        merged[i] = { ...merged[i], reasoning };
                        saveMessageReasoning(merged[i].id, reasoning);
                        orphanIdx--;
                    }
                }
            }

            state.messages = merged;
            state.streamingMessageIdx = null;
            state.isStreaming = false;
            state.isLoadingMessages = false;
            state.streamingUsesBlocks = false;
        });
    },
});

export const {
    clearMessages,
    addUserMessage,
    addAssistantMessage,
    appendAssistantContent,
    openContentBlock,
    appendContentBlockDelta,
    closeContentBlock,
    appendAssistantReasoningContent,
    setReasoningExpanded,
    startStreaming,
    stopStreaming,
    setStreamingError,
    clearError,
} = chatSlice.actions;

export default chatSlice.reducer;
