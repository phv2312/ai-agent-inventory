import { useCallback, useRef } from 'react';
import { useAppDispatch, useAppSelector } from './redux';
import { MESSAGE_ROLE, STREAM_EVENT, USER_FEEDBACK } from '../types/messages';
import type {
    BlockClosePayload,
    BlockDeltaPayload,
    BlockOpenPayload,
} from '../types/contentBlocks';
import {
    addAssistantMessage,
    addUserMessage,
    appendAssistantContent,
    appendAssistantReasoningContent,
    appendContentBlockDelta,
    closeContentBlock,
    fetchMessagesByConversation,
    openContentBlock,
    startStreaming,
    stopStreaming,
    setStreamingError,
    setPendingInterruption,
    clearPendingInterruption,
    startResolvingInterruption,
    finishResolvingInterruption,
    setInterruptionError,
} from '../store/chat.slice';
import { patchConversationTitle } from '../store/conversation.slice';
import { useConversationSelections } from './useConversationSelections';
import {
    respondToInterruption,
    streamChatResponse,
    type InterruptionDecision,
    type SSEEvent,
} from '../services/api/chats';
import { parseChatCommand } from '../utils/chatCommands';
import { v4 as uuidv4 } from 'uuid';

interface UseChatStream {
    sendMessage: (text: string) => Promise<void>;
    isStreaming: boolean;
    isResolvingInterruption: boolean;
    resolveInterruption: (
        decision: InterruptionDecision,
        feedback?: string,
    ) => Promise<void>;
    cancel: () => void;
}

export function useChatStream(): UseChatStream {
    const dispatch = useAppDispatch();
    const { selectedConversationId } = useAppSelector((state) => state.conversation);
    const { collections: selectedCollections } = useConversationSelections(
        selectedConversationId,
    );
    const {
        isStreaming,
        pendingInterruption,
        isResolvingInterruption,
    } = useAppSelector((state) => state.chat);
    const abortRef = useRef<AbortController | null>(null);

    const cancel = useCallback((): void => {
        abortRef.current?.abort();
        abortRef.current = null;
        dispatch(stopStreaming());
    }, [dispatch]);

    const applyStreamEvent = useCallback(
        (event: SSEEvent, conversationId: string): 'interruption' | 'error' | null => {
            switch (event.event) {
                case STREAM_EVENT.BLOCK_OPEN:
                    dispatch(openContentBlock(event.data as BlockOpenPayload));
                    break;
                case STREAM_EVENT.BLOCK_DELTA:
                    dispatch(appendContentBlockDelta(event.data as BlockDeltaPayload));
                    break;
                case STREAM_EVENT.BLOCK_CLOSE:
                    dispatch(closeContentBlock(event.data as BlockClosePayload));
                    break;
                case STREAM_EVENT.CHAT:
                    dispatch(appendAssistantContent(event.data[0]?.content || ''));
                    break;
                case STREAM_EVENT.REASONING:
                    dispatch(
                        appendAssistantReasoningContent(
                            event.data[0]?.content || '',
                        ),
                    );
                    break;
                case STREAM_EVENT.NAME_SUGGESTION:
                    dispatch(
                        patchConversationTitle({
                            id: conversationId,
                            title: event.data.name,
                        }),
                    );
                    break;
                case STREAM_EVENT.INTERRUPTION:
                    dispatch(setPendingInterruption(event.data));
                    return 'interruption';
                case STREAM_EVENT.ERROR:
                    dispatch(
                        setStreamingError(event.data.message || 'Stream error'),
                    );
                    return 'error';
                default:
                    break;
            }
            return null;
        },
        [dispatch],
    );

    const sendMessage = useCallback(
        async (text: string) => {
            if (
                !selectedConversationId
                || isStreaming
                || pendingInterruption
                || isResolvingInterruption
            ) {
                return;
            }

            const command = parseChatCommand(text);
            if (!command.message) {
                dispatch(setStreamingError('Enter a query after /global.'));
                return;
            }

            abortRef.current?.abort();
            const abort = new AbortController();
            abortRef.current = abort;

            const userMessageId = uuidv4();
            const assistantMessageId = uuidv4();

            dispatch(
                addUserMessage({
                    id: userMessageId,
                    role: MESSAGE_ROLE.USER,
                    content: command.message.replace(/@\[(.+?)\]\(.+?\)/g, '$1'),
                    feedback: USER_FEEDBACK.NEUTRAL,
                    contentBlocks: [],
                }),
            );

            dispatch(
                addAssistantMessage({
                    id: assistantMessageId,
                    role: MESSAGE_ROLE.ASSISTANT,
                    feedback: USER_FEEDBACK.NEUTRAL,
                    content: '',
                    contentBlocks: [],
                }),
            );

            dispatch(startStreaming());

            try {
                for await (const event of streamChatResponse(
                    {
                        conversationId: selectedConversationId,
                        message: command.message,
                        collectionIds: selectedCollections.map((c) => c.id),
                        globalQuery: command.globalQuery,
                    },
                    abort.signal,
                )) {
                    if (abort.signal.aborted) break;
                    applyStreamEvent(event, selectedConversationId);
                }

                if (!abort.signal.aborted && selectedConversationId) {
                    dispatch(stopStreaming());
                    await dispatch(
                        fetchMessagesByConversation(selectedConversationId),
                    );
                }
            } catch (error) {
                if (!abort.signal.aborted) {
                    const errorMessage =
                        error instanceof Error
                            ? error.message
                            : 'An error occurred while streaming';
                    dispatch(setStreamingError(errorMessage));
                }
            } finally {
                dispatch(stopStreaming());
                abortRef.current = null;
            }
        },
        [
            dispatch,
            selectedConversationId,
            selectedCollections,
            isStreaming,
            pendingInterruption,
            isResolvingInterruption,
            applyStreamEvent,
        ],
    );

    const resolveInterruption = useCallback(
        async (decision: InterruptionDecision, feedback = '') => {
            if (
                !selectedConversationId
                || !pendingInterruption
                || isResolvingInterruption
                || isStreaming
            ) {
                return;
            }

            const abort = new AbortController();
            abortRef.current = abort;
            dispatch(startResolvingInterruption());

            if (decision !== 'cancel') {
                dispatch(
                    addAssistantMessage({
                        id: uuidv4(),
                        role: MESSAGE_ROLE.ASSISTANT,
                        feedback: USER_FEEDBACK.NEUTRAL,
                        content: '',
                        contentBlocks: [],
                    }),
                );
                dispatch(startStreaming());
            }

            let nextInterruption = false;
            let streamFailed = false;
            try {
                for await (const event of respondToInterruption(
                    pendingInterruption,
                    decision,
                    feedback,
                    abort.signal,
                )) {
                    if (abort.signal.aborted) return;
                    const outcome = applyStreamEvent(
                        event,
                        selectedConversationId,
                    );
                    nextInterruption ||= outcome === 'interruption';
                    streamFailed ||= outcome === 'error';
                }

                if (decision === 'cancel' || (!nextInterruption && !streamFailed)) {
                    dispatch(clearPendingInterruption());
                }
                dispatch(stopStreaming());
                await dispatch(
                    fetchMessagesByConversation(selectedConversationId),
                );
            } catch (error) {
                if (!abort.signal.aborted) {
                    dispatch(
                        setInterruptionError(
                            error instanceof Error
                                ? error.message
                                : 'Failed to resolve the global query plan',
                        ),
                    );
                }
            } finally {
                dispatch(stopStreaming());
                dispatch(finishResolvingInterruption());
                abortRef.current = null;
            }
        },
        [
            selectedConversationId,
            pendingInterruption,
            isResolvingInterruption,
            isStreaming,
            dispatch,
            applyStreamEvent,
        ],
    );

    return {
        sendMessage,
        isStreaming,
        isResolvingInterruption,
        resolveInterruption,
        cancel,
    };
}
