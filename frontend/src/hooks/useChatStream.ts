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
} from '../store/chat.slice';
import { patchConversationTitle } from '../store/conversation.slice';
import { useConversationSelections } from './useConversationSelections';
import { streamChatResponse } from '../services/api/chats';
import { v4 as uuidv4 } from 'uuid';

interface UseChatStream {
    sendMessage: (text: string) => Promise<void>;
    isStreaming: boolean;
    cancel: () => void;
}

export function useChatStream(): UseChatStream {
    const dispatch = useAppDispatch();
    const { selectedConversationId } = useAppSelector((state) => state.conversation);
    const { collections: selectedCollections } = useConversationSelections(
        selectedConversationId,
    );
    const { isStreaming } = useAppSelector((state) => state.chat);
    const abortRef = useRef<AbortController | null>(null);

    const cancel = useCallback((): void => {
        abortRef.current?.abort();
        abortRef.current = null;
        dispatch(stopStreaming());
    }, [dispatch]);

    const sendMessage = useCallback(
        async (text: string) => {
            if (!selectedConversationId || isStreaming) return;

            abortRef.current?.abort();
            const abort = new AbortController();
            abortRef.current = abort;

            const userMessageId = uuidv4();
            const assistantMessageId = uuidv4();

            dispatch(
                addUserMessage({
                    id: userMessageId,
                    role: MESSAGE_ROLE.USER,
                    content: text.replace(/@\[(.+?)\]\(.+?\)/g, '$1'),
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
                        message: text,
                        collectionIds: selectedCollections.map((c) => c.id),
                    },
                    abort.signal,
                )) {
                    if (abort.signal.aborted) break;

                    switch (event.event) {
                        case STREAM_EVENT.BLOCK_OPEN:
                            dispatch(
                                openContentBlock(event.data as BlockOpenPayload),
                            );
                            break;
                        case STREAM_EVENT.BLOCK_DELTA:
                            dispatch(
                                appendContentBlockDelta(
                                    event.data as BlockDeltaPayload,
                                ),
                            );
                            break;
                        case STREAM_EVENT.BLOCK_CLOSE:
                            dispatch(
                                closeContentBlock(event.data as BlockClosePayload),
                            );
                            break;
                        case STREAM_EVENT.CHAT: {
                            const token = event.data[0]?.content || '';
                            dispatch(appendAssistantContent(token));
                            break;
                        }
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
                                    id: selectedConversationId,
                                    title: event.data.name,
                                }),
                            );
                            break;
                        case STREAM_EVENT.ERROR:
                            dispatch(
                                setStreamingError(
                                    event.data.message || 'Stream error',
                                ),
                            );
                            break;
                        default:
                            break;
                    }
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
        [dispatch, selectedConversationId, selectedCollections, isStreaming],
    );

    return { sendMessage, isStreaming, cancel };
}
