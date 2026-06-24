import { useEffect, useLayoutEffect, useRef } from 'react';
import { MessageBubble } from './MessageBubble';
import { useAppDispatch, useAppSelector } from '../../hooks/redux';
import { clearError, fetchMessagesByConversation } from '../../store/chat.slice';
import { ErrorBanner } from '../banner/Error';

const STICKY_BOTTOM_THRESHOLD_PX = 140;

export function MessageList() {
    const dispatch = useAppDispatch();
    const selectedConversationId = useAppSelector(
        (state) => state.conversation.selectedConversationId,
    );
    const messages = useAppSelector((state) => state.chat.messages);
    const { error, isStreaming, streamingMessageIdx, isLoadingMessages } =
        useAppSelector((state) => state.chat);
    const scrollContainerRef = useRef<HTMLDivElement>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const stickToBottomRef = useRef(true);
    const prevMessageCountRef = useRef(0);
    const prevConversationIdRef = useRef<string | null>(null);

    useEffect(() => {
        if (!selectedConversationId || isStreaming) return;
        dispatch(fetchMessagesByConversation(selectedConversationId));
        // Only refetch when the conversation changes, not when streaming ends.
        // eslint-disable-next-line react-hooks/exhaustive-deps -- isStreaming read once on mount/select
    }, [dispatch, selectedConversationId]);

    useEffect(() => {
        const el = scrollContainerRef.current;
        if (!el) return;

        const onScroll = () => {
            const dist = el.scrollHeight - el.scrollTop - el.clientHeight;
            stickToBottomRef.current = dist < STICKY_BOTTOM_THRESHOLD_PX;
        };

        el.addEventListener('scroll', onScroll, { passive: true });
        onScroll();
        return () => el.removeEventListener('scroll', onScroll);
    }, [selectedConversationId]);

    useLayoutEffect(() => {
        const convChanged = selectedConversationId !== prevConversationIdRef.current;
        if (convChanged) {
            prevConversationIdRef.current = selectedConversationId;
            prevMessageCountRef.current = 0;
            stickToBottomRef.current = true;
        }

        const len = messages.length;
        const prevLen = prevMessageCountRef.current;
        const newMessage = len > prevLen;
        prevMessageCountRef.current = len;

        if (newMessage) {
            stickToBottomRef.current = true;
        }

        if (!stickToBottomRef.current && !newMessage && !convChanged) {
            return;
        }

        const sc = scrollContainerRef.current;
        if (sc) {
            sc.scrollTop = Math.max(0, sc.scrollHeight - sc.clientHeight);
            return;
        }

        messagesEndRef.current?.scrollIntoView({
            block: 'end',
            behavior: newMessage && !isStreaming ? 'smooth' : 'auto',
        });
    }, [selectedConversationId, messages, isStreaming]);

    if (isLoadingMessages && !isStreaming) {
        return (
            <div className="flex flex-1 items-center justify-center bg-app">
                <div className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--color-border)] border-t-[var(--color-primary)]" />
            </div>
        );
    }

    if (messages.length === 0 && !isStreaming) {
        return null;
    }

    return (
        <div
            ref={scrollContainerRef}
            className="flex-1 overflow-y-auto bg-app"
        >
            <div className="mx-auto w-full max-w-3xl space-y-1 px-4 py-8 pb-4">
                {messages.map((msg, idx) => (
                    <MessageBubble
                        key={msg.id}
                        message={msg}
                        isStreaming={isStreaming && idx === streamingMessageIdx}
                    />
                ))}
                <ErrorBanner error={error} onClose={() => dispatch(clearError())} />
                <div ref={messagesEndRef} />
            </div>
        </div>
    );
}
